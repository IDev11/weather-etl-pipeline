"""Local runner — use this to test the pipeline without Airflow."""
import argparse
from datetime import date, timedelta

from etl.extract import extract
from etl.load import load
from etl.quality import run_checks
from etl.transform import transform

DB_PATH = "data/weather.duckdb"


def run(start_date: str, end_date: str) -> None:
    print(f"=== Weather ETL Pipeline ({start_date} to {end_date}) ===")
    raw = extract(start_date=start_date, end_date=end_date)
    clean = transform(raw)
    load(clean, db_path=DB_PATH)
    run_checks(db_path=DB_PATH)
    print("=== Pipeline complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=(date.today() - timedelta(days=7)).isoformat())
    parser.add_argument("--end", default=(date.today() - timedelta(days=1)).isoformat())
    args = parser.parse_args()
    run(args.start, args.end)
