"""
Airflow DAG for testing LLM+RAG Queries on Google Calendar events.
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


def task_validate_params(**airflow_context):
    from django_gen_ai_examples.apps.chat_bot.tasks import validate_user_email

    params = airflow_context["params"]
    logger.info("Params = %s", params)

    if (
        params["user_email"]
        and params["query"]
        and isinstance(params["include_attachments"], bool)
        and isinstance(params["date_range_limit"], int)
        and validate_user_email(params["user_email"])
    ):
        return "validation_succeeded"
    return "validation_failed"


def perform_llm_rag_query(**airflow_context):
    from django_gen_ai_examples.apps.chat_bot.services.llm_service import google_llm_service

    params = airflow_context["params"]
    logger.info("Performing LLM+RAG query with params: %s", params)

    # Collect streaming response
    full_response = ""
    events_found = 0
    model_used = ""
    response_time_ms = 0
    events = []
    similarity_scores = []
    chunk_count = 0

    for event_type, data in google_llm_service.generate_calendar_response(
        user_email=params["user_email"],
        query=params["query"],
        include_attachments=params["include_attachments"],
        date_range_days=params["date_range_limit"],
    ):
        if event_type == "status":
            logger.info("Status: %s", data.get("message", ""))

        elif event_type == "chunk":
            chunk_text = data.get("text", "")
            full_response += chunk_text
            chunk_count += 1
            logger.info("Chunk %d: %s", chunk_count, chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text)

        elif event_type == "complete":
            events_found = data.get("events_found", 0)
            model_used = data.get("model_used", "")
            response_time_ms = data.get("response_time_ms", 0)
            events = data.get("events", [])
            similarity_scores = data.get("similarity_scores", [])
            full_response = data.get("response", full_response)  # Use complete response if available
            break

    logger.info("Final Response: %s", full_response)
    logger.info("Total Events Found: %d", events_found)
    logger.info("Model Used: %s", model_used)
    logger.info("Response Time: %d ms", response_time_ms)
    logger.info("Total Chunks Received: %d", chunk_count)

    # Show found events:
    if events:
        logger.info("Retrieved Events:")
        for i, (event, score) in enumerate(zip(events, similarity_scores), 1):
            logger.info(
                f"{i}. {event.summary} "
                f"({event.start_datetime.strftime('%Y-%m-%d %H:%M')}) "
                f"- Similarity: {score:.3f}"
            )


with DAG(
    dag_id="test_calendar_llm_rag",
    schedule=None,
    start_date=pendulum.datetime(2025, 8, 6, tz="UTC"),
    catchup=False,
    tags=["RAG", "calendar-events", "prompts"],
    params=ParamsDict(
        {
            "user_email": Param(
                type=["null", "string"],
                format="idn-email",
                default="saravanan.ramanathan@kellton.com",
                description="Email of the user whose calendar events we want to fetch",
            ),
            "query": Param(
                type=["null", "string"],
                default="What are my events for today?",
                description="Query about calendar events",
            ),
            "include_attachments": Param(
                type="boolean",
                default=True,
                description="Whether to include attachments in the search",
            ),
            "date_range_limit": Param(
                type="integer",
                minimum=1,
                maximum=365,
                default=2,
                description="Number of days to limit the search for calendar events",
            ),
        }
    ),
) as dag:

    t_validate_params = BranchPythonOperator(
        task_id="validate_params",
        python_callable=task_validate_params,
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

    t_perform_llm_rag_query = PythonOperator(
        task_id="perform_llm_rag_query",
        python_callable=perform_llm_rag_query,
        trigger_rule=TriggerRule.ALL_SUCCESS,
        retries=0,
        retry_delay=timedelta(seconds=20),
    )

    # Happy path:
    (t_validate_params >> t_validation_succeeded >> t_perform_llm_rag_query)

    # Broken path:
    t_validate_params >> t_validation_failed
