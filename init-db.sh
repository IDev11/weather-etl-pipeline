#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE weather_db;
    GRANT ALL PRIVILEGES ON DATABASE weather_db TO $POSTGRES_USER;
EOSQL
