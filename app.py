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

        result = []
        for artist in df['artist'].unique():
            artist_rows = df[df['artist'] == artist].sort_values('timestamp', ascending=False)
            if len(artist_rows) == 0:
                continue

            latest = artist_rows.iloc[0]
            
            change = 0
            pct_change = 0
            if len(artist_rows) > 1:
                previous = artist_rows.iloc[1]
                change = latest['monthly_listeners'] - previous['monthly_listeners']
                pct_change = round(change / previous['monthly_listeners'] * 100, 1) if previous['monthly_listeners'] > 0 else 0

            row = {
                'artist': artist,
                'date_of_latest_scan': latest['timestamp'].strftime('%Y-%m-%d %H:%M'),
                'most_recent_listeners': latest['monthly_listeners'],
                'change_since_yesterday': change,
                'pct_change_since_yesterday': pct_change,
            }
            result.append(row)

        return pd.DataFrame(result)
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
        }
    )

if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()
