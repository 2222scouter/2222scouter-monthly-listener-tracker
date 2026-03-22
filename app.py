import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tracker", layout="wide", initial_sidebar_state="collapsed")

# Off-white background, hide sidebar/header
st.markdown("""
    <style>
        section[data-testid="stSidebar"] {display: none;}
        .main .block-container {padding: 1rem 1rem 0rem !important;}
        body, .stApp {background-color: #f8f9fa !important;}
        .tiny-title {
            font-size: 11px;
            color: #aaa;
            text-align: center;
            margin: 20px 0 40px 0;
            letter-spacing: 1px;
        }
        .stDataFrame [data-testid="stTable"] {
            overflow-x: auto;
        }
        .stDataFrame th:first-child, .stDataFrame td:first-child {
            position: sticky;
            left: 0;
            background-color: #f8f9fa;
            z-index: 1;
            min-width: 140px;
            padding: 8px !important;
        }
        .stDataFrame th:first-child {
            background-color: #e0e0e0;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="tiny-title">2222scouter tracker</div>', unsafe_allow_html=True)

# Load and process data
@st.cache_data(ttl=300)
def load_and_process():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df = df.sort_values(['artist', 'timestamp'], ascending=[True, False])

        # Keep only latest per artist
        latest_df = df.drop_duplicates(subset='artist', keep='first')

        # Calculate gains (assuming df has multiple rows per artist for history)
        result = []
        for artist in df['artist'].unique():
            artist_rows = df[df['artist'] == artist].sort_values('timestamp', ascending=False)
            if len(artist_rows) == 0:
                continue

            latest = artist_rows.iloc[0]
            row = {
                'artist': artist,
                'time': latest['timestamp'].strftime('%Y-%m-%d %H:%M UTC'),
                'monthly_listeners': latest['monthly_listeners'],
            }

            # Change Since Yesterday (latest vs previous row)
            if len(artist_rows) > 1:
                yesterday = artist_rows.iloc[1]
                delta_yest = latest['monthly_listeners'] - yesterday['monthly_listeners']
                pct_yest = round(delta_yest / yesterday['monthly_listeners'] * 100, 1) if yesterday['monthly_listeners'] > 0 else 0
                row['change_since_yesterday'] = delta_yest
                row['pct_since_yesterday'] = pct_yest
            else:
                row['change_since_yesterday'] = 0
                row['pct_since_yesterday'] = 0

            # Day1→Day2 (previous vs day before)
            if len(artist_rows) > 2:
                day1 = artist_rows.iloc[1]
                day2 = artist_rows.iloc[2]
                delta_1to2 = day1['monthly_listeners'] - day2['monthly_listeners']
                pct_1to2 = round(delta_1to2 / day2['monthly_listeners'] * 100, 1) if day2['monthly_listeners'] > 0 else 0
                row['change_day1_to_day2'] = delta_1to2
                row['pct_day1_to_day2'] = pct_1to2
            else:
                row['change_day1_to_day2'] = 0
                row['pct_day1_to_day2'] = 0

            # Day2→Day3 (day before vs 2 days before)
            if len(artist_rows) > 3:
                day2 = artist_rows.iloc[2]
                day3 = artist_rows.iloc[3]
                delta_2to3 = day2['monthly_listeners'] - day3['monthly_listeners']
                pct_2to3 = round(delta_2to3 / day3['monthly_listeners'] * 100, 1) if day3['monthly_listeners'] > 0 else 0
                row['change_day2_to_day3'] = delta_2to3
                row['pct_day2_to_day3'] = pct_2to3
            else:
                row['change_day2_to_day3'] = 0
                row['pct_day2_to_day3'] = 0

            result.append(row)

        result_df = pd.DataFrame(result)
        # Select only the columns you want in order
        cols = [
            'artist', 'time', 'monthly_listeners',
            'change_since_yesterday', 'pct_since_yesterday',
            'change_day1_to_day2', 'pct_day1_to_day2',
            'change_day2_to_day3', 'pct_day2_to_day3'
        ]
        result_df = result_df[[c for c in cols if c in result_df.columns]]
        return result_df
    except:
        return pd.DataFrame()

df = load_and_process()

if df.empty:
    st.text("no data yet")
else:
    # Format display
    def fmt_change(x):
        if pd.isna(x) or x == 0:
            return "0"
        return f"{x:+,d}"

    def fmt_pct(x):
        if pd.isna(x) or x == 0:
            return "-"
        return f"{x:+.1f}%"

    display_df = df.copy()
    for col in display_df.columns:
        if 'change_' in col:
            display_df[col] = display_df[col].apply(fmt_change)
        elif 'pct_' in col:
            display_df[col] = display_df[col].apply(fmt_pct)
        elif col == 'monthly_listeners':
            display_df[col] = display_df[col].apply(lambda x: f"{x:,}" if isinstance(x, (int, float)) else x)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "artist": st.column_config.TextColumn("Artist", width="medium", frozen=True),
            "time": st.column_config.TextColumn("Time"),
            "monthly_listeners": st.column_config.TextColumn("Monthly Listeners"),
            "change_since_yesterday": st.column_config.TextColumn("Todays gain/loss"),
            "pct_since_yesterday": st.column_config.TextColumn("Todays gain/loss %"),
            "change_day1_to_day2": st.column_config.TextColumn("Change Day1→Day2"),
            "pct_day1_to_day2": st.column_config.TextColumn("% Day1→Day2"),
            "change_day2_to_day3": st.column_config.TextColumn("Change Day2→Day3"),
            "pct_day2_to_day3": st.column_config.TextColumn("% Day2→Day3"),
        }
    )

# Refresh button
if st.button("Refresh"):
    st.rerun()
