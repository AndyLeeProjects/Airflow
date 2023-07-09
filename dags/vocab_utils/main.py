from vocab_utils.lingua_api import get_definitions
from sqlalchemy import create_engine, text
from vocab_utils.send_slack_message import send_slack_message
from vocab_utils.scrape_images import scrape_web_images
from datetime import date, datetime, timezone, timedelta, time as time_time
from slack import WebClient
import pandas as pd
import numpy as np
import random
import difflib
from airflow.models import Variable
from vocab_utils.slack_interactive import update_memorized_vocabs, update_quizzed_vocabs, review_previous_quiz_result
from vocab_utils.slack_quiz import send_slack_quiz
import nltk
nltk.download('wordnet')
nltk.download('omw-1.4')
from nltk.corpus import wordnet
import logging

log = logging.getLogger(__name__)

class LearnVocab():

    def __init__(self, user_id):
        self.con = create_engine(Variable.get("db_uri_token"))
        slack_token = Variable.get("slack_credentials_token")
        self.client = WebClient(slack_token)

        # Retrieve vocabularies from the database
        self.vocab_all_df = pd.read_sql_query(f"SELECT * FROM my_vocabs;", self.con)
        self.vocab_df = pd.read_sql_query(f"SELECT * FROM my_vocabs where user_id = '{user_id}';", self.con)
        self.vocab_rest_df = pd.read_sql_query(f"SELECT * FROM my_vocabs where user_id != '{user_id}';", self.con)
        self.vocabs_next = self.vocab_df[self.vocab_df['status'] == 'Next']
        self.vocabs_waitlist = self.vocab_df[self.vocab_df['status'] == 'Wait List']
        self.user_id = user_id
        # Get vocab_details from the database
        self.quiz_details_df = pd.read_sql_query("SELECT * FROM quiz_details", self.con)

        # Total number of vocabularies for each slack notification
        self.num_vocab_sug = 5

        # When it reaches the total_exposures, move to "memorized" database for testing
        self.exposure_aim = 7

    def get_quiz_results(self, user_id):
        self.vocab_df = update_quizzed_vocabs(self.vocab_df, self.quiz_details_df, user_id, self.con)
        updated_vocab_df = pd.concat([self.vocab_df, self.vocab_rest_df])
        updated_vocab_df.to_sql('my_vocabs', self.con, if_exists='replace', index=False)

    def extract_memorized(self):
        updated_vocab_df = update_memorized_vocabs(self.vocab_df)
        updated_vocab_df = pd.concat([updated_vocab_df, self.vocab_rest_df])
        updated_vocab_df.to_sql('my_vocabs', self.con, if_exists='replace', index=False)

    def update_exposures(self):
        # Update the exposure of each vocab
        for i in range(len(self.vocab_df)):
            if self.vocab_df.loc[i, 'status'] == 'Next':
                self.vocab_df.loc[i, 'exposure'] += 1
                self.vocab_df.loc[i, 'status'] = 'Wait List'

    def update_next_vocabs(self):
        self.vocabs_waitlist = self.vocabs_waitlist.sort_values(by=['exposure'], ascending=False)
        
        # Randomly select self.num_vocab_sug amount of vocabularies from the waitlist
        adjusted_num_vocab_sug = min(self.num_vocab_sug, len(self.vocabs_waitlist))
        next_random = self.vocabs_waitlist.sample(n=adjusted_num_vocab_sug)
        
        # Change the status of the selected vocabularies to "Next" in the self.vocab_df
        for vocab in next_random['vocab']:
            self.vocab_df.loc[self.vocab_df['vocab'] == vocab, 'status'] = 'Next'

    def is_valid_word(self, word):
        if wordnet.synsets(word):
            return True
        return False

    def find_closest_word(self, word):
        valid_words = set(wordnet.words())
        closest_match = difflib.get_close_matches(word, valid_words, n=1, cutoff=0.8)
        if closest_match:
            return closest_match[0]
        return None

    def update_new_vocabs(self, user_id):
        slack_data = self.client.conversations_history(channel=user_id)
        new_vocabs = []
        self.vocab_origins = []
        
        # Calculate the day difference between today and the inputted vocabs
        ## Find newly added vocabs in the last 3 days
        today = datetime.today()
        two_days_ts = datetime.timestamp(today - timedelta(days = 40))

        # Unfold dictionary to get the list of newly added vocabs
        added_vocabs = [slack_data['messages'][i]['text'].lower()
                        for i in range(len(slack_data['messages'])) 
                        if float(slack_data['messages'][i]['ts']) > two_days_ts
                        and "check out" not in slack_data['messages'][i]['text']]

        # Check if the vocab is already in the database
        for vocab in added_vocabs:
            vocab_len = vocab.split("(")[0].strip()
            if len(vocab_len.split(' ')) < 6 and 'has joined the channel' not in vocab:
                
                # Append "vocab_origin" (e.g. tree (I like tree))
                if "(" in vocab and ")" in vocab:
                    v_origin = vocab.split("(")[1].strip(")")
                    v_origin = v_origin[0].upper() + v_origin[1:]  # Captialize the first letter of the origin
                    self.vocab_origins.append(v_origin)
                    vocab = vocab.split("(")[0].strip()

                else:
                    self.vocab_origins.append(None)

                new_vocabs.append(vocab)

        if list(self.vocab_df['vocab'].values) == []:
            vocab_id_counter = 0
        else:
            vocab_id_counter = int(self.vocab_all_df["vocab_id"].max().replace("V", ""))

        # Adding vocabularies first time
        for ind, vocab in enumerate(new_vocabs):

            # Check if the word is valid
            if not self.is_valid_word(vocab):
                closest_word = self.find_closest_word(vocab)
                if closest_word:
                    vocab = closest_word
                else:
                    pass

            vocab = vocab.replace("_", " ")
            vocab_id_counter += 1
            if vocab not in self.vocab_df['vocab'].values:
                # Scrape web images (three)
                web_images = scrape_web_images(vocab)

                # Add new vocabs to the database
                self.vocab_df = pd.concat([self.vocab_df, 
                                           pd.DataFrame(
                                               {'vocab_id': "V" + f"{vocab_id_counter}".zfill(5), 
                                                'vocab': vocab, 
                                                'vocab_origin': self.vocab_origins[ind],
                                                'exposure': 0, 
                                                'status': "Wait List",
                                                "img_url1": web_images[0], 
                                                "img_url2": web_images[1], 
                                                "img_url3": web_images[2],
                                                "created_at_utc": datetime.now(timezone.utc), 
                                                "memorized_at_utc": None,
                                                "confidence": None, 
                                                "quizzed_count":0, 
                                                "correct_count": 0, 
                                                "incorrect_count":0,
                                                "user_id": user_id}, index=[0])])

        # Push it to the database
        updated_df = pd.concat([self.vocab_rest_df, self.vocab_df])
        updated_df.to_sql('my_vocabs', con=self.con, if_exists='replace', index=False)

    def send_slack_messages(self, user_id, target_lang, quiz_blocks, review_blocks):
        vocab_dic = get_definitions(self.vocabs_next['vocab'].values, self.vocabs_next['vocab_origin'].values, target_lang)

        # Add image urls to the dictionary
        img_url_dic = {}
        for i, vocab in enumerate(list(vocab_dic.keys())):
            # Add exposure count for each vocab
            vocab = vocab.replace("_", " ")
            vocab_dic[vocab][0]['exposure'] = self.vocabs_next[self.vocabs_next['vocab'] == vocab]['exposure'].values[0]

            img_df = self.vocabs_next[self.vocabs_next['vocab'] == vocab][['img_url1', 'img_url2', 'img_url3']]
            img_url_dic[vocab] = img_df.values.tolist()[0]

        send_slack_message(self.vocab_df, self.quiz_details_df, vocab_dic, img_url_dic, self.client, user_id, target_lang, quiz_blocks, review_blocks, self.con)

    def execute_all(self, user_id, target_lang, timezone):
        log.info(f"Updating {user_id}'s Vocabularies ...")
        log.info("Updating Quiz Results ...")
        self.get_quiz_results(user_id)
        log.info("Updating Memorized Vocabularies ...")
        self.extract_memorized()
        log.info("Updating Exposures ...")
        self.update_exposures()
        log.info("Updating Next Vocabularies ...")
        self.update_next_vocabs()
        log.info("Updating New Vocabularies ...")
        self.update_new_vocabs(user_id)
        log.info("Sending Slack Message ...")
        quiz_blocks, self.vocab_df = send_slack_quiz(self.vocab_df, self.quiz_details_df, user_id, target_lang, self.con)
        review_blocks = review_previous_quiz_result(self.quiz_details_df, user_id, timezone, self.con)
        # quiz_blocks = None means that no quiz was sent
        if quiz_blocks != None:
            updated_df = pd.concat([self.vocab_rest_df, self.vocab_df])
            updated_df.to_sql('my_vocabs', con=self.con, if_exists='replace', index=False)
        self.send_slack_messages(user_id, target_lang, quiz_blocks, review_blocks)
        log.info("\n")

class UsersDeployment:
    def __init__(self, user_id, language, timezone = None):
        self.LV = LearnVocab(user_id)
        self.user_id = user_id
        self.target_lang = language
        self.timezone = timezone

    def execute_by_user(self):
        self.LV.execute_all(self.user_id, self.target_lang, self.timezone)