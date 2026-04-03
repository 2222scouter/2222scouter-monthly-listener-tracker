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
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Force correct column names
        if 'index' in df.columns:
            df = df.rename(columns={'index': 'artist'})
        if 'artist' not in df.columns:
            if len(df.columns) > 0:
                df = df.rename(columns={df.columns[0]: 'artist'})
        
        df = df.sort_values(['artist', 'timestamp'], ascending=[True, False])
        df = df.drop_duplicates(subset='artist', keep='first')
        return df
    except:
        return pd.DataFrame(columns=['artist', 'timestamp', 'monthly_listeners'])

df = load_data()

if df.empty or 'artist' not in df.columns:
    st.text("no data yet")
else:
    def fmt_number(x):
        if pd.isna(x):
            return "0"
        return f"{x:,}"

    def fmt_pct(x):
        if pd.isna(x) or x == 0:
            return "-"
        return f"{x:+.1f}%"

    display_df = df.copy()
    display_df['most_recent_listeners'] = display_df.get('monthly_listeners', 0).apply(fmt_number)
    display_df['change_since_last'] = 0
    display_df['pct_change_since_last'] = "-"

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "artist": st.column_config.TextColumn("Artist"),
            "timestamp": st.column_config.TextColumn("Date of Latest Scan"),
            "most_recent_listeners": st.column_config.TextColumn("Most Recent Listeners"),
            "pct_change_since_last": st.column_config.TextColumn("% Change Since Last Scan"),
            "change_since_last": st.column_config.TextColumn("# Change Since Last Scan"),
        }
    )

if st.button("Refresh"):
    st.rerun()
