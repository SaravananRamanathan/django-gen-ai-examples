"""
Simple test DAG to verify Airflow is working properly
"""

from datetime import datetime, timedelta

import django_bootstrap
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import PythonOperator


def task_test_airflow_dag():
    from django_gen_ai_examples.apps.chat_bot.tasks.test_airflow_dags import test_airflow_dag

    return test_airflow_dag()


default_args = {
    "owner": "django-gen-ai-examples",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    "simple_test",
    default_args=default_args,
    description="Simple test DAG with basic commands",
    schedule=None,
    catchup=False,
    tags=["test", "simple"],
)

echo_task = BashOperator(
    task_id="echo_hello",
    bash_command='echo "Hello, test successful!"',
    dag=dag,
)

date_task = BashOperator(
    task_id="print_date",
    bash_command="date",
    dag=dag,
)

ls_task = BashOperator(
    task_id="list_directory",
    bash_command="ls -la /code",
    dag=dag,
)

t_task_test_airflow_dag = PythonOperator(
    task_id="test_airflow_dag",
    python_callable=task_test_airflow_dag,
    dag=dag,
    retries=2,
    retry_delay=timedelta(seconds=30),
)

# Set task dependencies:
echo_task >> date_task >> ls_task >> t_task_test_airflow_dag
