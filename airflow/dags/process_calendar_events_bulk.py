"""
Process Google Calendar events for all users in the system.
"""

import logging
from datetime import timedelta

import django_bootstrap
import pendulum
from airflow import DAG
from airflow.models.param import ParamsDict
from airflow.sdk import Param

logger = logging.getLogger(__name__)

from airflow.exceptions import AirflowSkipException
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.trigger_rule import TriggerRule


def task_validate_params(**airflow_context):

    params = airflow_context["params"]
    logger.info("Params = %s", params)
    if type(params["process_embeddings"]) is not bool or type(params["cleanup_old_queries"]) is not bool:
        return "validation_failed"
    if (
        not int(params["days_back"]) > 0
        or not int(params["days_forward"]) > 0
        or not int(params["cleanup_cutoff_days"]) > 0
    ):
        return "validation_failed"
    return "validation_succeeded"


def task_bulk_process_all_users_calendar_events(**airflow_context):
    from django_gen_ai_examples.apps.chat_bot.tasks import bulk_process_all_users_calendar_events

    return bulk_process_all_users_calendar_events(
        days_back=int(airflow_context["params"]["days_back"]),
        days_forward=int(airflow_context["params"]["days_forward"]),
    )


def task_generate_embeddings_for_unprocessed_events(**airflow_context):
    from django_gen_ai_examples.apps.chat_bot.tasks import generate_embeddings_for_unprocessed_events

    if not airflow_context["params"]["process_embeddings"]:
        logger.warning("Skipping embedding generation.")
        raise AirflowSkipException("Embedding generation is disabled in parameters.")

    return generate_embeddings_for_unprocessed_events()


def task_cleanup_old_rag_queries(**airflow_context):
    from django_gen_ai_examples.apps.chat_bot.tasks import cleanup_old_rag_queries

    if not airflow_context["params"]["cleanup_old_queries"]:
        logger.warning("Skipping old RAG queries cleanup.")
        raise AirflowSkipException("Old RAG queries cleanup is disabled in parameters.")

    return cleanup_old_rag_queries(cutoff_days=int(airflow_context["params"]["cleanup_cutoff_days"]))


with DAG(
    dag_id="process_calendar_events_bulk",
    schedule=None,
    start_date=pendulum.datetime(2025, 8, 6, tz="UTC"),
    catchup=False,
    tags=["bulk-processing", "google", "calendar-events"],
    params=ParamsDict(
        {
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
            "process_embeddings": Param(
                type="boolean",
                default=True,
                description="Whether to process embeddings for the events",
            ),
            "cleanup_old_queries": Param(
                type="boolean",
                default=True,
                description="Whether to clean up old RAG queries",
            ),
            "cleanup_cutoff_days": Param(
                type="integer",
                minimum=1,
                maximum=365,
                default=1,
                description="Number of days to keep RAG queries (default: 1)",
            ),
        }
    ),
) as dag:

    t_validate_params = BranchPythonOperator(
        task_id="validate_params",
        python_callable=task_validate_params,
        retries=2,
        retry_delay=timedelta(seconds=30),
    )

    t_validation_succeeded = EmptyOperator(
        task_id="validation_succeeded",
    )

    t_validation_failed = BashOperator(
        task_id="validation_failed",
        bash_command="echo 'Validation failed, exiting.' && exit 1",
    )

    t_bulk_process_all_users_calendar_events = PythonOperator(
        task_id="bulk_process_all_users_calendar_events",
        python_callable=task_bulk_process_all_users_calendar_events,
        retries=2,
        retry_delay=timedelta(seconds=30),
    )

    t_generate_embeddings_for_unprocessed_events = PythonOperator(
        task_id="generate_embeddings_for_unprocessed_events",
        python_callable=task_generate_embeddings_for_unprocessed_events,
        retries=2,
        retry_delay=timedelta(seconds=30),
        trigger_rule=TriggerRule.ALL_DONE,
    )

    t_cleanup_old_rag_queries = PythonOperator(
        task_id="cleanup_old_rag_queries",
        python_callable=task_cleanup_old_rag_queries,
        retries=2,
        retry_delay=timedelta(seconds=30),
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # Happy path:
    (
        t_validate_params
        >> t_validation_succeeded
        >> t_bulk_process_all_users_calendar_events
        >> t_generate_embeddings_for_unprocessed_events
        >> t_cleanup_old_rag_queries
    )

    # Broken path:
    t_validate_params >> t_validation_failed
