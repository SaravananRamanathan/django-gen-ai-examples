FROM python:3.11-slim

LABEL maintainer Tivix <saravanan.ramanathan@kellton.com>
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code/

RUN apt-get update &&\
    apt-get install --yes --no-install-recommends \
    gnupg \
    curl \
    gcc \
    make \
    postgresql \
    linux-libc-dev \
    libc6-dev \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    build-essential \
    python3-dev \
    && \
    rm -rf /var/lib/apt/lists/* &&\
    pip3 install --no-cache --disable-pip-version-check --progress-bar off --upgrade pip

COPY requirements/base.txt /temp/
RUN pip3 install --no-cache --disable-pip-version-check --progress-bar off -r /temp/base.txt

COPY ./ ./
