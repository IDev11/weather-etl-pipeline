SELECT
    city,
    country,
    DATE_TRUNC('month', date)                 AS month,
    EXTRACT(YEAR FROM date)::int              AS year,
    EXTRACT(MONTH FROM date)::int             AS month_num,
    ROUND(AVG(temperature_max)::numeric, 1)   AS avg_temp_max,
    ROUND(AVG(temperature_min)::numeric, 1)   AS avg_temp_min,
    ROUND(AVG(temperature_mean)::numeric, 1)  AS avg_temp_mean,
    ROUND(AVG(apparent_temp_max)::numeric, 1) AS avg_apparent_temp_max,
    ROUND(AVG(humidity_max_pct)::numeric, 0)  AS avg_humidity_pct,
    ROUND(SUM(precipitation_mm)::numeric, 1)  AS total_precipitation_mm,
    ROUND(SUM(snowfall_mm)::numeric, 1)       AS total_snowfall_mm,
    COUNT(*)                                  AS days_recorded,
    SUM(CASE WHEN is_heat_wave_day THEN 1 ELSE 0 END) AS heat_wave_days
FROM {{ ref('mart_daily_weather') }}
GROUP BY city, country, DATE_TRUNC('month', date),
         EXTRACT(YEAR FROM date)::int, EXTRACT(MONTH FROM date)::int
ORDER BY city, month
