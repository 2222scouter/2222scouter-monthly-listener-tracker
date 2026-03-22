import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="2222scouter Listener Tracker", layout="wide", page_icon="📈")

st.title("2222scouter Monthly Listener Tracker")

# Load data from GitHub raw CSV (updates automatically after each run)
@st.cache_data(ttl=300)  # Cache for 5 minutes
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
    # Tab layout: Graph and Table
    tab1, tab2 = st.tabs(["📊 Growth Chart", "📋 Full Data Table"])

    with tab1:
        st.subheader("Monthly Listeners Over Time")
        fig = px.line(df, x='timestamp', y='monthly_listeners', color='artist',
                      markers=True, title='Listener Trend by Artist')
        fig.update_layout(hovermode='x unified', legend_title='Artist')
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Raw CSV Data (All Rows & Columns)")
        # Show full table with all columns
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "timestamp": st.column_config.DateColumn("Timestamp", format="D MMM YYYY HH:mm"),
                "monthly_listeners": st.column_config.NumberColumn("Monthly Listeners", format="%d"),
                "change_since_yesterday": st.column_config.NumberColumn("Change Yesterday", format="%+d"),
                "pct_since_yesterday": st.column_config.NumberColumn("Pct Yesterday", format="%+.1f%%"),
                "change_day1_to_day2": st.column_config.NumberColumn("Change Day1→Day2", format="%+d"),
                "pct_day1_to_day2": st.column_config.NumberColumn("Pct Day1→Day2", format="%+.1f%%"),
                "change_day2_to_day3": st.column_config.NumberColumn("Change Day2→Day3", format="%+d"),
                "pct_day2_to_day3": st.column_config.NumberColumn("Pct Day2→Day3", format="%+.1f%%"),
            }
        )

        # Optional: Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="spotify_listeners_history.csv",
            mime="text/csv"
        )

    # Refresh button at bottom
    if st.button("Refresh Data (from GitHub)"):
        st.cache_data.clear()
        st.rerun()

st.markdown("Data updates via GitHub Actions (3–4 PM EST). Add artists in your Google Sheet — they auto-appear here.")
