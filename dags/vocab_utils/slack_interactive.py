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

def update_memorized_vocabs(vocab_df):

    # Make a GET request to the /payloads endpoint
    response = requests.get('http://199.241.139.206:5001/payloads')

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Extract the payloads from the response
        payloads = response.json()

        df = pd.DataFrame(columns=['vocab', 'button_clicked', 'timestamp', 'user_id'])
        stopwords = ["User Update &amp; Analysis :heavy_check_mark:",
                     "Go to the Page"]
        # Process the payloads as needed
        for payload in payloads:
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
        condition = (vocab_df['vocab'] == row['vocab']) & (vocab_df['user_id'] == row['user_id'])
        vocab_df.loc[condition, 'status'] = 'Memorized'
        action_ts_float = row['timestamp']
        action_utc_time = datetime.utcfromtimestamp(action_ts_float).replace(tzinfo=timezone.utc)

        # Formatting the action_utc_time as a string in the desired datetime format
        formatted_time = action_utc_time.strftime('%Y-%m-%dT%H:%M:%S.%f')
        vocab_df.loc[condition, 'memorized_at_utc'] = formatted_time

    return vocab_df
