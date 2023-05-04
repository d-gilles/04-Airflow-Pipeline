# First-time build can take upto 10 mins.

FROM apache/airflow:2.2.3

ENV AIRFLOW_HOME=/opt/airflow

USER root
RUN apt-get update -qq && apt-get install vim -qqq

# git gcc g++ -qqq

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install --no-cache-dir pandas sqlalchemy psycopg2-binary

# Ref: https://airflow.apache.org/docs/docker-stack/recipes.html

SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

ARG CLOUD_SDK_VERSION=322.0.0
ENV GCLOUD_HOME=/home/google-cloud-sdk

ENV PATH="${GCLOUD_HOME}/bin/:${PATH}"

RUN DOWNLOAD_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz" \
  && TMP_DIR="$(mktemp -d)" \
  && curl -fL "${DOWNLOAD_URL}" --output "${TMP_DIR}/google-cloud-sdk.tar.gz" \
  && mkdir -p "${GCLOUD_HOME}" \
  && tar xzf "${TMP_DIR}/google-cloud-sdk.tar.gz" -C "${GCLOUD_HOME}" --strip-components=1 \
  && "${GCLOUD_HOME}/install.sh" \
  --bash-completion=false \
  --path-update=false \
  --usage-reporting=false \
  --quiet \
  && rm -rf "${TMP_DIR}" \
  && gcloud --version

WORKDIR $AIRFLOW_HOME

# If some more funtionalety is needed in the container bash,
# then uncomment the following lines:

# RUN apt-get update -qq && apt-get install -y passwd
# RUN echo 'root:root' | chpasswd
# COPY ./scripts .
# RUN chmod +x ./install.sh && ./install.sh

RUN echo 'airflow:airflow' | chpasswd
USER $AIRFLOW_UID
