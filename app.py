import streamlit as st
import pandas as pd

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

# Load data (use old cache for compatibility)
@st.cache(show_spinner=False, ttl=300)
def load_data():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.fillna("-")
        return df
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.text("no data yet")
else:
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": "time",
            "artist": "artist",
            "monthly_listeners": "listeners",
            "change_since_yesterday": "change yesterday",
            "pct_since_yesterday": "pct yesterday",
            "change_day1_to_day2": "change day1→day2",
            "pct_day1_to_day2": "pct day1→day2",
            "change_day2_to_day3": "change day2→day3",
            "pct_day2_to_day3": "pct day2→day3",
        }
    )

# Refresh button
if st.button("Refresh"):
    st.cache.clear()
    st.rerun()
