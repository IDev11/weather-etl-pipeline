import time
from datetime import date, timedelta

import pandas as pd
import requests

CITIES = [
    {"name": "New York",     "country": "US", "lat":  40.71, "lon":  -74.01},
    {"name": "London",       "country": "GB", "lat":  51.51, "lon":   -0.13},
    {"name": "Paris",        "country": "FR", "lat":  48.85, "lon":    2.35},
    {"name": "Tokyo",        "country": "JP", "lat":  35.68, "lon":  139.69},
    {"name": "Dubai",        "country": "AE", "lat":  25.20, "lon":   55.27},
    {"name": "Sydney",       "country": "AU", "lat": -33.87, "lon":  151.21},
    {"name": "Cairo",        "country": "EG", "lat":  30.06, "lon":   31.25},
    {"name": "Mumbai",       "country": "IN", "lat":  19.08, "lon":   72.88},
    {"name": "Sao Paulo",    "country": "BR", "lat": -23.55, "lon":  -46.63},
    {"name": "Lagos",        "country": "NG", "lat":   6.45, "lon":    3.40},
    {"name": "Moscow",       "country": "RU", "lat":  55.75, "lon":   37.62},
    {"name": "Beijing",      "country": "CN", "lat":  39.91, "lon":  116.39},
    {"name": "Los Angeles",  "country": "US", "lat":  34.05, "lon": -118.24},
    {"name": "Berlin",       "country": "DE", "lat":  52.52, "lon":   13.40},
    {"name": "Toronto",      "country": "CA", "lat":  43.70, "lon":  -79.42},
    {"name": "Nairobi",      "country": "KE", "lat":  -1.29, "lon":   36.82},
    {"name": "Buenos Aires", "country": "AR", "lat": -34.60, "lon":  -58.38},
    {"name": "Seoul",        "country": "KR", "lat":  37.57, "lon":  126.98},
    {"name": "Mexico City",  "country": "MX", "lat":  19.43, "lon":  -99.13},
    {"name": "Algiers",      "country": "DZ", "lat":  36.74, "lon":    3.06},
]

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "relative_humidity_2m_max",
    "precipitation_sum",
    "snowfall_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "weather_code",
]

API_URL = "https://archive-api.open-meteo.com/v1/archive"

# Open-Meteo's free tier rate-limits by request "weight" (date range × variables).
# Space requests out and back off on 429 so large backfills don't get throttled.
REQUEST_DELAY_SEC = 1.5
MAX_RETRIES = 5


def _fetch_city(city: dict, start_date: str, end_date: str) -> pd.DataFrame:
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_VARS),
        "timezone": "UTC",
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(API_URL, params=params, timeout=60)
        except requests.exceptions.ConnectionError as exc:
            # Transient container/network blip — back off and retry instead of failing the task
            wait = min(60, 2 ** attempt)
            print(f"  Connection error on {city['name']} (attempt {attempt}); waiting {wait}s... ({exc})")
            time.sleep(wait)
            continue
        if resp.status_code == 429:
            # Honor the server's Retry-After header when present; otherwise exponential backoff
            retry_after = resp.headers.get("Retry-After")
            wait = int(retry_after) if retry_after and retry_after.isdigit() else min(60, 2 ** attempt)
            print(f"  Rate limited on {city['name']} (attempt {attempt}); waiting {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return pd.DataFrame(resp.json()["daily"])
    raise RuntimeError(f"Gave up on {city['name']} after {MAX_RETRIES} retries (rate limit / network).")


def extract(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    if end_date is None:
        end_date = (date.today() - timedelta(days=1)).isoformat()
    if start_date is None:
        start_date = (date.today() - timedelta(days=7)).isoformat()

    frames = []
    for city in CITIES:
        df = _fetch_city(city, start_date, end_date)
        df["city"] = city["name"]
        df["country"] = city["country"]
        df["latitude"] = city["lat"]
        df["longitude"] = city["lon"]
        frames.append(df)
        time.sleep(REQUEST_DELAY_SEC)

    result = pd.concat(frames, ignore_index=True)
    result["time"] = pd.to_datetime(result["time"])
    result.rename(columns={"time": "date"}, inplace=True)
    print(f"Extracted {len(result):,} rows for {len(CITIES)} cities ({start_date} to {end_date}).")
    return result
