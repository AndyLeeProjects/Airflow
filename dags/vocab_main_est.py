import os, sys
from vocab_utils.db_connections import con
from vocab_utils.lingua_api import get_definitions
from vocab_utils.send_slack_message import send_slack_message
from vocab_utils.main import LearnVocab, UsersDeployment
from vocab_utils.scrape_images import scrape_web_images
from airflow import DAG
from datetime import date, datetime, timezone, timedelta, time as time_time
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import logging
import nltk
nltk.download('wordnet')

log = logging.getLogger(__name__)

def send_vocab_message():
    UD = UsersDeployment()
    UD.execute_by_user()


default_args = {
    'owner': 'anddy0622@gmail.com',
    'depends_on_past': False,
    'email': ['anddy0622@gmail.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    "send_vocab_message_dag",
    start_date=datetime(2022, 6, 1, 17, 15),
    default_args=default_args,
    schedule_interval="0 9 * * *",
    catchup=False
) as dag:

    uploading_data = PythonOperator(
        task_id="send_vocab_message_dag",
        python_callable=send_vocab_message
    )