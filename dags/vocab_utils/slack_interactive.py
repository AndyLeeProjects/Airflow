import random
import numpy as np
from datetime import datetime, date, timedelta, timezone
import time
from airflow.models import Variable
from spellchecker import SpellChecker
import os
import json
import requests
import pandas as pd
from slack_sdk.errors import SlackApiError
from sqlalchemy import create_engine, text
from slack import WebClient

def update_memorized_vocabs(vocab_df):
    
    # extract data from memorized_vocabs table
    sql = "select * from memorized_vocabs"

    con = create_engine(Variable.get("db_uri_token"))

    memorized_df = pd.read_sql_query(sql, con)

    # Make a GET request to the /payloads endpoint
    response = requests.get('http://199.241.139.206:5001/payloads')

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Extract the payloads from the response
        payloads = response.json()

        df = pd.DataFrame(columns=['vocab', 'text', 'button_clicked', 'timestamp', 'user_id'])
        
        # Process the payloads as needed
        for payload in payloads:
            # Extract the necessary data from the payload
            vocab = vocab.split("* ")[1]
            text = payload.get('message', {}).get('text', '')
            button_clicked = payload.get('actions', [{}])[0].get('text', {}).get('text', '')
            timestamp = payload.get('actions', [{}])[0].get('action_ts', '')
            user_id = payload.get('channel', {}).get('id', '')

            # Check if the timestamp is greater than June 25, 2023
            if float(timestamp) > 1675286400.0:
                # make a dataframe
                df = df.append({'vocab': vocab, 'text': text, 'button_clicked': button_clicked, 'timestamp': timestamp, 'user_id': user_id}, ignore_index=True)

    else:
        # Request was not successful, handle the error
        print(f"Error: {response.status_code}")

    # Check if there's any row that matches any row in memorized_df
    df = df[~df.isin(memorized_df)].dropna()
    df.to_sql('memorized_vocabs', con=con, if_exists='append', index=False)

    # Update vocab_df with the new memorized vocabs
    vocab_df["status"] = np.where(vocab_df["vocab"].isin(df["vocab"]), "Memorized", vocab_df["status"])
    vocab_df["memorized_at_utc"] = np.where(vocab_df["vocab"].isin(df["vocab"]), timezone.utc, vocab_df["memorized_at_utc"])
    vocab_df.to_sql('my_vocabs', con=con, if_exists='replace', index=False)

def send_memorized_button(channel_id, vocabulary_name):
    try:
        # Construct the Slack message blocks
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Vocabulary:* {vocabulary_name}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Memorized 🤩"
                        },
                        "value": "memorized"
                    }
                ]
            }
        ]

        client.chat_postMessage(
                text = "test",
                channel = channel_id,
                blocks = blocks)

        # Print the response from Slack API (optional)
        print(response)

    except SlackApiError as e:
        print(e.response)
        print(f"Error sending Slack message: {e.response['error']}")
