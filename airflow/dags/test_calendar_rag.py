"""
Airflow DAG for testing CalendarRAGService methods.
Tests query_calendar_events and get_context_for_llm functionality.
"""

import logging
from datetime import timedelta

import django_bootstrap
import pendulum
from airflow import DAG
from airflow.models.param import ParamsDict
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from airflow.sdk import Param
from airflow.utils.trigger_rule import TriggerRule

logger = logging.getLogger(__name__)


def task_validate_params(**airflow_context):
    """Validate input parameters for the RAG test."""
    from django_gen_ai_examples.apps.chat_bot.tasks import validate_user_email

    params = airflow_context["params"]
    logger.info("Validating params: %s", params)

    if (
        params["user_email"]
        and params["query"]
        and isinstance(params["include_attachments"], bool)
        and isinstance(params["date_range_days"], int)
        and isinstance(params["similarity_threshold"], (int, float))
        and isinstance(params["max_results"], int)
        and validate_user_email(params["user_email"])
    ):
        logger.info("Validation succeeded")
        return "validation_succeeded"

    logger.error("Validation failed")
    return "validation_failed"


def task_test_rag_service(**airflow_context):
    """Test both CalendarRAGService.query_calendar_events and get_context_for_llm methods."""
    from django_gen_ai_examples.apps.chat_bot.services.rag_service import calendar_rag_service

    params = airflow_context["params"]
    logger.info("Testing CalendarRAGService methods with params: %s", params)

    # Test 1: query_calendar_events
    logger.info("=== TESTING QUERY_CALENDAR_EVENTS ===")
    events, scores, rag_query = calendar_rag_service.query_calendar_events(
        user_email=params["user_email"],
        query_text=params["query"],
        include_attachments=params["include_attachments"],
        date_range_days=params["date_range_days"],
        similarity_threshold=params["similarity_threshold"],
        max_results=params["max_results"],
    )

    # Log detailed results
    logger.info(f"Query: {params['query']}")
    logger.info(f"User: {params['user_email']}")
    logger.info(f"Events found: {len(events)}")
    logger.info(f"RAG Query ID: {rag_query.pk if rag_query else 'None'}")

    if events:
        logger.info("Retrieved Events with Similarity Scores:")
        for i, (event, score) in enumerate(zip(events, scores), 1):
            logger.info(
                f"{i}. [{score:.3f}] {event.summary or 'No Title'} "
                f"({event.start_datetime.strftime('%Y-%m-%d %H:%M')})"
            )
            if event.description:
                logger.info(f"    Description: {event.description[:100]}...")
            if event.location:
                logger.info(f"    Location: {event.location}")

            # Check for attachments
            attachments = event.attachments.filter(processing_status="completed")
            if attachments.exists():
                logger.info(f"    Attachments: {[att.file_name for att in attachments]}")
    else:
        logger.warning("No events found for the query")

    # Test 2: get_context_for_llm
    logger.info("=== TESTING GET_CONTEXT_FOR_LLM ===")
    context = calendar_rag_service.get_context_for_llm(events, scores)

    logger.info(f"Context length: {len(context)} characters")
    logger.info("Generated context:")
    logger.info(context)
    logger.info("=== END CONTEXT ===")

    # Return combined results
    return {
        "query_test": {
            "events_count": len(events),
            "query_successful": True,
            "rag_query_id": rag_query.pk if rag_query else None,
            "similarity_scores": scores,
            "has_events": len(events) > 0,
        },
        "context_test": {
            "context_length": len(context),
            "events_included": len(events),
            "context_generated": True,
            "context_preview": context[:200] + "..." if len(context) > 200 else context,
        },
    }


def task_test_user_calendar_summary(**airflow_context):
    """Test the CalendarRAGService.get_user_calendar_summary method."""
    from django_gen_ai_examples.apps.chat_bot.services.rag_service import calendar_rag_service

    params = airflow_context["params"]
    logger.info("Testing get_user_calendar_summary method")

    # Test the summary method
    summary = calendar_rag_service.get_user_calendar_summary(
        user_email=params["user_email"], days_ahead=params.get("summary_days_ahead", 0)
    )

    logger.info("=== USER CALENDAR SUMMARY ===")
    logger.info(f"Summary: {summary}")

    if "error" not in summary:
        logger.info(f"Total upcoming events: {summary['total_events']}")
        logger.info(f"Period: {summary['period']}")

        if summary["events"]:
            logger.info("Upcoming events:")
            for i, event in enumerate(summary["events"][:5], 1):
                logger.info(f"{i}. {event['title']} - {event['start']}")
    else:
        logger.error(f"Summary error: {summary['error']}")

    return summary


with DAG(
    dag_id="test_calendar_rag",
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
                description="Email of the user whose calendar events to search",
            ),
            "query": Param(
                type=["null", "string"],
                default="meeting",
                description="Search query for calendar events",
            ),
            "include_attachments": Param(
                type="boolean",
                default=True,
                description="Whether to include attachments in the search",
            ),
            "date_range_days": Param(
                type="integer",
                minimum=1,
                maximum=365,
                default=30,
                description="Number of days to search (from today backwards)",
            ),
            "similarity_threshold": Param(
                type="number",
                minimum=0.0,
                maximum=1.0,
                default=0.35,
                description="Minimum similarity threshold (0.0 to 1.0)",
            ),
            "max_results": Param(
                type="integer",
                minimum=1,
                maximum=50,
                default=10,
                description="Maximum number of results to return",
            ),
            "summary_days_ahead": Param(
                type="integer",
                minimum=0,
                maximum=30,
                default=0,
                description="Days ahead for calendar summary",
            ),
        }
    ),
) as dag:

    # Validation step
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
        bash_command="echo 'Parameter validation failed, exiting.' && exit 1",
    )

    # Main testing tasks
    t_test_rag_service = PythonOperator(
        task_id="test_rag_service",
        python_callable=task_test_rag_service,
        trigger_rule=TriggerRule.ALL_SUCCESS,
        retries=1,
        retry_delay=timedelta(seconds=30),
    )

    t_test_calendar_summary = PythonOperator(
        task_id="test_user_calendar_summary",
        python_callable=task_test_user_calendar_summary,
        trigger_rule=TriggerRule.ALL_SUCCESS,
        retries=1,
        retry_delay=timedelta(seconds=30),
    )

    # Happy path:
    (t_validate_params >> t_validation_succeeded >> t_test_rag_service >> t_test_calendar_summary)

    # Broken path:
    t_validate_params >> t_validation_failed
