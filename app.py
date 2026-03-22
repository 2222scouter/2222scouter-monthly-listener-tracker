@st.cache_data(ttl=300)
def load_data():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        # Keep only the latest row per artist (most recent timestamp)
        df = df.sort_values(['artist', 'timestamp'], ascending=[True, False])
        df = df.drop_duplicates(subset='artist', keep='first')  # Latest per artist
        # Fill missing gains with 0
        gain_cols = [c for c in df.columns if 'change_' in c or 'pct_' in c]
        df[gain_cols] = df[gain_cols].fillna(0)
        return df
    except:
        return pd.DataFrame()
