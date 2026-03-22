import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="2222scouter Listener Tracker", layout="wide", page_icon="📈")

st.title("2222scouter Monthly Listener Tracker")

# Load data from GitHub raw CSV
@st.cache_data(ttl=300)  # refresh every 5 minutes
def load_data():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Replace missing values with "-"
        df = df.fillna("-")
        return df
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No data yet — wait for the next scheduled run or trigger manually in Actions.")
else:
    tab1, tab2 = st.tabs(["📊 Growth Chart", "📋 Full CSV Table"])

    with tab1:
        st.subheader("Monthly Listeners Over Time")
        fig = px.line(df[df['monthly_listeners'] != "-"], 
                      x='timestamp', y='monthly_listeners', color='artist',
                      markers=True, title='Listener Trend by Artist')
        fig.update_layout(hovermode='x unified', legend_title='Artist')
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Full Data Table (like the CSV)")

        # Format numbers nicely
        def format_number(x):
            if x == "-":
                return "-"
            try:
                return f"{float(x):,}"
            except:
                return x

        def format_change(x):
            if x == "-":
                return "-"
            try:
                return f"{float(x):+,.0f}"
            except:
                return x

        def format_pct(x):
            if x == "-":
                return "-"
            try:
                return f"{float(x):+.1f}%"
            except:
                return x

        # Apply formatting
        display_df = df.copy()
        for col in display_df.columns:
            if "change_" in col:
                display_df[col] = display_df[col].apply(format_change)
            elif "pct_" in col:
                display_df[col] = display_df[col].apply(format_pct)
            elif col == "monthly_listeners":
                display_df[col] = display_df[col].apply(format_number)
            elif col == "timestamp":
                display_df[col] = display_df[col].apply(lambda x: "-" if x == "-" else x.strftime("%Y-%m-%d %H:%M UTC"))

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "timestamp": "Timestamp",
                "artist": "Artist",
                "monthly_listeners": "Monthly Listeners",
                "change_since_yesterday": "Change Yesterday",
                "pct_since_yesterday": "Pct Yesterday",
                "change_day1_to_day2": "Change Day1→Day2",
                "pct_day1_to_day2": "Pct Day1→Day2",
                "change_day2_to_day3": "Change Day2→Day3",
                "pct_day2_to_day3": "Pct Day2→Day3",
            }
        )

        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="spotify_listeners_history.csv",
            mime="text/csv"
        )

    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

st.markdown("Data updates via GitHub Actions (3–4 PM EST). Add artists in your Google Sheet — they auto-appear here.")
