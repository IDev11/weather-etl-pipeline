-- Heat wave episodes: 3+ consecutive days at or above the city's LOCAL climate
-- threshold (see int_city_climatology). Uses the "islands" technique — the gap
-- between two row numbers is constant for a run of consecutive flagged days.
WITH flagged AS (
    SELECT
        city,
        country,
        date,
        temperature_max,
        heat_threshold,
        is_heat_wave_day,
        ROW_NUMBER() OVER (PARTITION BY city ORDER BY date)
          - ROW_NUMBER() OVER (PARTITION BY city, is_heat_wave_day ORDER BY date)
            AS island_grp
    FROM {{ ref('mart_daily_weather') }}
    WHERE temperature_max IS NOT NULL
)

SELECT
    city,
    country,
    MIN(date)                                AS wave_start,
    MAX(date)                                AS wave_end,
    COUNT(*)                                 AS duration_days,
    ROUND(MAX(temperature_max)::numeric, 1)  AS peak_temp_c,
    ROUND(AVG(temperature_max)::numeric, 1)  AS avg_temp_c,
    ROUND(MAX(heat_threshold)::numeric, 1)   AS local_threshold_c
FROM flagged
WHERE is_heat_wave_day
GROUP BY city, country, island_grp
HAVING COUNT(*) >= 3
ORDER BY city, wave_start
