# Send a Message using Slack API
from cgitb import text
import random
import numpy as np
from datetime import datetime, date, timedelta
import time
from airflow.models import Variable
from spellchecker import SpellChecker
import os
import json
from slack_sdk import WebClient
import requests
from slack_sdk.errors import SlackApiError

# slack_token = Variable.get("slack_credentials_token")
client = WebClient(token=slack_token)

def send_slack_message(channel_id, vocabulary_name):
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
                            "text": "👎"
                        },
                        "value": "confident"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "😐"
                        },
                        "value": "neutral"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "👍"
                        },
                        "value": "not_confident"
                    }
                ]
            }
        ]

        payload = {
            "blocks": blocks
        }

        # Send the Slack message
        response = requests.post(webhook_url, json=payload)

        # Print the response from Slack API (optional)
        print(response)

    except SlackApiError as e:
        print(e.response)
        print(f"Error sending Slack message: {e.response['error']}")

# Usage: Specify the channel ID and vocabulary name
webhook_url = "https://hooks.slack.com/services/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"
vocabulary_name = "Timid"

# Send the Slack message
send_slack_message(webhook_url, vocabulary_name)
