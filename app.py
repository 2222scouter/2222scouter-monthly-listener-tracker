import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Tracker", layout="wide", initial_sidebar_state="collapsed")

# Off-white background, hide sidebar/header
st.markdown("""
    <style>
        section[data-testid="stSidebar"] {display: none;}
        .main .block-container {padding: 1rem 1rem 0rem !important;}
        body, .stApp {background-color: #f8f9fa !important;}
        .tiny-title {
            font-size: 11px;
            color: #aaa;
            text-align: center;
            margin: 20px 0 40px 0;
            letter-spacing: 1px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="tiny-title">2222scouter tracker</div>', unsafe_allow_html=True)

# Load data
@st.cache_data(ttl=300)
def load_data():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Replace NaN with 0 for gain columns
        gain_cols = [c for c in df.columns if 'change_' in c or 'pct_' in c]
        df[gain_cols] = df[gain_cols].fillna(0)
        return df
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.text("no data yet")
else:
    # Format display
    def fmt_change(x):
        if x == "-" or pd.isna(x) or x == "":
            return "0"
        try:
            return f"{float(x):+,d}"
        except (ValueError, TypeError):
            return str(x)

    def fmt_pct(x):
        if x == "-" or pd.isna(x) or x == "":
            return "-"
        try:
            return f"{float(x):+.1f}%"
        except (ValueError, TypeError):
            return str(x)

    display_df = df.copy()
    for col in display_df.columns:
        if 'change_' in col:
            display_df[col] = display_df[col].apply(fmt_change)
        elif 'pct_' in col:
            display_df[col] = display_df[col].apply(fmt_pct)
        elif col == 'monthly_listeners':
            display_df[col] = display_df[col].apply(lambda x: f"{x:,}" if isinstance(x, (int, float)) else x)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": st.column_config.TextColumn("Time"),
            "artist": st.column_config.TextColumn("Artist"),
            "monthly_listeners": st.column_config.TextColumn("Monthly Listeners"),
            "change_since_yesterday": st.column_config.TextColumn("Change Yesterday"),
            "pct_since_yesterday": st.column_config.TextColumn("Pct Yesterday"),
            "change_day1_to_day2": st.column_config.TextColumn("Day1→Day2"),
            "pct_day1_to_day2": st.column_config.TextColumn("Pct Day1→Day2"),
            "change_day2_to_day3": st.column_config.TextColumn("Day2→Day3"),
            "pct_day2_to_day3": st.column_config.TextColumn("Pct Day2→Day3"),
        }
    )

# Refresh button
if st.button("Refresh"):
    st.rerun()
