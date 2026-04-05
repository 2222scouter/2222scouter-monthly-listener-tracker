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
            artist_rows = df[df['artist'] == artist].sort_values('timestamp', ascending=False).head(5)
            if len(artist_rows) == 0:
                continue

            latest = artist_rows.iloc[0]

            change_yesterday = 0
            pct_yesterday = 0
            if len(artist_rows) > 1:
                previous = artist_rows.iloc[1]
                change_yesterday = latest['monthly_listeners'] - previous['monthly_listeners']
                pct_yesterday = round(change_yesterday / previous['monthly_listeners'] * 100, 1) if previous['monthly_listeners'] > 0 else 0

            pct_past_2 = 0
            if len(artist_rows) > 2:
                two_days_ago = artist_rows.iloc[2]
                pct_past_2 = round((latest['monthly_listeners'] - two_days_ago['monthly_listeners']) / two_days_ago['monthly_listeners'] * 100, 1) if two_days_ago['monthly_listeners'] > 0 else 0

            pct_past_3 = 0
            if len(artist_rows) > 3:
                three_days_ago = artist_rows.iloc[3]
                pct_past_3 = round((latest['monthly_listeners'] - three_days_ago['monthly_listeners']) / three_days_ago['monthly_listeners'] * 100, 1) if three_days_ago['monthly_listeners'] > 0 else 0

            row = {
                'artist': artist,
                'date_of_latest_scan': latest['timestamp'].strftime('%Y-%m-%d %H:%M'),
                'most_recent_listeners': latest['monthly_listeners'],
                'change_since_yesterday': change_yesterday,
                'pct_change_since_yesterday': pct_yesterday,
                'pct_change_past_2_days': pct_past_2,
                'pct_change_past_3_days': pct_past_3,
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
