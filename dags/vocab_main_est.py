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
    dag_timezone = "EST"
    con = create_engine(Variable.get("db_uri_token"))
    user_df = pd.read_sql_query("SELECT * FROM users;", con)
    est_users = user_df[user_df['timezone'] == dag_timezone]

    # Only include Active users
    est_users = est_users[est_users["status"] == "Active"]

    # Exclude Test user
    est_users = est_users[est_users["user"] != "Test"]

    for ind, user_id in enumerate(est_users['user_id']):
        # Get the language for the user_id
        language = est_users[est_users['user_id'] == user_id]['language'].iloc[0]

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
    "send_vocab_message_dag_est",
    start_date=datetime(2022, 6, 1, 17, 15),
    default_args=default_args,
    schedule="0 12,01 * * *",
    catchup=False
) as dag:

    uploading_data = PythonOperator(
        task_id="send_vocab_message_dag_est",
        python_callable=send_vocab_message
    )
