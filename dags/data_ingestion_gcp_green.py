import os
from datetime import datetime
from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from data_handling import (read_data, convert_date, check_dtypes_match, save_parquet,
                           upload_to_gcs, create_bigquery_external_table)

# GCP related variables
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
BUCKET = os.environ.get("GCP_GCS_BUCKET")
BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET", 'nytaxi')

# Download file variables
url_prefix = 'https://d37ci6vzurychx.cloudfront.net/trip-data/'
download_date = '{{(execution_date).strftime(\'%Y-%m\')}}'
filename = f'green_tripdata_{download_date}.parquet'
dataset_url = url_prefix + filename

# Save file to local variables
path_to_local_home = os.path.join(os.environ.get("AIRFLOW_HOME", "/opt/airflow"), "data")
output_path = f'{path_to_local_home}/{filename}'

# Required columns and data types
required_columns = {
        'VendorID': 'int64',
        'lpep_pickup_datetime': 'datetime64[ns]',
        'lpep_dropoff_datetime': 'datetime64[ns]',
        'store_and_fwd_flag': 'object',
        'RatecodeID': 'float64',
        'PULocationID': 'int64',
        'DOLocationID': 'int64',
        'passenger_count': 'float64',
        'trip_distance': 'float64',
        'fare_amount': 'float64',
        'extra': 'float64',
        'mta_tax': 'float64',
        'tip_amount': 'float64',
        'tolls_amount': 'float64',
        'ehail_fee': 'object',
        'improvement_surcharge': 'float64',
        'total_amount': 'float64',
        'payment_type': 'float64',
        'trip_type': 'float64',
        'congestion_surcharge': 'float64'
        }

timestamp_columns = ['lpep_pickup_datetime', 'lpep_dropoff_datetime']

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1
}

green_taxi_to_bq_dag = DAG(
    'green_taxi_to_bq_dag',
    description='Pipeline to ingest data of green taxi to bigquery',
    schedule_interval='0 16 5 * *',
    start_date=datetime(2021, 1, 1),
    end_date=datetime(2022, 12, 31),
    tags = ['ingest', 'gcp', 'bigquery','nytaxi','green'],
    concurrency=1,
    max_active_runs=2
)

if not os.path.exists(path_to_local_home):
    os.mkdir(path_to_local_home)

with green_taxi_to_bq_dag:
    download = BashOperator(
        task_id='01_download',
        bash_command=f'curl -sSL {url_prefix}{filename} > {output_path} ',
        do_xcom_push=False,
    )

    read_file = PythonOperator(
        task_id='02_read_file',
        python_callable=read_data,
        op_kwargs={
            "input_fn": filename,
            "path_to_local_home": path_to_local_home,
        },
    )

    convert_file = PythonOperator(
        task_id='03_convert_date',
        python_callable=convert_date,
        op_kwargs={
            'timestamp_columns': timestamp_columns,
        }
    )

    check_dtypes = PythonOperator(
        task_id='04_check_dtypes',
        python_callable=check_dtypes_match,
        op_kwargs={
            'required_columns': required_columns,
        }
    )

    save_file = PythonOperator(
        task_id='04_save_file',
        python_callable=save_parquet,
    )

    local_to_gcs_task = PythonOperator(
        task_id="05_local_to_gcs_task",
        python_callable=upload_to_gcs,
        op_kwargs={
            "bucket": BUCKET,
            "PROJECT_ID": PROJECT_ID,
            "BIGQUERY_DATASET": BIGQUERY_DATASET,
        },
    )

    create_bigquery_external_table_task = PythonOperator(
        task_id='06_create_bigquery_external_table_task',
        python_callable=create_bigquery_external_table,
        provide_context=True,
        op_kwargs={
            "PROJECT_ID": PROJECT_ID,
            "BIGQUERY_DATASET": BIGQUERY_DATASET,
            "datecolumn": timestamp_columns[0],
        },
    )

# Define the task sequence
download >> read_file >> convert_file >> check_dtypes >> save_file >> local_to_gcs_task >> create_bigquery_external_table_task
