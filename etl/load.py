import pandas as pd
from sqlalchemy import create_engine, text

# Raw landing table lives in its own schema; dbt reads it as a source and
# builds the analytics marts in the `weather` schema.
DDL_STATEMENTS = [
    "CREATE SCHEMA IF NOT EXISTS raw",
    """
    CREATE TABLE IF NOT EXISTS raw.weather_stats (
        date                DATE             NOT NULL,
        city                VARCHAR          NOT NULL,
        country             VARCHAR          NOT NULL,
        latitude            DOUBLE PRECISION,
        longitude           DOUBLE PRECISION,
        temperature_max     DOUBLE PRECISION,
        temperature_min     DOUBLE PRECISION,
        temperature_mean    DOUBLE PRECISION,
        temperature_range   DOUBLE PRECISION,
        apparent_temp_max   DOUBLE PRECISION,
        apparent_temp_min   DOUBLE PRECISION,
        humidity_max_pct    SMALLINT,
        precipitation_mm    DOUBLE PRECISION,
        snowfall_mm         DOUBLE PRECISION,
        windspeed_max       DOUBLE PRECISION,
        wind_gusts_max      DOUBLE PRECISION,
        weather_code        SMALLINT,
        weather_description VARCHAR,
        PRIMARY KEY (city, date)
    )
    """,
]


def load(df: pd.DataFrame, pg_url: str) -> None:
    engine = create_engine(pg_url)

    min_date = df["date"].min()
    max_date = df["date"].max()

    # Idempotent upsert: delete the date range being loaded, then append.
    # The (city, date) primary key guarantees no duplicates survive.
    with engine.begin() as conn:
        for stmt in DDL_STATEMENTS:
            conn.execute(text(stmt))
        deleted = conn.execute(
            text("DELETE FROM raw.weather_stats WHERE date BETWEEN :start AND :end"),
            {"start": min_date, "end": max_date},
        ).rowcount

    df.to_sql("weather_stats", engine, schema="raw", if_exists="append", index=False)

    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM raw.weather_stats")).scalar()

    engine.dispose()
    print(f"Upserted {len(df):,} rows (replaced {deleted} existing). Table total: {total:,} rows.")
