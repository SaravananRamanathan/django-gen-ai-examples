from datetime import timedelta

import django_bootstrap
import pendulum
from airflow.models.dag import DAG
from airflow.providers.standard.operators.python import PythonOperator


def task_get_google_authenticated_user_emails():
    from django_gen_ai_examples.apps.chat_bot.tasks import get_google_authenticated_user_emails

    return get_google_authenticated_user_emails()


def task_get_upcoming_events(email: str):
    from django_gen_ai_examples.apps.chat_bot.tasks import get_upcoming_events

    return get_upcoming_events(email)


with DAG(
    dag_id="list_users_calendar_events",
    schedule=None,
    start_date=pendulum.datetime(2025, 8, 1, tz="UTC"),
    catchup=False,
    tags=["upcoming-events", "google", "calendar"],
) as dag:

    t_get_google_authenticated_user_emails = PythonOperator(
        task_id="get_google_authenticated_user_emails",
        python_callable=task_get_google_authenticated_user_emails,
        retries=5,
        retry_delay=timedelta(seconds=30),
    )

    t_get_upcoming_events = PythonOperator.partial(
        task_id="get_upcoming_events",
        python_callable=task_get_upcoming_events,
    ).expand(op_args=t_get_google_authenticated_user_emails.output.map(lambda email: [email]))
    # ).expand(op_args=t_get_google_authenticated_user_emails.output)

    t_get_google_authenticated_user_emails >> t_get_upcoming_events
