-- Daily weather enriched with an absolute heat category (for display) and a
-- CLIMATE-RELATIVE heat-wave-day flag based on each city's local threshold.
SELECT
    s.*,
    CASE
        WHEN s.temperature_max >= 40 THEN 'Extreme Heat'
        WHEN s.temperature_max >= 35 THEN 'Very Hot'
        WHEN s.temperature_max >= 28 THEN 'Hot'
        WHEN s.temperature_max >= 20 THEN 'Warm'
        WHEN s.temperature_max >= 10 THEN 'Mild'
        WHEN s.temperature_max >= 0  THEN 'Cold'
        ELSE 'Freezing'
    END AS heat_category,
    c.heat_threshold,
    (s.temperature_max >= c.heat_threshold) AS is_heat_wave_day,
    ROUND((s.apparent_temp_max - s.temperature_max)::numeric, 1) AS feels_like_gap_c
FROM {{ ref('stg_weather_stats') }} s
JOIN {{ ref('int_city_climatology') }} c
    ON s.city = c.city
   AND EXTRACT(MONTH FROM s.date)::int = c.month_num
