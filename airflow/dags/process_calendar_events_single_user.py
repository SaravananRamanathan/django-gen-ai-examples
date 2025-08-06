"""
Process Google Calendar events for a single user.
"""

import logging
from datetime import timedelta

import django_bootstrap
import pendulum
from airflow import DAG
from airflow.models.param import ParamsDict
from airflow.sdk import Param

logger = logging.getLogger(__name__)

from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.trigger_rule import TriggerRule


def task_validate_user_email(**airflow_context):
    from django_gen_ai_examples.apps.chat_bot.tasks import validate_user_email

    logger.info("Params = %s", airflow_context["params"])
    user_email = airflow_context["params"]["user_email"]
    validation_status = validate_user_email(user_email)
    if not validation_status:
        return "validation_failed"
    return "validation_succeeded"


def task_process_single_user_calendar_events(**airflow_context):
    from django_gen_ai_examples.apps.chat_bot.tasks import process_single_user_calendar_events

    user_email = airflow_context["params"]["user_email"]
    days_back = airflow_context["params"]["days_back"]
    days_forward = airflow_context["params"]["days_forward"]

    result = process_single_user_calendar_events(email=user_email, days_back=days_back, days_forward=days_forward)

    return result


with DAG(
    dag_id="process_calendar_events_single_user",
    schedule=None,
    start_date=pendulum.datetime(2025, 8, 6, tz="UTC"),
    catchup=False,
    tags=["single-user", "google", "calendar-events"],
    params=ParamsDict(
        {
            "user_email": Param(
                type=["null", "string"],
                format="idn-email",
                default=None,
                description="Email of the user whose calendar events to process",
            ),
            "days_back": Param(
                type="integer",
                minimum=1,
                maximum=365,
                default=1,
                description="Number of days to look back [Past] for events (default: 1)",
            ),
            "days_forward": Param(
                type="integer",
                minimum=1,
                maximum=365,
                default=1,
                description="Number of days to look forward [Future] for events (default: 1)",
            ),
        }
    ),
) as dag:

    t_validate_user_email = BranchPythonOperator(
        task_id="validate_user_email",
        python_callable=task_validate_user_email,
        retries=2,
        retry_delay=timedelta(seconds=20),
    )

    t_process_single_user_calendar_events = PythonOperator(
        task_id="process_single_user_calendar_events",
        python_callable=task_process_single_user_calendar_events,
        trigger_rule=TriggerRule.ALL_SUCCESS,
        retries=2,
        retry_delay=timedelta(seconds=20),
    )

    t_validation_succeeded = EmptyOperator(
        task_id="validation_succeeded",
    )

    t_validation_failed = BashOperator(
        task_id="validation_failed",
        bash_command="echo 'Validation failed, exiting.' && exit 1",
    )

    t_validate_user_email >> t_validation_succeeded >> t_process_single_user_calendar_events
    t_validate_user_email >> t_validation_failed
