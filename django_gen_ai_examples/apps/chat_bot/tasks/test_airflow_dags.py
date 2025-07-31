"""
Tasks related to testing Airflow DAGs
"""

import logging

logger = logging.getLogger(__name__)


def test_airflow_dag():
    "Test Django <> Airflow connection by triggering a simple DAG"
    logger.warning("This is a test task for Airflow DAG")

    return "Test completed successfully."
