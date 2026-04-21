import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ── Brand color palette (professional, travel-themed) ──
COLORS = [
    "#0066FF", "#00C2FF", "#7B61FF", "#FF6B6B",
    "#FFB347", "#2ECC71", "#E74C3C", "#9B59B6"
]

BG_COLOR    = "#0F1117"   # dark background (matches Streamlit dark)
PAPER_COLOR = "#1A1D2E"   # card background
FONT_COLOR  = "#FFFFFF"


def _base_layout(title: str) -> dict:
    """Shared layout config applied to every chart."""
    return dict(
        title=dict(
            text=title,
            font=dict(size=18, color=FONT_COLOR, family="Arial Black"),
            x=0.01
        ),
        paper_bgcolor=PAPER_COLOR,
        plot_bgcolor =BG_COLOR,
        font=dict(color=FONT_COLOR, family="Arial"),
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=1
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.05)",
            zerolinecolor="rgba(255,255,255,0.1)"
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.05)",
            zerolinecolor="rgba(255,255,255,0.1)"
        ),
    )


# ════════════════════════════════════════════════════
# CHART 1: Horizontal Bar (default for comparisons)
# ════════════════════════════════════════════════════

def bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    df_sorted = df.sort_values(y_col, ascending=True).tail(15)

    fig = go.Figure(go.Bar(
        x=df_sorted[y_col],
        y=df_sorted[x_col],
        orientation='h',
        marker=dict(
            color=df_sorted[y_col],
            colorscale=[[0, "#0066FF"], [0.5, "#7B61FF"], [1, "#00C2FF"]],
            showscale=False,
            line=dict(color="rgba(255,255,255,0.1)", width=0.5)
        ),
        text=df_sorted[y_col].apply(
            lambda v: f"${v:,.0f}" if v > 1000 else f"{v:,.1f}"
        ),
        textposition='outside',
        textfont=dict(size=11, color=FONT_COLOR),
    ))

    fig.update_layout(**_base_layout(title))
    fig.update_layout(height=max(350, len(df_sorted) * 45))
    return fig


# ════════════════════════════════════════════════════
# CHART 2: Funnel Chart
# ════════════════════════════════════════════════════

def funnel_chart(df: pd.DataFrame, step_col: str, value_col: str, title: str) -> go.Figure:
    fig = go.Figure(go.Funnel(
        y=df[step_col],
        x=df[value_col],
        textinfo="value+percent initial",
        textfont=dict(size=13, color=FONT_COLOR),
        marker=dict(
            color=["#0066FF", "#7B61FF", "#00C2FF", "#2ECC71"],
            line=dict(width=2, color=PAPER_COLOR)
        ),
        connector=dict(
            line=dict(color="rgba(255,255,255,0.2)", width=1)
        )
    ))

    fig.update_layout(**_base_layout(title))
    fig.update_layout(height=420)
    return fig


# ════════════════════════════════════════════════════
# CHART 3: Line Chart (time series)
# ════════════════════════════════════════════════════

def line_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode='lines+markers',
        line=dict(color="#0066FF", width=3),
        marker=dict(
            size=7,
            color="#00C2FF",
            line=dict(color=PAPER_COLOR, width=2)
        ),
        fill='tozeroy',
        fillcolor="rgba(0,102,255,0.08)",
    ))

    fig.update_layout(**_base_layout(title))
    fig.update_layout(height=400)
    return fig


# ════════════════════════════════════════════════════
# CHART 4: Pie / Donut Chart (share data)
# ════════════════════════════════════════════════════

def pie_chart(df: pd.DataFrame, label_col: str, value_col: str, title: str) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=df[label_col],
        values=df[value_col],
        hole=0.45,          # donut style
        marker=dict(
            colors=COLORS,
            line=dict(color=PAPER_COLOR, width=2)
        ),
        textinfo='label+percent',
        textfont=dict(size=12, color=FONT_COLOR),
        insidetextorientation='radial',
    ))

    fig.update_layout(**_base_layout(title))
    fig.update_layout(
        height=420,
        showlegend=True,
        annotations=[dict(
            text='Share',
            x=0.5, y=0.5,
            font=dict(size=14, color=FONT_COLOR),
            showarrow=False
        )]
    )
    return fig


# ════════════════════════════════════════════════════
# CHART 5: Grouped Bar (multi-category comparison)
# ════════════════════════════════════════════════════

def grouped_bar_chart(df: pd.DataFrame, x_col: str, y_cols: list, title: str) -> go.Figure:
    fig = go.Figure()

    for i, y_col in enumerate(y_cols):
        fig.add_trace(go.Bar(
            name=y_col.replace("_", " ").title(),
            x=df[x_col],
            y=df[y_col],
            marker_color=COLORS[i % len(COLORS)],
            marker_line=dict(color="rgba(255,255,255,0.1)", width=0.5),
        ))

    fig.update_layout(**_base_layout(title))
    fig.update_layout(barmode='group', height=420)
    return fig


# ════════════════════════════════════════════════════
# AUTO-DETECT: Smart chart picker
# ════════════════════════════════════════════════════

def auto_chart(df: pd.DataFrame, question: str = "") -> go.Figure:
    """
    Examines the DataFrame and question to pick the best chart.
    This is the ONLY function called by app.py.

    Decision logic:
      1. Funnel keywords in question OR step_order column → Funnel
      2. Date/time column present → Line
      3. Percentage/share column + ≤10 rows → Pie/Donut
      4. Multiple numeric columns → Grouped Bar
      5. Default → Horizontal Bar
    """

    if df is None or df.empty:
        return None

    cols        = df.columns.tolist()
    q_lower     = question.lower()
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    text_cols    = df.select_dtypes(include='object').columns.tolist()

    title = question.title() if question else "Query Results"

    # ── RULE 1: Funnel ──────────────────────────────
    funnel_keywords = ["funnel", "step", "drop", "conversion", "dropout"]
    has_funnel_col  = any("step" in c.lower() or "funnel" in c.lower() 
                          for c in cols)
    has_funnel_q    = any(kw in q_lower for kw in funnel_keywords)

    if (has_funnel_col or has_funnel_q) and len(numeric_cols) >= 1:
        step_col  = next(
            (c for c in text_cols if "step" in c.lower() or "event" in c.lower()),
            text_cols[0] if text_cols else cols[0]
        )
        value_col = numeric_cols[0]
        return funnel_chart(df, step_col, value_col, title)

    # ── RULE 2: Line (time series) ──────────────────
    date_keywords = ["date", "month", "year", "week", "time", "day"]
    date_col = next(
        (c for c in cols if any(kw in c.lower() for kw in date_keywords)),
        None
    )
    if date_col and numeric_cols:
        return line_chart(df, date_col, numeric_cols[0], title)

    # ── RULE 3: Pie (share / percentage) ───────────
    pct_keywords = ["pct", "percent", "share", "ratio", "rate"]
    has_pct_col  = any(any(kw in c.lower() for kw in pct_keywords) 
                       for c in numeric_cols)
    has_pct_q    = any(kw in q_lower for kw in ["share", "percent", "breakdown",
                                                  "proportion", "distribution"])

    if (has_pct_col or has_pct_q) and text_cols and len(df) <= 10:
        label_col = text_cols[0]
        value_col = numeric_cols[0]
        return pie_chart(df, label_col, value_col, title)

    # ── RULE 4: Grouped Bar (multiple metrics) ──────
    if len(numeric_cols) >= 3 and text_cols:
        return grouped_bar_chart(df, text_cols[0], numeric_cols[:3], title)

    # ── RULE 5: Default → Horizontal Bar ───────────
    if text_cols and numeric_cols:
        return bar_chart(df, text_cols[0], numeric_cols[0], title)

    # ── Fallback: plain bar on first two columns ────
    if len(cols) >= 2:
        return bar_chart(df, cols[0], cols[1], title)

    return None