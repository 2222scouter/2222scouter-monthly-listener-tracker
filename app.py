import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="2222scouter Tracker", layout="wide", page_icon="📈")

st.title("2222scouter Monthly Listener Tracker")

# Load data from GitHub raw CSV (updates automatically after each run)
@st.cache_data(ttl=300)  # Cache for 5 min
def load_data():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No data yet — wait for the next scheduled run or trigger manually in Actions.")
else:
    # Latest stats table
    latest = df.sort_values('timestamp').groupby('artist').last().reset_index()
    st.subheader("Latest Listener Counts & Gains")
    st.dataframe(
        latest[['artist', 'timestamp', 'monthly_listeners',
                'change_since_yesterday', 'pct_since_yesterday',
                'change_day1_to_day2', 'pct_day1_to_day2',
                'change_day2_to_day3', 'pct_day2_to_day3']],
        use_container_width=True, hide_index=True
    )

    # Interactive graph
    st.subheader("Growth Over Time")
    fig = px.line(df, x='timestamp', y='monthly_listeners', color='artist',
                  markers=True, title='Monthly Listeners Trend')
    fig.update_layout(hovermode='x unified', legend_title='Artist')
    st.plotly_chart(fig, use_container_width=True)

    # Refresh button
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

st.markdown("Data updates via GitHub Actions (3–4 PM EST). Add artists in your Google Sheet — they auto-appear here.")
