from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow/project")

DATA_DIR = Path("/opt/airflow/data")
RAW_PATH = DATA_DIR / "weather_raw.parquet"
CLEAN_PATH = DATA_DIR / "weather_clean.parquet"
PG_URL = "postgresql+psycopg2://airflow:airflow@postgres/weather_db"
DBT_DIR = "/opt/airflow/project/dbt"


def alert_on_failure(context):
    """Failure callback. Logs a clear alert and is ready to wire to Slack/webhook.

    To enable real notifications, POST to your webhook here, e.g.:
        import os, requests
        requests.post(os.environ["SLACK_WEBHOOK_URL"], json={"text": msg})
    """
    ti = context.get("task_instance")
    dag_id = context.get("dag").dag_id if context.get("dag") else "unknown"
    msg = (
        f"[ALERT] Airflow task FAILED: {dag_id}.{ti.task_id} "
        f"(run_id={ti.run_id}, try={ti.try_number}). Check logs."
    )
    print(msg)


def _extract(**context):
    from etl.extract import extract

    params = context.get("params", {})
    # Anchor on the run's logical date so scheduled/backfill runs pull the right
    # window; a 7-day trailing window absorbs the archive API's ~5-day lag and
    # late-arriving corrections. A manual `conf` override always wins.
    anchor = context["data_interval_end"].date()
    end_date = params.get("end_date") or (anchor - timedelta(days=1)).isoformat()
    start_date = params.get("start_date") or (anchor - timedelta(days=7)).isoformat()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = extract(start_date=start_date, end_date=end_date)
    df.to_parquet(RAW_PATH, index=False)


def _transform():
    import pandas as pd

    from etl.transform import transform

    df = pd.read_parquet(RAW_PATH)
    clean = transform(df)
    clean.to_parquet(CLEAN_PATH, index=False)


def _load():
    import pandas as pd

    from etl.load import load

    df = pd.read_parquet(CLEAN_PATH)
    load(df, pg_url=PG_URL)


def _quality_check():
    from etl.quality import run_checks

    run_checks(PG_URL)


default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": alert_on_failure,
    # To enable email alerts, configure SMTP in the Airflow env and set:
    #   "email": ["you@example.com"], "email_on_failure": True,
}

with DAG(
    dag_id="weather_etl",
    default_args=default_args,
    description="Daily weather ETL: Open-Meteo → Postgres → dbt marts → Grafana",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["weather", "etl"],
    params={
        "start_date": Param(
            default="",
            type="string",
            description="Override start date (YYYY-MM-DD). Defaults to 7 days before the run's logical date.",
        ),
        "end_date": Param(
            default="",
            type="string",
            description="Override end date (YYYY-MM-DD). Defaults to the run's logical date minus 1 day.",
        ),
    },
) as dag:

    extract = PythonOperator(task_id="extract", python_callable=_extract)
    transform = PythonOperator(task_id="transform", python_callable=_transform)
    load = PythonOperator(task_id="load", python_callable=_load)
    quality_check = PythonOperator(task_id="quality_check", python_callable=_quality_check)
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir .",
    )
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir .",
    )

    extract >> transform >> load >> quality_check >> dbt_run >> dbt_test
