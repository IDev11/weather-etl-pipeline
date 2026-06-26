import pandas as pd

WMO_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.rename(columns={
        "temperature_2m_max":      "temperature_max",
        "temperature_2m_min":      "temperature_min",
        "temperature_2m_mean":     "temperature_mean",
        "apparent_temperature_max": "apparent_temp_max",
        "apparent_temperature_min": "apparent_temp_min",
        "relative_humidity_2m_max": "humidity_max_pct",
        "precipitation_sum":        "precipitation_mm",
        "snowfall_sum":             "snowfall_mm",
        "wind_speed_10m_max":       "windspeed_max",
        "wind_gusts_10m_max":       "wind_gusts_max",
    }, inplace=True)

    # Drop rows missing city or date — nothing useful can be derived
    df.dropna(subset=["city", "date"], inplace=True)

    # Precipitation and snowfall can't be negative (API sometimes returns -0.0)
    df["precipitation_mm"] = df["precipitation_mm"].clip(lower=0)
    df["snowfall_mm"] = df["snowfall_mm"].clip(lower=0)

    # Humidity is a percentage — clamp to valid range, store as nullable int
    # (matches the SMALLINT column; NaN becomes proper NULL instead of failing the cast)
    df["humidity_max_pct"] = (
        df["humidity_max_pct"].clip(lower=0, upper=100).round().astype("Int64")
    )

    # Derived columns
    df["temperature_range"] = (df["temperature_max"] - df["temperature_min"]).round(1)
    # Store weather_code as nullable int (matches SMALLINT column; avoids NaN cast errors)
    df["weather_code"] = df["weather_code"].astype("Int64")
    df["weather_description"] = (
        df["weather_code"]
        .map(WMO_DESCRIPTIONS)
        .fillna("Unknown")
    )

    df.drop_duplicates(subset=["city", "date"], keep="last", inplace=True)
    df.sort_values(["city", "date"], inplace=True)

    col_order = [
        "date", "city", "country", "latitude", "longitude",
        "temperature_max", "temperature_min", "temperature_mean", "temperature_range",
        "apparent_temp_max", "apparent_temp_min",
        "humidity_max_pct",
        "precipitation_mm", "snowfall_mm",
        "windspeed_max", "wind_gusts_max",
        "weather_code", "weather_description",
    ]
    df = df[col_order].reset_index(drop=True)

    print(f"Transformed {len(df):,} rows across {df['city'].nunique()} cities.")
    return df
