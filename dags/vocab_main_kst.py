from vocab_utils.lingua_api import get_definitions
from vocab_utils.send_slack_message import send_slack_message
from vocab_utils.main import LearnVocab, UsersDeployment
from vocab_utils.scrape_images import scrape_web_images
from sqlalchemy import create_engine
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime, timedelta, time as time_time
import pandas as pd
import logging
import nltk
nltk.download('wordnet')

log = logging.getLogger(__name__)

def send_vocab_message():
    timezone = "KST"
    con = create_engine(Variable.get("db_uri_token"))
    user_df = pd.read_sql_query("SELECT * FROM users;", con)
    est_users = user_df[user_df['timezone'] == timezone]

    for user_id in est_users['user_id']:
        UD = UsersDeployment(user_id)
        UD.execute_by_user()

default_args = {
    'owner': 'anddy0622@gmail.com',
    'depends_on_past': False,
    'email': ['anddy0622@gmail.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    "send_vocab_message_dag_kst",
    start_date=datetime(2022, 6, 1, 17, 15),
    default_args=default_args,
    schedule_interval="0 12,23 * * *",
    catchup=False
) as dag:

    uploading_data = PythonOperator(
        task_id="send_vocab_message_dag_kst",
        python_callable=send_vocab_message
    )
