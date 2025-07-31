FROM python:3.11-slim

LABEL maintainer="Kellton <saravanan.ramanathan@kellton.com>"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Airflow perm fix:
# Create a non-root user with a home directory and a specific UID (50000)
# This user will be used by the 'user:' directive in docker-compose.yml
RUN useradd -ms /bin/bash -u 50000 airflow

WORKDIR /code/

# Install OS-level dependencies:
RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
    gnupg curl gcc make postgresql-client && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install --no-cache --disable-pip-version-check --progress-bar off --upgrade pip

# Reproducible Airflow installation:
ENV AIRFLOW_VERSION=3.0.3
ENV PYTHON_VERSION=3.11
RUN pip install "apache-airflow[celery,postgres,redis]==${AIRFLOW_VERSION}" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
RUN pip install "apache-airflow[celery,postgres,redis]==${AIRFLOW_VERSION}" \
    "apache-airflow-providers-postgres==6.2.1" \
    "apache-airflow-providers-redis==4.1.1" \
    "apache-airflow-providers-celery==3.12.1" \
    "connexion==3.2.0" \
    "Flask-Session==0.8.0" \
    "Flask-AppBuilder==4.8.0"

# Install Django project dependencies
COPY requirements/base.txt /temp/
RUN pip3 install --no-cache --disable-pip-version-check --progress-bar off -r /temp/base.txt


COPY . /code/

# Airflow perm fix:
# Set ownership of the entire /code directory to the airflow user.
# This ensures the non-root user can write logs and configs.
RUN chown -R airflow:airflow /code


# use following to install in venv [* after installing base.txt *] if needed:
# pip install "apache-airflow[celery,postgres,redis]==3.0.3" \
#     --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.0.3/constraints-3.11.txt"
# In similar way install other airflow providers in venv as needed to help with local development.
