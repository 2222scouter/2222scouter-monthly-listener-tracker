import streamlit as st
import pandas as pd

st.set_page_config(page_title="2222scouter Tracker", layout="wide", initial_sidebar_state="collapsed")

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
            margin: 15px 0 25px 0;
            letter-spacing: 1px;
        }
        .tab-button {
            font-size: 18px;
            padding: 10px 25px;
            margin: 0 10px;
            border: none;
            border-radius: 8px;
            background-color: #e0e0e0;
            color: #333;
        }
        .tab-button.active {
            background-color: #4CAF50;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="tiny-title">2222scouter tracker</div>', unsafe_allow_html=True)

# Session state to remember which tab is active
if 'view' not in st.session_state:
    st.session_state.view = "listeners"

# Tab buttons
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("Listeners", key="btn_listeners", 
                 type="primary" if st.session_state.view == "listeners" else "secondary"):
        st.session_state.view = "listeners"
        st.rerun()
    if st.button("Streams", key="btn_streams", 
                 type="primary" if st.session_state.view == "streams" else "secondary"):
        st.session_state.view = "streams"
        st.rerun()

# ====================== LISTENERS VIEW ======================
if st.session_state.view == "listeners":
    @st.cache_data(ttl=300)
    def load_listeners():
        url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
        try:
            df = pd.read_csv(url)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df['date'] = df['timestamp'].dt.date
            df = df.sort_values(['artist', 'date', 'timestamp'], ascending=[True, True, False])
            df = df.drop_duplicates(subset=['artist', 'date'], keep='first')
            
            result = []
            for artist in df['artist'].unique():
                artist_rows = df[df['artist'] == artist].sort_values('date', ascending=False).head(8)
                if len(artist_rows) == 0: continue
                
                latest = artist_rows.iloc[0]
                prev = artist_rows.iloc[1] if len(artist_rows) > 1 else None
                
                change = latest['monthly_listeners'] - (prev['monthly_listeners'] if prev is not None else 0)
                pct = round(change / prev['monthly_listeners'] * 100, 1) if prev is not None and prev['monthly_listeners'] > 0 else 0
                
                seven_ago = artist_rows.iloc[7] if len(artist_rows) > 7 else None
                change7 = latest['monthly_listeners'] - (seven_ago['monthly_listeners'] if seven_ago is not None else 0)
                pct7 = round(change7 / seven_ago['monthly_listeners'] * 100, 1) if seven_ago is not None and seven_ago['monthly_listeners'] > 0 else 0
                
                result.append({
                    'artist': artist,
                    'date_of_latest_scan': latest['timestamp'].strftime('%Y-%m-%d'),
                    'most_recent': latest['monthly_listeners'],
                    'pct_change': pct,
                    'change': change,
                    'last_scan': prev['monthly_listeners'] if prev is not None else 0,
                    'pct_7days': pct7,
                })
            return pd.DataFrame(result)
        except:
            return pd.DataFrame()

    df = load_listeners()
    title = "Monthly Listeners"

# ====================== STREAMS VIEW ======================
else:
    @st.cache_data(ttl=300)
    def load_streams():
        url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"  
        # ← We'll change this later when you add the streams CSV
        try:
            df = pd.read_csv(url)   # Placeholder for now
            # (We'll update this once you have a streams history file)
            return pd.DataFrame()   # temporary empty
        except:
            return pd.DataFrame()

    df = load_streams()
    title = "Total Streams"

# ====================== DISPLAY ======================
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
    display_df['pct_change'] = display_df['pct_change'].apply(fmt_pct)
    display_df['pct_7days'] = display_df['pct_7days'].apply(fmt_pct)
    display_df['most_recent'] = display_df['most_recent'].apply(fmt_number)
    display_df['change'] = display_df['change'].apply(fmt_number)
    display_df['last_scan'] = display_df['last_scan'].apply(fmt_number)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "artist": st.column_config.TextColumn("Artist", width="medium"),
            "date_of_latest_scan": st.column_config.TextColumn("Date of Latest Scan"),
            "most_recent": st.column_config.TextColumn(f"Most Recent {title}"),
            "pct_change": st.column_config.TextColumn("% Change Since Last Scan"),
            "change": st.column_config.TextColumn("# Change Since Last Scan"),
            "last_scan": st.column_config.TextColumn("Last Scan"),
            "pct_7days": st.column_config.TextColumn("% Gain/Loss Last 7 Days"),
        }
    )

if st.button("Refresh"):
    st.rerun()
