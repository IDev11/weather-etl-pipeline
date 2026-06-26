-- Per-city, per-calendar-month climatological baseline.
-- A heat wave should be RELATIVE to local climate: 35°C is ordinary in Dubai
-- but extreme in London. We define the local "hot day" threshold as the 90th
-- percentile of daily max temperature for that city and calendar month, floored
-- at 28°C so cold-season warm spells aren't mislabelled as heat waves.
SELECT
    city,
    EXTRACT(MONTH FROM date)::int AS month_num,
    ROUND(
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY temperature_max)::numeric, 1
    ) AS p90_temp_max,
    GREATEST(
        ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY temperature_max)::numeric, 1),
        28
    ) AS heat_threshold
FROM {{ ref('stg_weather_stats') }}
WHERE temperature_max IS NOT NULL
GROUP BY city, EXTRACT(MONTH FROM date)::int
