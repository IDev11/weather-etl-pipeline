import pandas as pd
from sqlalchemy import create_engine, text

from etl.extract import CITIES

EXPECTED_CITIES = {c["name"] for c in CITIES}
EXPECTED_CITY_COUNT = len(EXPECTED_CITIES)


class DataQualityError(Exception):
    pass


def run_checks(pg_url: str) -> None:
    engine = create_engine(pg_url)
    failures = []

    with engine.connect() as conn:
        row_count = conn.execute(text("SELECT COUNT(*) FROM raw.weather_stats")).scalar()
        if row_count == 0:
            failures.append("Table is empty")

        city_count = conn.execute(
            text("SELECT COUNT(DISTINCT city) FROM raw.weather_stats")
        ).scalar()
        if city_count < EXPECTED_CITY_COUNT:
            present = {
                r[0] for r in conn.execute(text("SELECT DISTINCT city FROM raw.weather_stats"))
            }
            missing = EXPECTED_CITIES - present
            failures.append(f"Missing cities ({len(missing)}): {', '.join(sorted(missing))}")

        null_count = conn.execute(
            text("SELECT COUNT(*) FROM raw.weather_stats WHERE city IS NULL OR date IS NULL")
        ).scalar()
        if null_count > 0:
            failures.append(f"Null city or date in {null_count} rows")

        max_date = conn.execute(text("SELECT MAX(date) FROM raw.weather_stats")).scalar()
        if max_date is None or (pd.Timestamp.now().date() - max_date).days > 5:
            failures.append(f"Data appears stale: latest date is {max_date}")

        bad_temps = conn.execute(
            text(
                "SELECT COUNT(*) FROM raw.weather_stats "
                "WHERE temperature_max < -80 OR temperature_max > 60"
            )
        ).scalar()
        if bad_temps > 0:
            failures.append(f"Implausible temperature_max values in {bad_temps} rows")

        negative_precip = conn.execute(
            text("SELECT COUNT(*) FROM raw.weather_stats WHERE precipitation_mm < 0")
        ).scalar()
        if negative_precip > 0:
            failures.append(f"Negative precipitation in {negative_precip} rows")

        duplicates = conn.execute(
            text(
                "SELECT COUNT(*) FROM ("
                "  SELECT city, date FROM raw.weather_stats"
                "  GROUP BY city, date HAVING COUNT(*) > 1"
                ") d"
            )
        ).scalar()
        if duplicates > 0:
            failures.append(f"Duplicate (city, date) pairs: {duplicates}")

    engine.dispose()

    if failures:
        raise DataQualityError(
            "Data quality checks failed:\n" + "\n".join(f"  - {f}" for f in failures)
        )

    print(f"All quality checks passed. {row_count:,} rows | {city_count} cities | latest date: {max_date}")
