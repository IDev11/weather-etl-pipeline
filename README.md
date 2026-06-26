# Weather ETL Pipeline

End-to-end data engineering pipeline that ingests daily weather data for 20 global cities, models it with dbt, and surfaces it in a live Grafana dashboard — with climate-relative heat wave detection.

## Stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow 2.9 |
| Storage | PostgreSQL 15 |
| Transformation | dbt-postgres |
| Visualization | Grafana 10.4 |
| Containerization | Docker + Docker Compose |
| Data Source | Open-Meteo Archive API (free, no key) |

## Architecture

```
Open-Meteo API
     │
     ▼
[extract]  →  weather_raw.parquet
     │
     ▼
[transform] →  weather_clean.parquet
     │
     ▼
[load]  →  PostgreSQL: raw.weather_stats
     │
     ▼
[quality_check]  (7 data quality assertions)
     │
     ▼
[dbt_run]  →  PostgreSQL: weather.*
     │             ├── int_city_climatology
     │             ├── mart_daily_weather
     │             ├── mart_heat_waves
     │             ├── mart_monthly_averages
     │             └── mart_city_anomalies
     ▼
[dbt_test]  (schema + data tests)
     │
     ▼
Grafana Dashboard
```

## Cities Covered

New York · London · Paris · Tokyo · Dubai · Sydney · Cairo · Mumbai · São Paulo · Lagos · Moscow · Beijing · Los Angeles · Berlin · Toronto · Nairobi · Buenos Aires · Seoul · Mexico City · Algiers

## Weather Variables

Temperature (max/min/mean) · Apparent temperature · Humidity · Precipitation · Snowfall · Wind speed · Wind gusts · Weather code/description

## Key Features

### Climate-Relative Heat Wave Detection
Heat waves are defined relative to each city's local climate — not a fixed global threshold. The pipeline computes each city's **90th-percentile daily max temperature per calendar month** as the hot-day threshold (floored at 28°C). A 30°C day correctly flags as a heat wave in London but not in Dubai.

### Idempotent Loads
Every run deletes the loaded date range before re-inserting. Re-running a DAG never creates duplicates.

### Partial-Month Fair Anomaly Comparison
The anomaly model compares the current month's first N days against the historical average for the **same N days** of prior years — not against full historical months.

### Data Quality Gate
7 checks run after every load and block downstream tasks on failure:
- Row count > 0
- All 20 cities present
- No null city or date
- Latest date within 5 days of today
- Temperature values in plausible range (−80°C to 60°C)
- No negative precipitation
- No duplicate (city, date) pairs

### dbt Tests
`dbt test` runs as a DAG task after `dbt run`, validating `not_null`, `unique`, and `accepted_values` constraints on every mart.

## Project Structure

```
.
├── Dockerfile                          # Bakes dbt-postgres deps into Airflow image
├── docker-compose.yml                  # Airflow + PostgreSQL + Grafana
├── init-db.sh                          # Creates weather_db on first Postgres boot
├── requirements-airflow.txt            # Pinned deps for the Docker image
├── requirements.txt                    # Local dev deps
│
├── dags/
│   └── weather_etl_dag.py             # Airflow DAG (6 tasks, @daily schedule)
│
├── etl/
│   ├── extract.py                      # Open-Meteo API fetch with rate-limit retry
│   ├── transform.py                    # Rename, clean, clip, WMO descriptions
│   ├── load.py                         # Idempotent upsert to raw.weather_stats
│   └── quality.py                      # 7 data quality assertions
│
├── dbt/
│   ├── profiles.yml                    # dbt-postgres connection (reads env vars)
│   ├── dbt_project.yml
│   └── models/
│       ├── staging/
│       │   ├── sources.yml             # Points dbt at raw.weather_stats
│       │   ├── stg_weather_stats.sql
│       │   └── schema.yml
│       └── marts/
│           ├── int_city_climatology.sql   # Per-city/month p90 heat threshold
│           ├── mart_daily_weather.sql     # Daily weather + heat category + flag
│           ├── mart_heat_waves.sql        # Heat wave episodes (islands technique)
│           ├── mart_monthly_averages.sql  # Monthly rollups
│           ├── mart_city_anomalies.sql    # Current month vs historical baseline
│           └── schema.yml
│
└── grafana/
    └── provisioning/
        ├── datasources/               # PostgreSQL datasource (auto-provisioned)
        └── dashboards/                # Weather dashboard (auto-provisioned)
```

## Getting Started

**Prerequisites:** Docker Desktop

```bash
git clone https://github.com/IDev11/weather-etl-pipeline.git
cd weather-etl-pipeline

# Build the image (installs dbt-postgres inside Airflow)
docker compose build

# Start the stack
docker compose up -d
```

| Service | URL | Credentials |
|---|---|---|
| Airflow | http://localhost:8080 | admin / admin |
| Grafana | http://localhost:3000 | admin / admin |

### Run the Pipeline

In the Airflow UI, find the `weather_etl` DAG, unpause it, then trigger with config:

```json
{ "start_date": "2024-01-01", "end_date": "2026-06-23" }
```

Or via CLI:

```bash
docker compose exec airflow-scheduler airflow dags trigger weather_etl \
  --conf '{"start_date": "2024-01-01", "end_date": "2026-06-23"}'
```

### Daily Schedule

Once the backfill completes, the DAG runs automatically at midnight UTC and pulls the trailing 7-day window — absorbing the archive API's ~5-day lag.

## Grafana Dashboard

The dashboard auto-provisions on startup and includes:

- **Current Conditions** — table of all 20 cities ranked by temperature
- **Temperature Trends** — 30-day rolling average per city
- **Monthly Heat Wave Days** — bar chart, climate-relative counts
- **Top 10 Longest Heat Waves** — ranked by duration
- **Temperature Anomaly This Month** — current vs historical baseline
- **Hottest City Today** — stat tile
- **Windiest City Today** — stat tile
- **Total Heat Wave Days This Year** — stat tile
- **Wettest City This Month** — stat tile
- **Data Freshness** — days since latest reading (color-coded alert)

## dbt Models

| Model | Type | Description |
|---|---|---|
| `stg_weather_stats` | View | Clean passthrough from `raw.weather_stats` |
| `int_city_climatology` | Table | Per-city/month 90th-percentile temperature baseline |
| `mart_daily_weather` | Table | Daily weather with heat category and local heat-wave flag |
| `mart_heat_waves` | Table | Heat wave episodes (3+ consecutive days above local threshold) |
| `mart_monthly_averages` | Table | Monthly aggregates including heat-wave day counts |
| `mart_city_anomalies` | Table | Current month vs same-days-of-month historical average |
