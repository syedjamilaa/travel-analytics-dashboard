import streamlit as st
import pandas as pd
from utils.db import (
    run_query,
    query_conversion_funnel,
    query_revenue_by_destination,
    query_device_performance,
    query_cancellation_by_rating,
    query_new_vs_returning,
)
from utils.gemini import run_ai_pipeline
from utils.charts import auto_chart

# ══════════════════════════════════════════════════
# PAGE CONFIG (must be first)
# ══════════════════════════════════════════════════

st.set_page_config(
    page_title="AI Travel Analytics",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════

st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0F1117; }

    /* KPI card */
    .kpi-card {
        background: linear-gradient(135deg, #1A1D2E 0%, #16213E 100%);
        border: 1px solid rgba(0,102,255,0.3);
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 800;
        color: #00C2FF;
        margin: 0;
    }
    .kpi-label {
        font-size: 13px;
        color: #8B92A5;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-delta {
        font-size: 12px;
        color: #2ECC71;
        margin-top: 2px;
    }

    /* Section headers */
    .section-header {
        font-size: 16px;
        font-weight: 700;
        color: #FFFFFF;
        padding: 8px 0 4px 0;
        border-bottom: 2px solid rgba(0,102,255,0.4);
        margin-bottom: 12px;
    }

    /* SQL code box */
    .sql-box {
        background: #1A1D2E;
        border: 1px solid rgba(0,102,255,0.3);
        border-radius: 8px;
        padding: 16px;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        color: #00C2FF;
        white-space: pre-wrap;
        word-break: break-word;
    }

    /* Insight box */
    .insight-box {
        background: linear-gradient(135deg, #1A1D2E 0%, #0D1B2A 100%);
        border-left: 4px solid #0066FF;
        border-radius: 0 8px 8px 0;
        padding: 16px 20px;
        color: #E8EAF0;
        font-size: 15px;
        line-height: 1.7;
    }

    /* Input styling */
    .stTextInput > div > div > input {
        background-color: #1A1D2E !important;
        border: 1px solid rgba(0,102,255,0.5) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        font-size: 16px !important;
        padding: 12px 16px !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1A1D2E;
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 6px;
        color: #8B92A5;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0066FF !important;
        color: #FFFFFF !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════

st.markdown("""
<div style='padding: 8px 0 24px 0;'>
    <h1 style='color:#FFFFFF; font-size:36px; font-weight:900; margin:0;'>
        ✈️ AI Travel Analytics Dashboard
    </h1>
    <p style='color:#8B92A5; font-size:16px; margin-top:6px;'>
        Ask any business question in plain English — powered by Gemini AI + SQLite
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()


# ══════════════════════════════════════════════════
# KPI METRICS ROW
# ══════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def load_kpis():
    total_revenue = run_query("""
        SELECT ROUND(SUM(total_price)/1000000, 2) as val
        FROM bookings WHERE status != 'cancelled'
    """)['val'][0]

    total_bookings = run_query("""
        SELECT COUNT(*) as val FROM bookings
    """)['val'][0]

    completion_rate = run_query("""
        SELECT ROUND(SUM(CASE WHEN status='completed' 
                    THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) as val
        FROM bookings
    """)['val'][0]

    top_destination = run_query("""
        SELECT destination FROM bookings
        WHERE status != 'cancelled'
        GROUP BY destination
        ORDER BY SUM(total_price) DESC LIMIT 1
    """)['destination'][0]

    avg_booking = run_query("""
        SELECT ROUND(AVG(total_price),0) as val
        FROM bookings WHERE status != 'cancelled'
    """)['val'][0]

    mobile_share = run_query("""
        SELECT ROUND(SUM(CASE WHEN device='mobile' 
                    THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) as val
        FROM bookings
    """)['val'][0]

    return total_revenue, total_bookings, completion_rate, \
           top_destination, avg_booking, mobile_share

try:
    total_rev, total_book, comp_rate, top_dest, avg_book, mob_share = load_kpis()

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        st.markdown(f"""
        <div class='kpi-card'>
            <p class='kpi-value'>${total_rev}M</p>
            <p class='kpi-label'>Total Revenue</p>
            <p class='kpi-delta'>↑ Platform Lifetime</p>
        </div>""", unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class='kpi-card'>
            <p class='kpi-value'>{total_book:,}</p>
            <p class='kpi-label'>Total Bookings</p>
            <p class='kpi-delta'>↑ All Time</p>
        </div>""", unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class='kpi-card'>
            <p class='kpi-value'>{comp_rate}%</p>
            <p class='kpi-label'>Completion Rate</p>
            <p class='kpi-delta'>↑ vs Industry 68%</p>
        </div>""", unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class='kpi-card'>
            <p class='kpi-value'>{top_dest}</p>
            <p class='kpi-label'>Top Destination</p>
            <p class='kpi-delta'>↑ By Revenue</p>
        </div>""", unsafe_allow_html=True)

    with k5:
        st.markdown(f"""
        <div class='kpi-card'>
            <p class='kpi-value'>${avg_book:,.0f}</p>
            <p class='kpi-label'>Avg Booking Value</p>
            <p class='kpi-delta'>↑ Per Transaction</p>
        </div>""", unsafe_allow_html=True)

    with k6:
        st.markdown(f"""
        <div class='kpi-card'>
            <p class='kpi-value'>{mob_share}%</p>
            <p class='kpi-label'>Mobile Share</p>
            <p class='kpi-delta'>↑ Of All Bookings</p>
        </div>""", unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Could not load KPIs: {e}")

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════
# AI QUESTION INPUT
# ══════════════════════════════════════════════════

st.markdown("<div class='section-header'>🤖 Ask the AI Analyst</div>",
            unsafe_allow_html=True)

EXAMPLE_QUESTIONS = [
    "What are the top 5 destinations by total revenue?",
    "Which device type has the highest cancellation rate?",
    "Compare new vs returning users by average booking value",
    "Show me the conversion funnel drop-off rates",
    "Which property type generates the most revenue?",
    "What is the cancellation rate by property rating?",
]

col_input, col_examples = st.columns([3, 1])

with col_input:
    question = st.text_input(
        label="question",
        label_visibility="collapsed",
        placeholder="e.g. What are the top 5 destinations by revenue?",
        key="main_question"
    )

with col_examples:
    selected_example = st.selectbox(
        "📌 Try an example",
        [""] + EXAMPLE_QUESTIONS,
        key="example_select"
    )

# Use example if selected
if selected_example and not question:
    question = selected_example

run_button = st.button("🔍 Analyse", type="primary", use_container_width=False)


# ══════════════════════════════════════════════════
# AI PIPELINE OUTPUT
# ══════════════════════════════════════════════════

if run_button and question:
    with st.spinner("🧠 Gemini is thinking..."):
        result = run_ai_pipeline(question)

    if result["error"]:
        st.error(result["error"])

    else:
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Row 1: SQL + Insight side by side ──
        col_sql, col_insight = st.columns([1, 1], gap="large")

        with col_sql:
            st.markdown("<div class='section-header'>📝 Generated SQL</div>",
                        unsafe_allow_html=True)
            st.markdown(
                f"<div class='sql-box'>{result['sql']}</div>",
                unsafe_allow_html=True
            )

        with col_insight:
            st.markdown("<div class='section-header'>💡 Business Insight</div>",
                        unsafe_allow_html=True)
            st.markdown(
                f"<div class='insight-box'>💡 {result['insight']}</div>",
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Row 2: Chart ──
        st.markdown("<div class='section-header'>📊 Visualisation</div>",
                    unsafe_allow_html=True)

        fig = auto_chart(result["dataframe"], question)
        if fig:
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Could not auto-generate a chart for this result.")

        # ── Row 3: Raw data (collapsed by default) ──
        with st.expander("📋 View Raw Data", expanded=False):
            st.dataframe(
                result["dataframe"],
                width='stretch',
                hide_index=True
            )

elif run_button and not question:
    st.warning("Please enter a question first.")


# ══════════════════════════════════════════════════
# PRE-BUILT ANALYTICS TABS
# ══════════════════════════════════════════════════

st.markdown("<br>", unsafe_allow_html=True)
st.divider()
st.markdown("<div class='section-header'>🔍 Pre-Built Analytics</div>",
            unsafe_allow_html=True)
st.markdown(
    "<p style='color:#8B92A5; font-size:13px; margin-bottom:16px;'>"
    "Explore key business metrics — no question needed.</p>",
    unsafe_allow_html=True
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔽 Conversion Funnel",
    "🌍 Revenue by Destination",
    "📱 Device Performance",
    "⭐ Cancellation by Rating",
    "👥 New vs Returning"
])

with tab1:
    df_funnel = query_conversion_funnel()
    fig = auto_chart(df_funnel, "conversion funnel drop off steps")
    st.plotly_chart(fig, width='stretch')
    with st.expander("📋 Data"):
        st.dataframe(df_funnel, hide_index=True)

with tab2:
    df_rev = query_revenue_by_destination()
    fig = auto_chart(df_rev, "revenue by destination")
    st.plotly_chart(fig, width='stretch')
    with st.expander("📋 Data"):
        st.dataframe(df_rev, hide_index=True)

with tab3:
    df_dev = query_device_performance()
    fig = auto_chart(df_dev, "device performance comparison metrics")
    st.plotly_chart(fig, width='stretch')
    with st.expander("📋 Data"):
        st.dataframe(df_dev, hide_index=True)

with tab4:
    df_cancel = query_cancellation_by_rating()
    fig = auto_chart(df_cancel, "cancellation rate by rating")
    st.plotly_chart(fig, width='stretch')
    with st.expander("📋 Data"):
        st.dataframe(df_cancel, hide_index=True)

with tab5:
    df_users = query_new_vs_returning()
    fig = auto_chart(df_users, "new vs returning users comparison")
    st.plotly_chart(fig, width='stretch')
    with st.expander("📋 Data"):
        st.dataframe(df_users, hide_index=True)


# ══════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════

st.divider()
st.markdown("""
<div style='text-align:center; color:#8B92A5; font-size:13px; padding:12px 0;'>
    Built with ✈️ Streamlit · Plotly · SQLite · Google Gemini AI &nbsp;|&nbsp;
    <span style='color:#0066FF;'>AI-Powered Travel Analytics Dashboard</span>
</div>
""", unsafe_allow_html=True)