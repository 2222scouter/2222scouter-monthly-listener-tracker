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

# Load and process data - one row per artist per day
@st.cache_data(ttl=300)
def load_data():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        # Create a date-only column for grouping
        df['date'] = df['timestamp'].dt.date
        
        # Keep only the latest scan per artist per day
        df = df.sort_values(['artist', 'date', 'timestamp'], ascending=[True, True, False])
        df = df.drop_duplicates(subset=['artist', 'date'], keep='first')
        
        # Now group by artist and calculate gains based on previous days
        result = []
        for artist in df['artist'].unique():
            artist_rows = df[df['artist'] == artist].sort_values('date', ascending=False).head(8)
            
            if len(artist_rows) == 0:
                continue

            latest = artist_rows.iloc[0]
            previous = artist_rows.iloc[1] if len(artist_rows) > 1 else None

            change_since_last = latest['monthly_listeners'] - previous['monthly_listeners'] if previous is not None else 0
            pct_since_last = round(change_since_last / previous['monthly_listeners'] * 100, 1) if previous is not None and previous['monthly_listeners'] > 0 else 0

            seven_days_ago = artist_rows.iloc[7] if len(artist_rows) > 7 else None
            change_7days = latest['monthly_listeners'] - seven_days_ago['monthly_listeners'] if seven_days_ago is not None else 0
            pct_7days = round(change_7days / seven_days_ago['monthly_listeners'] * 100, 1) if seven_days_ago is not None and seven_days_ago['monthly_listeners'] > 0 else 0

            row = {
                'artist': artist,
                'date_of_latest_scan': latest['timestamp'].strftime('%Y-%m-%d'),
                'most_recent_listeners': latest['monthly_listeners'],
                'pct_change_since_last': pct_since_last,
                'change_since_last': change_since_last,
                'last_scan_listeners': previous['monthly_listeners'] if previous is not None else 0,
                'pct_7days': pct_7days,
            }
            result.append(row)

        return pd.DataFrame(result)
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.text("no data yet")
else:
    # Safe formatters
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
    display_df['pct_7days'] = display_df['pct_7days'].apply(fmt_pct)
    display_df['most_recent_listeners'] = display_df['most_recent_listeners'].apply(fmt_number)
    display_df['change_since_last'] = display_df['change_since_last'].apply(fmt_number)
    display_df['last_scan_listeners'] = display_df['last_scan_listeners'].apply(fmt_number)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "artist": st.column_config.TextColumn("Artist"),
            "date_of_latest_scan": st.column_config.TextColumn("Date of Latest Scan"),
            "most_recent_listeners": st.column_config.TextColumn("Most Recent Listeners"),
            "pct_change_since_last": st.column_config.TextColumn("% Change Since Last Scan"),
            "change_since_last": st.column_config.TextColumn("# Change Since Last Scan"),
            "last_scan_listeners": st.column_config.TextColumn("Last Scan Listeners"),
            "pct_7days": st.column_config.TextColumn("% Gain/Loss Last 7 Days"),
        }
    )

# Refresh button
if st.button("Refresh"):
    st.rerun()
