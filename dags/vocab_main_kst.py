from vocab_utils.main import UsersDeployment
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import logging

log = logging.getLogger(__name__)

def send_vocab_message():
    from sqlalchemy import create_engine
    import pandas as pd
    dag_timezone = "KST"
    con = create_engine(Variable.get("db_uri_token"))
    user_df = pd.read_sql_query("SELECT * FROM users;", con)
    kst_users = user_df[user_df['timezone'] == timezone]
    kst_users = kst_users[kst_users["status"] == "Active"]

    kst_users = []
    if len(kst_users) != 0:
        for ind, user_id in enumerate(kst_users['user_id']):
            language = kst_users[kst_users['user_id'] == user_id]['language'].iloc[0]
            UD = UsersDeployment(user_id, language, dag_timezone)
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
    schedule="0 12,23 * * *",
    catchup=False
) as dag:

    uploading_data = PythonOperator(
        task_id="send_vocab_message_dag_kst",
        python_callable=send_vocab_message
    )
