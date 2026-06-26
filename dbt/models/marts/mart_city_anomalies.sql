-- Current month-to-date vs the historical average for the SAME calendar month
-- AND the same days-of-month. Comparing 8 days of June against full historical
-- Junes is unfair; we instead compare June 1-8 this year against June 1-8 in
-- prior years. Positive temp_anomaly_c means warmer than the historical norm.
WITH latest AS (
    SELECT MAX(date) AS max_date FROM {{ ref('stg_weather_stats') }}
),

bounds AS (
    SELECT
        max_date,
        DATE_TRUNC('month', max_date)        AS cur_month,
        EXTRACT(MONTH FROM max_date)::int     AS cur_month_num,
        EXTRACT(DAY FROM max_date)::int       AS cur_dom
    FROM latest
),

daily AS (
    SELECT
        city,
        country,
        date,
        temperature_max,
        precipitation_mm,
        DATE_TRUNC('month', date)        AS month,
        EXTRACT(MONTH FROM date)::int     AS month_num,
        EXTRACT(DAY FROM date)::int       AS dom,
        EXTRACT(YEAR FROM date)::int      AS year
    FROM {{ ref('stg_weather_stats') }}
),

current_month AS (
    SELECT
        d.city,
        d.country,
        b.cur_month                                 AS month,
        ROUND(AVG(d.temperature_max)::numeric, 1)   AS current_avg_temp_max,
        ROUND(AVG(d.precipitation_mm)::numeric, 1)  AS current_avg_precip_mm,
        MAX(d.dom)                                  AS days_counted
    FROM daily d
    CROSS JOIN bounds b
    WHERE d.month = b.cur_month
    GROUP BY d.city, d.country, b.cur_month
),

historical_baseline AS (
    SELECT
        d.city,
        ROUND(AVG(d.temperature_max)::numeric, 1)   AS hist_avg_temp_max,
        ROUND(AVG(d.precipitation_mm)::numeric, 1)  AS hist_avg_precip_mm,
        COUNT(DISTINCT d.year)                      AS years_of_data
    FROM daily d
    CROSS JOIN bounds b
    WHERE d.month_num = b.cur_month_num
      AND d.dom <= b.cur_dom          -- same days-of-month for a fair comparison
      AND d.month <> b.cur_month      -- exclude the current (partial) month
    GROUP BY d.city
)

SELECT
    c.city,
    c.country,
    c.month,
    c.days_counted,
    c.current_avg_temp_max,
    h.hist_avg_temp_max,
    ROUND((c.current_avg_temp_max - h.hist_avg_temp_max)::numeric, 1)   AS temp_anomaly_c,
    c.current_avg_precip_mm,
    h.hist_avg_precip_mm,
    ROUND((c.current_avg_precip_mm - h.hist_avg_precip_mm)::numeric, 1) AS precip_anomaly_mm,
    h.years_of_data
FROM current_month c
JOIN historical_baseline h ON c.city = h.city
ORDER BY temp_anomaly_c DESC
