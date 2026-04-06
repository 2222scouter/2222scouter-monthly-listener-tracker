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
    # Load history
    history_url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSa5tdG_4WSMrmGcaJhOZBwC_6oyXVSbpLjdrf8hfgRB_rHwm49rohMiE6ZATi42ScZDo5d1_fAW_Sw/pub?gid=0&single=true&output=csv"
    
    try:
        df = pd.read_csv(history_url)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df = df.sort_values(['artist', 'timestamp'], ascending=[True, False])
        
        # Keep latest per artist
        df = df.drop_duplicates(subset='artist', keep='first')
        
        # Load current artists from Google Sheet
        sheet_df = pd.read_csv(sheet_url)
        # Assume first column is artist name
        active_artists = set(sheet_df.iloc[:, 0].astype(str).str.strip().str.lower())
        
        # Filter to only show artists still in the sheet
        df['artist_lower'] = df['artist'].astype(str).str.strip().str.lower()
        df = df[df['artist_lower'].isin(active_artists)]
        df = df.drop(columns=['artist_lower'])
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
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

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "artist": st.column_config.TextColumn("Artist"),
            "timestamp": st.column_config.TextColumn("Date of Latest Scan"),
            "most_recent_listeners": st.column_config.TextColumn("Most Recent Listeners"),
        }
    )

if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()
