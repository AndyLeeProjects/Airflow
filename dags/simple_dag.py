from datetime import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator

# Define the DAG
dag = DAG(
    'sample_dag',
    description='A basic sample DAG',
    schedule_interval="0 12 * * *",
    start_date=datetime(2023, 5, 27),
    catchup=False
)

# Define the tasks
task1 = DummyOperator(
    task_id='task1',
    dag=dag
)

task2 = DummyOperator(
    task_id='task2',
    dag=dag
)

# Define the task dependencies
task1 >> task2
