"""
DAG to list Google Calendar events.
Testing: gcd Domain-Wide Delegation, Trying to pull in all users' calendars.
NOTE: Domain-Wide Delegation perms needed for this to work.
"""

import logging

import pendulum
from airflow.models.dag import DAG
from airflow.providers.google.suite.hooks.calendar import GoogleCalendarHook
from airflow.providers.standard.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# A list of users whose calendars we want to access.
# The Idea is: service account can now impersonate any of the users within organization.
# This can later come from an API endpoint directory.
USER_EMAILS = [
    "saravanan.ramanathan@kellton.com",
]


def fetch_and_process_events_for_user(user_email: str):
    """
    Impersonates a user and fetches their calendar events.
    """
    logger.info("Starting to fetch calendar details for user: %s", user_email)

    hook = GoogleCalendarHook(
        api_version="v3",
        gcp_conn_id="google_calendar",  # Airflow Admin Connection ID
        impersonation_chain=[user_email],
    )

    # Get the authenticated Google Calendar API service object.
    # connection should already set setup in Airflow Admin.
    service = hook.get_conn()

    events_result = (
        service.events()
        .list(
            calendarId="primary",  # main calendar of the Impersonated user
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])

    if not events:
        logger.warning("No upcoming events found for %s.", user_email)
        return

    logger.info("Found %d events for %s:", len(events), user_email)
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        summary = event["summary"]
        logger.info("- %s: %s", start, summary)

        # PULL in more info as needed.
        # save data to pg-vector.
        # ADD RAG logic.


with DAG(
    dag_id="domain_wide_calendar_rag_etl",
    schedule="0 5 * * *",  # Daily at 5 AM
    start_date=pendulum.datetime(2025, 8, 1, tz="UTC"),
    catchup=False,
    tags=["google", "calendar", "rag", "domain_wide"],
) as dag:

    fetch_events_task = PythonOperator.partial(
        task_id="fetch_events_for_user",
        python_callable=fetch_and_process_events_for_user,
    ).expand(op_args=[[email] for email in USER_EMAILS])
