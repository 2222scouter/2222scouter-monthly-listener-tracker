@st.cache_data(ttl=300)
def load_and_process():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        # Force 'artist' column name if it's 'index'
        if 'index' in df.columns:
            df = df.rename(columns={'index': 'artist'})
        if 'artist' not in df.columns:
            df['artist'] = 'Unknown'  # Fallback (rare)
        # Replace NaN with 0 for gain columns
        gain_cols = [c for c in df.columns if 'change_' in c or 'pct_' in c]
        df[gain_cols] = df[gain_cols].fillna(0)
        return df
    except:
        return pd.DataFrame()
