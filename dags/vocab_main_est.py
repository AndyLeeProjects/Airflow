from vocab_utils.main import UsersDeployment
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine
import pandas as pd

def send_vocab_message():
    try:
        con = create_engine(Variable.get("db_uri_token"))
        user_df = pd.read_sql_query("SELECT * FROM users;", con)
        est_users = user_df[user_df['timezone'] == "EST"]

        est_users = est_users[est_users["status"] == "Active"]
        est_users = est_users[est_users["user"] != "Test"]

        for _, user_id in est_users['user_id'].iteritems():
            language = est_users[est_users['user_id'] == user_id]['language'].iloc[0]
            UD = UsersDeployment(user_id, language, "EST")
            UD.execute_by_user()
    except Exception as e:
        logging.error(f"Error in send_vocab_message: {e}")
        raise

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
    "send_vocab_message_dag_est",
    start_date=datetime(2022, 6, 1, 17, 15),
    default_args=default_args,
    schedule_interval="0 12,13 * * *",
    catchup=False
) as dag:

    start = DummyOperator(
        task_id='start'
    )

    uploading_data = PythonOperator(
        task_id="send_vocab_message_task",
        python_callable=send_vocab_message
    )

    end = DummyOperator(
        task_id='end'
    )

    start >> uploading_data >> end
