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
            min-width: 120px;
        }
        .stDataFrame th:first-child {
            background-color: #e8e8e8;
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

        result = []
        for artist in df['artist'].unique():
            artist_rows = df[df['artist'] == artist].sort_values('timestamp', ascending=False).head(8)  # 7 days + current = 8 points max
            if len(artist_rows) == 0:
                continue

            latest = artist_rows.iloc[0]
            row = {
                'artist': artist,
                'time': latest['timestamp'].strftime('%Y-%m-%d %H:%M UTC'),
                'monthly_listeners': latest['monthly_listeners'],
            }

            # Rolling daily changes (latest vs 1 day ago, 1 vs 2, 2 vs 3, ..., 6 vs 7)
            for i in range(1, 8):
                if i < len(artist_rows):
                    prev = artist_rows.iloc[i]
                    delta = latest['monthly_listeners'] - prev['monthly_listeners']
                    pct = round(delta / prev['monthly_listeners'] * 100, 1) if prev['monthly_listeners'] > 0 else 0
                    row[f'change_day{i-1}_to_day{i}'] = delta
                    row[f'pct_day{i-1}_to_day{i}'] = pct
                else:
                    row[f'change_day{i-1}_to_day{i}'] = 0
                    row[f'pct_day{i-1}_to_day{i}'] = 0

            result.append(row)

        result_df = pd.DataFrame(result)
        # Reorder columns exactly as requested
        cols = ['artist', 'time', 'monthly_listeners',
                'change_day0_to_day1', 'pct_day0_to_day1',  # since yesterday
                'change_day1_to_day2', 'pct_day1_to_day2',
                'change_day2_to_day3', 'pct_day2_to_day3']
        result_df = result_df[cols]
        return result_df
    except:
        return pd.DataFrame()

df = load_and_process()

if df.empty:
    st.text("no data yet")
else:
    # Format for display
    def fmt_change(x):
        return f"{x:+,d}" if isinstance(x, (int, float)) else x

    def fmt_pct(x):
        return f"{x:+.1f}%" if isinstance(x, (int, float)) else x

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
            "artist": st.column_config.TextColumn("Artist", width="medium"),
            "time": st.column_config.TextColumn("Time"),
            "monthly_listeners": st.column_config.TextColumn("Monthly Listeners"),
            "change_day0_to_day1": st.column_config.TextColumn("Change Yesterday"),
            "pct_day0_to_day1": st.column_config.TextColumn("Pct Yesterday"),
            "change_day1_to_day2": st.column_config.TextColumn("Day1→Day2"),
            "pct_day1_to_day2": st.column_config.TextColumn("Pct Day1→Day2"),
            "change_day2_to_day3": st.column_config.TextColumn("Day2→Day3"),
            "pct_day2_to_day3": st.column_config.TextColumn("Pct Day2→Day3"),
        }
    )

# Refresh button
if st.button("Refresh"):
    st.rerun()
