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
    history_url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSa5tdG_4WSMrmGcaJhOZBwC_6oyXVSbpLjdrf8hfgRB_rHwm49rohMiE6ZATi42ScZDo5d1_fAW_Sw/pub?gid=0&single=true&output=csv"
    
    try:
        df = pd.read_csv(history_url)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df = df.sort_values(['artist', 'timestamp'], ascending=[True, False])

        # Keep latest per artist for display
        df = df.drop_duplicates(subset='artist', keep='first')
        
        # Load current artists from Google Sheet
        sheet_df = pd.read_csv(sheet_url)
        # First column of the sheet is assumed to be the artist name
        active_artists = set(sheet_df.iloc[:, 0].astype(str).str.strip())
        
        # Filter to only show artists that are still in the Google Sheet
        df = df[df['artist'].astype(str).str.strip().isin(active_artists)]
        
        return df
    except:
        return pd.DataFrame()

df = load_data()

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

    def fmt_number(x):
        if pd.isna(x):
            return "0"
        return f"{x:,}"

    display_df = df.copy()
    display_df['change_since_yesterday'] = display_df['change_since_yesterday'].apply(fmt_change)
    display_df['pct_change_since_yesterday'] = display_df['pct_change_since_yesterday'].apply(fmt_pct)
    display_df['pct_change_past_2_days'] = display_df['pct_change_past_2_days'].apply(fmt_pct)
    display_df['pct_change_past_3_days'] = display_df['pct_change_past_3_days'].apply(fmt_pct)
    display_df['most_recent_listeners'] = display_df['most_recent_listeners'].apply(fmt_number)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "artist": st.column_config.TextColumn("Artist"),
            "date_of_latest_scan": st.column_config.TextColumn("Date of Latest Scan"),
            "most_recent_listeners": st.column_config.TextColumn("Most Recent Listeners"),
            "change_since_yesterday": st.column_config.TextColumn("# Change Since Yesterday"),
            "pct_change_since_yesterday": st.column_config.TextColumn("% Change Since Yesterday"),
            "pct_change_past_2_days": st.column_config.TextColumn("% Change Past 2 Days"),
            "pct_change_past_3_days": st.column_config.TextColumn("% Change Past 3 Days"),
        }
    )

if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()
