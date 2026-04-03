import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tracker", layout="wide", initial_sidebar_state="collapsed")

# Clean minimal style
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

# Load data - one row per artist per day
@st.cache_data(ttl=300)
def load_data():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df['date'] = df['timestamp'].dt.date
        
        # Keep only the latest scan per artist per day
        df = df.sort_values(['artist', 'date', 'timestamp'], ascending=[True, True, False])
        df = df.drop_duplicates(subset=['artist', 'date'], keep='first')
        
        # Calculate basic gains (latest vs previous day)
        result = []
        for artist in df['artist'].unique():
            artist_rows = df[df['artist'] == artist].sort_values('date', ascending=False).head(4)
            if len(artist_rows) == 0:
                continue

            latest = artist_rows.iloc[0]
            previous = artist_rows.iloc[1] if len(artist_rows) > 1 else None

            change = latest['monthly_listeners'] - (previous['monthly_listeners'] if previous is not None else 0)
            pct = round(change / previous['monthly_listeners'] * 100, 1) if previous is not None and previous['monthly_listeners'] > 0 else 0

            row = {
                'artist': artist,
                'date_of_latest_scan': latest['timestamp'].strftime('%Y-%m-%d'),
                'most_recent_listeners': latest['monthly_listeners'],
                'pct_change_since_last': pct,
                'change_since_last': change,
                'last_scan_listeners': previous['monthly_listeners'] if previous is not None else 0,
            }
            result.append(row)

        return pd.DataFrame(result)
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.text("no data yet")
else:
    def fmt_pct(x):
        if pd.isna(x) or x == 0:
            return "-"
        return f"{x:+.1f}%"

    def fmt_number(x):
        if pd.isna(x):
            return "0"
        return f"{x:,}"

    display_df = df.copy()
    display_df['pct_change_since_last'] = display_df['pct_change_since_last'].apply(fmt_pct)
    display_df['most_recent_listeners'] = display_df['most_recent_listeners'].apply(fmt_number)
    display_df['change_since_last'] = display_df['change_since_last'].apply(fmt_number)
    display_df['last_scan_listeners'] = display_df['last_scan_listeners'].apply(fmt_number)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "artist": st.column_config.TextColumn("Artist", width="medium"),
            "date_of_latest_scan": st.column_config.TextColumn("Date of Latest Scan"),
            "most_recent_listeners": st.column_config.TextColumn("Most Recent Listeners"),
            "pct_change_since_last": st.column_config.TextColumn("% Change Since Last Scan"),
            "change_since_last": st.column_config.TextColumn("# Change Since Last Scan"),
            "last_scan_listeners": st.column_config.TextColumn("Last Scan Listeners"),
        }
    )

if st.button("Refresh"):
    st.rerun()
