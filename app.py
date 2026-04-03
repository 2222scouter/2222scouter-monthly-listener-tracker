import streamlit as st
import pandas as pd

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
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df = df.sort_values(['artist', 'timestamp'], ascending=[True, False])
        # Keep only latest per artist
        df = df.drop_duplicates(subset='artist', keep='first')
        return df
    except:
        return pd.DataFrame()

df = load_data()

# Get current artists from Google Sheet to filter
sheet_url = SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSa5tdG_4WSMrmGcaJhOZBwC_6oyXVSbpLjdrf8hfgRB_rHwm49rohMiE6ZATi42ScZDo5d1_fAW_Sw/pub?gid=0&single=true&output=csv"
try:
    sheet_df = pd.read_csv(sheet_url)
    active_artists = set(sheet_df.iloc[:, 0].astype(str).str.strip())  # first column = artist names
    df = df[df['artist'].isin(active_artists)]
except:
    pass  # if sheet fails, show all

if df.empty:
    st.text("no data yet")
else:
    def fmt_change(x):
        if pd.isna(x) or x == 0:
            return "0"
        return f"{x:+,d}"

    def fmt_pct(x):
        if pd.isna(x) or x == 0:
            return "-"
        return f"{x:+.1f}%"

    display_df = df.copy()
    # Add basic gain calculation if you have history
    display_df['change_since_last'] = 0
    display_df['pct_since_last'] = "-"

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "artist": st.column_config.TextColumn("Artist", width="medium"),
            "timestamp": st.column_config.TextColumn("Date of Latest Scan"),
            "monthly_listeners": st.column_config.TextColumn("Most Recent Listeners"),
            "change_since_last": st.column_config.TextColumn("# Change Since Last Scan"),
            "pct_since_last": st.column_config.TextColumn("% Change Since Last Scan"),
        }
    )

if st.button("Refresh"):
    st.rerun()
