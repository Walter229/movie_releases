import datetime
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator
import pendulum

# Set local timezone
local_tz = pendulum.timezone("Europe/Amsterdam")

# Extend path to include crawler module
sys.path.append('/Users/clemens/coding_projects/movie_releases')
from crawler import main

# Define default arguments
default_args={
    "depends_on_past": False,
    "email": ["bestmovieservice@gmail.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": datetime.timedelta(minutes=5)
}

# Set-Up DAG
dag =  DAG(
    'movie_crawler_dag',
    default_args=default_args,
    description='DAG that runs the movie crawler and uploads the data to MongoDB.',
    start_date=datetime.datetime(2022,12,29, tzinfo=local_tz),
    schedule_interval='0 17 * * *'
)

# Define ETL task
run_etl = PythonOperator(
    task_id='run_crawler_etl',
    python_callable=main.run_etl,
    dag=dag
)

# Define order of tasks
run_etl
    