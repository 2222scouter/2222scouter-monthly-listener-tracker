import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Tracker", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        section[data-testid="stSidebar"] {display: none;}
        .main .block-container {padding: 1rem 1rem 0rem !important;}
        body, .stApp {background-color: #f8f9fa !important;}
        .tiny-title {
            font-size: 12px;
            color: #888;
            text-align: center;
            margin: 20px 0 30px 0;
            letter-spacing: 1px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="tiny-title">2222scouter tracker</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        
        # Fix timestamp if it's in milliseconds (Unix timestamp)
        if df['timestamp'].dtype == 'int64' or df['timestamp'].dtype == 'float64':
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        # Keep only the latest entry per artist
        df = df.sort_values(['artist', 'timestamp'], ascending=[True, False])
        df = df.drop_duplicates(subset='artist', keep='first')
        
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame(columns=['artist', 'timestamp', 'monthly_listeners'])

df = load_data()

if df.empty or 'artist' not in df.columns:
    st.text("no data yet")
else:
    def fmt_number(x):
        if pd.isna(x):
            return "0"
        return f"{x:,}"

    display_df = df.copy()
    display_df['most_recent_listeners'] = display_df.get('monthly_listeners', 0).apply(fmt_number)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "artist": st.column_config.TextColumn("Artist"),
            "timestamp": st.column_config.DatetimeColumn("Date of Latest Scan", format="D MMM YYYY HH:mm"),
            "most_recent_listeners": st.column_config.TextColumn("Most Recent Listeners"),
        }
    )

if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()
