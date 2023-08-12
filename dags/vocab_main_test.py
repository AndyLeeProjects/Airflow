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
    con = create_engine(Variable.get("db_uri_token"))
    dag_timezone = "EST"
    user_df = pd.read_sql_query("SELECT * FROM users;", con)
    test_users = user_df[user_df['user'] == "Test"]

    for ind, user_id in enumerate(test_users['user_id']):
        # Get the language for the user_id
        log.info(user_id)
        language = test_users[test_users['user_id'] == user_id]['language'].iloc[0]

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
    "send_vocab_message_dag_test",
    start_date=datetime(2022, 6, 1, 17, 15),
    default_args=default_args,
    schedule="0 12,01 * * *",
    catchup=False
) as dag:

    uploading_data = PythonOperator(
        task_id="send_vocab_message_dag_test",
        python_callable=send_vocab_message
    )
