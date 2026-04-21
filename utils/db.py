import sqlite3
import pandas as pd
import os

# ── Path to database ──────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'travel.db')


def get_connection():
    """Return a SQLite connection to travel.db"""
    conn = sqlite3.connect(DB_PATH)
    return conn


def run_query(sql: str) -> pd.DataFrame:
    """
    Execute any SQL string and return a DataFrame.
    Used by both pre-built queries AND AI-generated queries.
    """
    try:
        conn = get_connection()
        df   = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame({'error': [str(e)]})


# ════════════════════════════════════════════════════════
# PRE-BUILT ANALYTICAL QUERIES
# Each returns a clean DataFrame ready for charting
# ════════════════════════════════════════════════════════

def query_conversion_funnel() -> pd.DataFrame:
    """
    BUSINESS QUESTION:
    At which funnel step do we lose the most users?
    
    WHY IT MATTERS:
    If 'view→cart' has a 60% drop-off, the product team
    should investigate the property detail page UX.
    If 'cart→booking' drops, it's a pricing/trust issue.
    """
    sql = """
    SELECT 
        event_type                        AS funnel_step,
        COUNT(DISTINCT user_id)           AS unique_users,
        -- Order for sorting in chart
        CASE event_type
            WHEN 'search'  THEN 1
            WHEN 'view'    THEN 2
            WHEN 'cart'    THEN 3
            WHEN 'booking' THEN 4
        END                               AS step_order
    FROM events
    GROUP BY event_type
    ORDER BY step_order
    """
    return run_query(sql)


def query_revenue_by_destination() -> pd.DataFrame:
    """
    BUSINESS QUESTION:
    Which destinations generate the most revenue?
    
    WHY IT MATTERS:
    Pareto effect — top 5 destinations likely drive
    70%+ of revenue. This tells inventory/marketing teams
    where to double down investment.
    """
    sql = """
    SELECT 
        destination,
        COUNT(*)                                        AS total_bookings,
        ROUND(SUM(total_price), 2)                      AS total_revenue,
        ROUND(AVG(total_price), 2)                      AS avg_booking_value,
        ROUND(SUM(total_price) * 100.0 / 
              (SELECT SUM(total_price) FROM bookings 
               WHERE status != 'cancelled'), 1)         AS revenue_share_pct
    FROM bookings
    WHERE status != 'cancelled'
    GROUP BY destination
    ORDER BY total_revenue DESC
    LIMIT 10
    """
    return run_query(sql)


def query_device_performance() -> pd.DataFrame:
    """
    BUSINESS QUESTION:
    Which device type converts best and generates most revenue?
    
    WHY IT MATTERS:
    If mobile converts 2x better than desktop, the engineering
    team should prioritize mobile app features and performance.
    Product managers use this to justify roadmap decisions.
    """
    sql = """
    SELECT 
        device,
        COUNT(*)                                            AS total_bookings,
        ROUND(SUM(CASE WHEN status='completed' 
                       THEN total_price ELSE 0 END), 2)    AS revenue,
        ROUND(AVG(total_price), 2)                         AS avg_order_value,
        ROUND(
            SUM(CASE WHEN status='completed' THEN 1.0 ELSE 0 END)
            / COUNT(*) * 100, 1
        )                                                   AS completion_rate_pct,
        ROUND(
            SUM(CASE WHEN status='cancelled' THEN 1.0 ELSE 0 END)
            / COUNT(*) * 100, 1
        )                                                   AS cancellation_rate_pct
    FROM bookings
    GROUP BY device
    ORDER BY revenue DESC
    """
    return run_query(sql)


def query_cancellation_by_rating() -> pd.DataFrame:
    """
    BUSINESS QUESTION:
    Do lower-rated properties have higher cancellation rates?
    
    WHY IT MATTERS:
    If yes, the platform should flag/delist properties below
    a threshold. This directly impacts customer satisfaction
    scores (NPS) and platform trust.
    """
    sql = """
    SELECT 
        CASE 
            WHEN p.rating < 2.5 THEN '⭐ Very Low (<2.5)'
            WHEN p.rating < 3.0 THEN '⭐⭐ Low (2.5–3.0)'
            WHEN p.rating < 3.5 THEN '⭐⭐⭐ Below Avg (3.0–3.5)'
            WHEN p.rating < 4.0 THEN '⭐⭐⭐ Average (3.5–4.0)'
            WHEN p.rating < 4.5 THEN '⭐⭐⭐⭐ Good (4.0–4.5)'
            ELSE                     '⭐⭐⭐⭐⭐ Excellent (4.5+)'
        END                                                 AS rating_bucket,
        COUNT(*)                                            AS total_bookings,
        ROUND(
            SUM(CASE WHEN b.status='cancelled' THEN 1.0 ELSE 0 END)
            / COUNT(*) * 100, 1
        )                                                   AS cancellation_rate_pct,
        ROUND(AVG(p.rating), 2)                             AS avg_rating
    FROM bookings b
    JOIN properties p ON b.property_id = p.property_id
    GROUP BY rating_bucket
    ORDER BY avg_rating
    """
    return run_query(sql)


def query_new_vs_returning() -> pd.DataFrame:
    """
    BUSINESS QUESTION:
    Do returning users book more and spend more than new users?
    
    WHY IT MATTERS:
    If returning users have 3x higher LTV, the business should
    invest heavily in loyalty programs and retention campaigns
    rather than pure acquisition spend.
    """
    sql = """
    SELECT 
        u.user_type,
        COUNT(DISTINCT u.user_id)                           AS total_users,
        COUNT(b.booking_id)                                 AS total_bookings,
        ROUND(COUNT(b.booking_id) * 1.0 
              / COUNT(DISTINCT u.user_id), 2)               AS bookings_per_user,
        ROUND(SUM(CASE WHEN b.status != 'cancelled' 
                       THEN b.total_price ELSE 0 END), 2)   AS total_revenue,
        ROUND(AVG(CASE WHEN b.status != 'cancelled' 
                       THEN b.total_price END), 2)          AS avg_booking_value
    FROM users u
    LEFT JOIN bookings b ON u.user_id = b.user_id
    GROUP BY u.user_type
    ORDER BY total_revenue DESC
    """
    return run_query(sql)


# ════════════════════════════════════════════════════════
# SCHEMA SUMMARY — used by Gemini to generate valid SQL
# ════════════════════════════════════════════════════════

SCHEMA_DESCRIPTION = """
You are a SQL expert. The SQLite database has these tables:

TABLE: users
  - user_id       INTEGER  (primary key)
  - name          TEXT
  - email         TEXT
  - country       TEXT
  - device        TEXT     (values: 'mobile', 'desktop', 'tablet')
  - user_type     TEXT     (values: 'new', 'returning')
  - signup_date   TEXT     (format: YYYY-MM-DD)
  - age           INTEGER

TABLE: properties
  - property_id   INTEGER  (primary key)
  - name          TEXT
  - destination   TEXT     (e.g. 'Paris', 'Tokyo', 'Dubai')
  - property_type TEXT     (values: 'Hotel','Resort','Villa','Apartment','Hostel')
  - rating        REAL     (1.0 to 5.0)
  - price_per_night REAL
  - total_rooms   INTEGER
  - amenities     TEXT

TABLE: bookings
  - booking_id    INTEGER  (primary key)
  - user_id       INTEGER  (FK → users)
  - property_id   INTEGER  (FK → properties)
  - destination   TEXT
  - checkin_date  TEXT     (format: YYYY-MM-DD)
  - checkout_date TEXT     (format: YYYY-MM-DD)
  - nights        INTEGER
  - total_price   REAL
  - status        TEXT     (values: 'confirmed','cancelled','completed')
  - device        TEXT
  - is_weekend    INTEGER  (1 = weekend check-in, 0 = weekday)

TABLE: events
  - event_id      INTEGER  (primary key)
  - user_id       INTEGER  (FK → users)
  - event_type    TEXT     (values: 'search','view','cart','booking')
  - device        TEXT
  - timestamp     TEXT     (format: YYYY-MM-DD HH:MM:SS)
  - destination   TEXT

IMPORTANT RULES:
- Always use proper JOIN syntax
- For cancellation rate: SUM(CASE WHEN status='cancelled' THEN 1.0 ELSE 0 END) / COUNT(*) * 100
- For revenue: always exclude cancelled bookings with WHERE status != 'cancelled'
- Return maximum 20 rows unless asked otherwise
- Only return the SQL query, nothing else
"""