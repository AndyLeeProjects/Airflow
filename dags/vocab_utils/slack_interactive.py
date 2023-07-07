import random
import numpy as np
from datetime import datetime, date, timedelta, timezone
import time
from spellchecker import SpellChecker
import os
import json
import requests
import pandas as pd
from slack_sdk.errors import SlackApiError
from sqlalchemy import create_engine, text
from slack import WebClient
import Levenshtein
import pytz

def update_memorized_vocabs(vocab_df):
    # Make a GET request to the /payloads endpoint
    response = requests.get('http://199.241.139.206:5001/payloads')

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Extract the payloads from the response
        payloads = response.json()

        df = pd.DataFrame(columns=['vocab', 'button_clicked', 'timestamp', 'user_id'])
        stopwords = ["User Update &amp; Analysis :heavy_check_mark:",
                     "Go to the Page", "Click the button:", "Submit Vocab"]
        # Process the payloads as needed
        for payload in payloads:
            if "Memorized" in payload.get('actions', [{}])[0].get('text', {}).get('text', ''):
                # Extract the necessary data from the payload
                vocab = payload.get('actions', [{}])[0].get('text', {}).get('text', '')
                vocab = vocab.split(" Memorized")[0].lower()
                button_clicked = payload.get('actions', [{}])[0].get('text', {}).get('text', '')
                timestamp = payload.get('actions', [{}])[0].get('action_ts', '')
                user_id = payload.get('channel', {}).get('id', '')

                # Check if the timestamp is greater than June 25, 2023
                if float(timestamp) > 1677261060 and vocab not in stopwords:
                    # make a dataframe
                    df = df.append({'vocab': vocab, 'button_clicked': button_clicked, 'timestamp': float(timestamp), 'user_id': user_id}, ignore_index=True)

    else:
        # Request was not successful, handle the error
        print(f"Error: {response.status_code}")

    for ind, row in df.iterrows():
        vocab = row['vocab']
        user_id = row['user_id']
        vocab_df.loc[(vocab_df['vocab'] == vocab) & (vocab_df['user_id'] == user_id), 'status'] = 'Memorized'

        action_ts_float = row['timestamp']
        action_utc_time = datetime.utcfromtimestamp(action_ts_float).replace(tzinfo=timezone.utc)

        # Formatting the action_utc_time as a string in the desired datetime format
        formatted_time = action_utc_time.strftime('%Y-%m-%dT%H:%M:%S.%f')
        vocab_df.loc[(vocab_df['vocab'] == vocab) & (vocab_df['user_id'] == user_id), 'memorized_at_utc'] = formatted_time

    return vocab_df

def get_values(payload, just_selected_option=False):
    block_id = next(iter(payload['state']['values']))  # Get the first block ID dynamically
    vocab_id = list(payload['state']['values'][block_id].keys())[0]
    selected_vocab = payload['state']['values'][block_id][vocab_id]['selected_option']["text"]["text"]
    if just_selected_option:
        return selected_vocab
    
    action_ts = payload['actions'][0]['action_ts']
    channel_id = payload['channel']['id']

    return selected_vocab, vocab_id, action_ts, channel_id


def update_quizzed_vocabs(vocab_df, quiz_details_df, engine):

    # Make a GET request to the /payloads endpoint
    response = requests.get('http://199.241.139.206:5001/payloads')
    
    # Check if the request was successful (status code 200)
    if response.status_code != 200:
        return response.status_code
    # Extract the payloads from the response
    payloads = response.json()
    quiz_details = pd.DataFrame(columns=["quiz_id", "user_id", "vocab_id", "target_vocab", "selected_vocab", "quiz_content", "quizzed_at_utc", "quiz_submitted_at_utc", "status", "quiz_result_sent"])
    for payload in payloads:
        # Gget Vocab from the payload
        try:
            selected_vocab = get_values(payload, just_selected_option=True)
        except:
            selected_vocab = None

        # Get Question from the payload
        question = None
        for block in payload['message']['blocks']:
            try:
                if "*Q: " in block["text"]["text"]:
                    question = block["text"]["text"].split("Q: ")[1]
            except:
                pass

        if question != None and selected_vocab != None:
            selected_vocab, vocab_id, action_ts, channel_id = get_values(payload)
            action_ts = datetime.utcfromtimestamp(float(action_ts)).replace(tzinfo=timezone.utc)
            try:
                vocab = vocab_df[vocab_df['vocab_id'] == vocab_id]['vocab'].values[0]

                if vocab_id + channel_id not in list(quiz_details_df['quiz_id']):
                    quiz_detail = pd.DataFrame({
                        "quiz_id": [vocab_id + channel_id],
                        "user_id": [channel_id],
                        "vocab_id": [vocab_id],
                        "target_vocab": [vocab],
                        "selected_vocab": [selected_vocab],
                        "quiz_content": [question],
                        "quizzed_at_utc": [None],
                        "quiz_submitted_at_utc": [action_ts],
                        "status": ["quiz_completed"],
                        "quiz_result_sent": [False]
                    })

                    # Concatenate quiz_details_df and quiz_detail
                    quiz_details_df = pd.concat([quiz_details_df, quiz_detail], ignore_index=True)
                
                elif quiz_details_df.loc[quiz_details_df['quiz_id'] == vocab_id + channel_id, 'status'].values[0] != "quiz_completed":
                    quiz_id = vocab_id + channel_id
                    quiz_details_df.loc[quiz_details_df['quiz_id'] == quiz_id, 'selected_vocab'] = selected_vocab
                    quiz_details_df.loc[quiz_details_df['quiz_id'] == quiz_id, 'quiz_submitted_at_utc'] = action_ts
                    quiz_details_df.loc[quiz_details_df['quiz_id'] == quiz_id, 'status'] = "quiz_completed"
                
                else:
                    quiz_detail = pd.DataFrame({
                        "quiz_id": [vocab_id + channel_id + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))],
                        "user_id": [channel_id],
                        "vocab_id": [vocab_id],
                        "target_vocab": [vocab],
                        "selected_vocab": [selected_vocab],
                        "quiz_content": [question],
                        "quizzed_at_utc": [None],
                        "quiz_submitted_at_utc": [action_ts],
                        "status": ["quiz_completed"],
                        "quiz_result_sent": [False]
                    })

                    # Concatenate quiz_details_df and quiz_detail
                    quiz_details_df = pd.concat([quiz_details_df, quiz_detail], ignore_index=True)


                distance = Levenshtein.distance(selected_vocab, vocab)
                max_length = max(len(selected_vocab), len(vocab))
                similarity_percentage = (max_length - distance) / max_length * 100
                if similarity_percentage >= 70:
                    vocab_df.loc[vocab_df['vocab_id'] == vocab_id, 'correct_count'] += 1
                else:
                    vocab_df.loc[vocab_df['vocab_id'] == vocab_id, 'incorrect_count'] += 1
            except:
                pass

    quiz_details_df.to_sql('quiz_details', engine, if_exists='replace', index=False)

    return vocab_df


def review_previous_quiz_result(quiz_details_df, user_id, timezone, con):
    
    def convert_utc_to_timezone(utc_time, target_timezone):
        # Define the UTC timezone
        utc_timezone = pytz.timezone('UTC')

        # Check if the UTC time is already timezone-aware
        if utc_time.tzinfo is None or utc_time.tzinfo.utcoffset(utc_time) is None:
            # If not timezone-aware, localize it with UTC timezone
            utc_time = utc_timezone.localize(utc_time)

        # Convert UTC time to the target timezone
        target_timezone = pytz.timezone(target_timezone)
        target_time = utc_time.astimezone(target_timezone)

        return target_time

    # Get the recent three quiz results
    most_recent_quiz_result = quiz_details_df[quiz_details_df['user_id'] == user_id].sort_values(by='quiz_submitted_at_utc', ascending=False).head(3)
    text_str = "*Answer / Selected  (Submitted at)*\n\n"
    for ind, row in most_recent_quiz_result.iterrows():
        target_vocab = row['target_vocab']
        selected_vocab = row['selected_vocab']
        date_submitted = row['quiz_submitted_at_utc']
        
        # Change the date_submitted to the user's timezone
        date_submitted = convert_utc_to_timezone(date_submitted, timezone)
        if target_vocab == selected_vocab:
            text_str += f"▻ *{target_vocab}* / {selected_vocab} ✅ ({date_submitted.strftime('%Y-%m-%d %H:%M:%S')})\n\n"
        else:
            text_str += f"▻ *{target_vocab}* / {selected_vocab} ❌ ({date_submitted.strftime('%Y-%m-%d %H:%M:%S')})\n\n"
        
        quiz_details_df.loc[quiz_details_df['quiz_id'] == row['quiz_id'], 'quiz_result_sent'] = True
    
    # Get the correct streak
    correct_streak = 0
    for ind, row in quiz_details_df[quiz_details_df['user_id'] == user_id].sort_values(by='quiz_submitted_at_utc', ascending=False).iterrows():
        if row['target_vocab'] == row['selected_vocab']:
            correct_streak += 1
        else:
            break
        
    
    quiz_result_block = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Previous Quiz Results 📝 [Streak: {correct_streak}]",
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text_str
                    }
                }
            ]
    
    quiz_details_df.to_sql('quiz_details', con, if_exists='replace', index=False)
    
    return quiz_result_block