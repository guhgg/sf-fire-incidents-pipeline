from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import requests
import pandas as pd
import logging
import concurrent.futures
from typing import List, Dict, Any, Optional

API_URL = "https://data.sfgov.org/resource/wr8u-xric.json"
BATCH_SIZE = 5000
MAX_WORKERS = 10
TEMP_FILE = "/tmp/fire_incidents.csv"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 10, 29),
    'catchup': False
}

dag = DAG(
    'sf_fire_incidents_etl',
    default_args=default_args,
    description='ETL pipeline to load SF fire incidents data into PostgreSQL',
    schedule_interval='@daily',
    max_active_runs=1
)


def get_postgres_connection():
    pg_hook = PostgresHook(postgres_conn_id='postgres_warehouse')
    return pg_hook.get_conn()


def execute_query(query: str, params: Optional[List[Any]] = None):
    with get_postgres_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()


def truncate_fact_table():
    execute_query("TRUNCATE TABLE fact_fire_incidents RESTART IDENTITY CASCADE;")
    logging.info("Fact table truncated.")


def fetch_data(offset: int) -> List[Dict[str, Any]]:
    params = {'$limit': BATCH_SIZE, '$offset': offset}
    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Fetched {len(data)} records from offset {offset}")
        return data
    except requests.RequestException as e:
        logging.error(f"Error fetching data for offset {offset}: {e}")
        return []


def extract_data():
    all_data = []
    offset = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            futures = [executor.submit(fetch_data, offset + i * BATCH_SIZE) for i in range(MAX_WORKERS)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            if not any(results):
                logging.info("All data fetched.")
                break
            for batch in results:
                all_data.extend(batch)
            offset += MAX_WORKERS * BATCH_SIZE

    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv(TEMP_FILE, index=False)
        logging.info(f"Extracted {len(all_data)} records successfully.")
    else:
        logging.warning("No data extracted.")


def load_dimensions():
    df = pd.read_csv(TEMP_FILE)

    df['neighborhood_district'] = df['neighborhood_district'].fillna("Unknown")

    with get_postgres_connection() as conn, conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO dim_district (district_name) 
            VALUES (%s) ON CONFLICT (district_name) DO NOTHING
            """,
            [(district,) for district in df['neighborhood_district'].unique()]
        )

        cursor.executemany(
            """
            INSERT INTO dim_battalion (battalion_name)
            VALUES (%s) ON CONFLICT (battalion_name) DO NOTHING
            """,
            [(battalion,) for battalion in df['battalion'].dropna().unique()]
        )

        dates = pd.to_datetime(df['incident_date']).dt.date.unique()
        cursor.executemany(
            """
            INSERT INTO dim_time (call_date, year, month, day, weekday)
            VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
            """, 
            [(d, d.year, d.month, d.day, d.strftime('%A')) for d in dates]
        )
    logging.info("Dimensions loaded successfully.")


def load_fact_table() -> None:
    df = pd.read_csv(TEMP_FILE)
    df = df.where(pd.notnull(df), None)

    with get_postgres_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT district_name, district_key FROM dim_district")
        district_map = dict(cursor.fetchall())

        cursor.execute("SELECT battalion_name, battalion_key FROM dim_battalion")
        battalion_map = dict(cursor.fetchall())

        cursor.execute("SELECT call_date, time_key FROM dim_time")
        time_map = dict(cursor.fetchall())

        fact_rows = [
            (
                int(row['incident_number']),
                time_map.get(pd.to_datetime(row['incident_date']).date()),
                district_map.get(row['neighborhood_district'], district_map.get("Unknown")),
                battalion_map.get(row['battalion']),
                row['zipcode'],
                row['primary_situation'],
                row['estimated_property_loss'],
                row['number_of_alarms'],
                1
            )
            for _, row in df.iterrows()
            if pd.to_datetime(row['incident_date']).date() in time_map and
               row['battalion'] in battalion_map
        ]

        if fact_rows:
            cursor.executemany(
                """
                INSERT INTO fact_fire_incidents (
                    incident_number, time_key, district_key, battalion_key,
                    zipcode, incident_type, property_loss, alarm_count, incident_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (incident_number) DO NOTHING
                """, fact_rows
            )
            logging.info(f"Inserted {len(fact_rows)} rows.")
        else:
            logging.warning("No rows inserted.")


truncate_task = PythonOperator(
    task_id='truncate_fact_table',
    python_callable=truncate_fact_table,
    dag=dag
)

extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    dag=dag
)

load_dimensions_task = PythonOperator(
    task_id='load_dimensions',
    python_callable=load_dimensions,
    dag=dag
)

load_fact_task = PythonOperator(
    task_id='load_fact_table',
    python_callable=load_fact_table,
    dag=dag
)

truncate_task >> extract_task >> load_dimensions_task >> load_fact_task
