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


def update_quizzed_vocabs(vocab_df, quiz_details_df, engine):

    # Make a GET request to the /payloads endpoint
    response = requests.get('http://199.241.139.206:5001/payloads')
    
    # Check if the request was successful (status code 200)
    if response.status_code != 200:
        return response.status_code
    # Extract the payloads from the response
    payloads = response.json()
    quiz_details = pd.DataFrame(columns=["quiz_id", "user_id", "vocab_id", "target_vocab", "selected_vocab", "quiz_content", "quizzed_at_utc", "quiz_submitted_at_utc", "status"])
    for payload in payloads:
        # Gget Vocab from the payload
        try:
            selected_vocab = payload["actions"][0]["selected_option"]["text"]["text"]
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
            vocab_id = payload["actions"][0]["action_id"]
            action_ts = payload["actions"][0]["action_ts"]
            action_ts = datetime.utcfromtimestamp(float(action_ts)).replace(tzinfo=timezone.utc)
            channel_id = payload["channel"]["id"]
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
                        "status": ["quiz_completed"]
                    })

                    # Concatenate quiz_details_df and quiz_detail
                    quiz_details_df = pd.concat([quiz_details_df, quiz_detail], ignore_index=True)
                else:
                    quiz_id = vocab_id + channel_id
                    quiz_details_df.loc[quiz_details_df['quiz_id'] == quiz_id, 'selected_vocab'] = selected_vocab
                    quiz_details_df.loc[quiz_details_df['quiz_id'] == quiz_id, 'quiz_submitted_at_utc'] = action_ts
                    quiz_details_df.loc[quiz_details_df['quiz_id'] == quiz_id, 'status'] = "quiz_completed"

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

