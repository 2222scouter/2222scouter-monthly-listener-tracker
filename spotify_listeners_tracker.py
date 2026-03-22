from datetime import datetime, timezone, timedelta
import re
import pandas as pd
from playwright.sync_api import sync_playwright
import requests
import os
import plotly.express as px

# ============== AUTO-LOAD ARTISTS FROM YOUR GOOGLE SHEET ==============
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSa5tdG_4WSMrmGcaJhOZBwC_6oyXVSbpLjdrf8hfgRB_rHwm49rohMiE6ZATi42ScZDo5d1_fAW_Sw/pub?gid=0&single=true&output=csv"

try:
    artists_df = pd.read_csv(SHEET_CSV_URL)
    name_col = next((col for col in artists_df.columns if 'artist' in col.lower() or 'name' in col.lower()), artists_df.columns[0])
    url_col = next((col for col in artists_df.columns if 'url' in col.lower() or 'spotify' in col.lower()), artists_df.columns[1])
    
    ARTISTS = [
        {"name": str(row[name_col]).strip(), "url": str(row[url_col]).strip()}
        for _, row in artists_df.iterrows()
        if pd.notna(row[name_col]) and pd.notna(row[url_col]) and 'open.spotify.com/artist' in str(row[url_col])
    ]
    print(f"Loaded {len(ARTISTS)} artists from Google Sheet: {', '.join(a['name'] for a in ARTISTS)}")
except Exception as e:
    print(f"Error loading sheet: {e}. Using fallback artists.")
    ARTISTS = [
        {"name": "Grace Ives", "url": "https://open.spotify.com/artist/4TZieE5978SbTInJswaay2"},
        {"name": "King Kylie", "url": "https://open.spotify.com/artist/16PVIKGOsSoCCAIBANjgil"},
    ]

CHANGE_THRESHOLD_PERCENT = 5.0
CHANGE_THRESHOLD_ABSOLUTE = 15000
# =====================================================================

def get_monthly_listeners(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        elem = page.get_by_text(re.compile("monthly listeners", re.IGNORECASE)).first
        text = elem.inner_text().strip() if elem else ""
        match = re.search(r'([\d,]+)', text)
        browser.close()
        return int(match.group(1).replace(',', '')) if match else None

def send_telegram(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
        print("Telegram alert sent!")

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
now_dt = datetime.now(timezone.utc)

# Load existing history (one row per artist)
try:
    df_history = pd.read_csv("spotify_listeners_history.csv")
    df_history.set_index('artist', inplace=True)
except FileNotFoundError:
    df_history = pd.DataFrame(columns=[
        'artist', 'timestamp', 'monthly_listeners',
        'listeners_1day_ago', 'timestamp_1day_ago',
        'listeners_2days_ago', 'timestamp_2days_ago',
        'listeners_3days_ago', 'timestamp_3days_ago',
        'change_since_yesterday', 'pct_since_yesterday',
        'change_day1_to_day2', 'pct_day1_to_day2',
        'change_day2_to_day3', 'pct_day2_to_day3'
    ])
    df_history.set_index('artist', inplace=True)

new_rows = []
for artist in ARTISTS:
    try:
        count = get_monthly_listeners(artist["url"])
        if count is not None:
            new_rows.append({
                'artist': artist["name"],
                'timestamp': timestamp,
                'monthly_listeners': count
            })
            print(f"✅ {artist['name']}: {count:,} at {timestamp}")
    except Exception as e:
        print(f"Error for {artist['name']}: {e}")

if new_rows:
    df_new = pd.DataFrame(new_rows)
    df_new.set_index('artist', inplace=True)

    for artist, row in df_new.iterrows():
        new_count = row['monthly_listeners']
        if artist in df_history.index:
            old_row = df_history.loc[artist]

            # Safely get old values (None if missing column or value)
            listeners_1day_ago = old_row.get('listeners_1day_ago')
            timestamp_1day_ago = old_row.get('timestamp_1day_ago')
            listeners_2days_ago = old_row.get('listeners_2days_ago')
            timestamp_2days_ago = old_row.get('timestamp_2days_ago')
            listeners_3days_ago = old_row.get('listeners_3days_ago')
            timestamp_3days_ago = old_row.get('timestamp_3days_ago')

            # Shift old values back
            df_history.at[artist, 'listeners_3days_ago'] = listeners_2days_ago
            df_history.at[artist, 'timestamp_3days_ago'] = timestamp_2days_ago
            df_history.at[artist, 'listeners_2days_ago'] = listeners_1day_ago
            df_history.at[artist, 'timestamp_2days_ago'] = timestamp_1day_ago
            df_history.at[artist, 'listeners_1day_ago'] = old_row['monthly_listeners']
            df_history.at[artist, 'timestamp_1day_ago'] = old_row['timestamp']

            # Calculate sequential changes (safe checks)
            # Change since yesterday (current vs 1 day ago)
            if listeners_1day_ago is not None and listeners_1day_ago > 0:
                delta_yest = new_count - listeners_1day_ago
                pct_yest = (delta_yest / listeners_1day_ago * 100)
                df_history.at[artist, 'change_since_yesterday'] = delta_yest
                df_history.at[artist, 'pct_since_yesterday'] = round(pct_yest, 1)

            # Day 1 to Day 2 (1day ago vs 2days ago)
            if listeners_1day_ago is not None and listeners_2days_ago is not None and listeners_2days_ago > 0:
                delta_1to2 = listeners_1day_ago - listeners_2days_ago
                pct_1to2 = (delta_1to2 / listeners_2days_ago * 100)
                df_history.at[artist, 'change_day1_to_day2'] = delta_1to2
                df_history.at[artist, 'pct_day1_to_day2'] = round(pct_1to2, 1)

            # Day 2 to Day 3 (2days ago vs 3days ago)
            if listeners_2days_ago is not None and listeners_3days_ago is not None and listeners_3days_ago > 0:
                delta_2to3 = listeners_2days_ago - listeners_3days_ago
                pct_2to3 = (delta_2to3 / listeners_3days_ago * 100)
                df_history.at[artist, 'change_day2_to_day3'] = delta_2to3
                df_history.at[artist, 'pct_day2_to_day3'] = round(pct_2to3, 1)

            # Update current
            df_history.at[artist, 'timestamp'] = timestamp
            df_history.at[artist, 'monthly_listeners'] = new_count
        else:
            # New artist
            df_history = pd.concat([df_history, pd.DataFrame({
                'timestamp': [timestamp],
                'monthly_listeners': [new_count],
                'listeners_1day_ago': [None],
                'timestamp_1day_ago': [None],
                'listeners_2days_ago': [None],
                'timestamp_2days_ago': [None],
                'listeners_3days_ago': [None],
                'timestamp_3days_ago': [None],
                'change_since_yesterday': [None],
                'pct_since_yesterday': [None],
                'change_day1_to_day2': [None],
                'pct_day1_to_day2': [None],
                'change_day2_to_day3': [None],
                'pct_day2_to_day3': [None]
            }, index=[artist])])

    # Save updated history (one row per artist)
    df_history.reset_index().to_csv("spotify_listeners_history.csv", index=False)

    # Alerts on significant current change
    for artist, row in df_new.iterrows():
        if artist in df_history.index:
            old_row = df_history.loc[artist]
            last_count = old_row['monthly_listeners']
            new_count = row['monthly_listeners']
            if last_count > 0:
                pct_change = abs((new_count - last_count) / last_count * 100)
                abs_change = abs(new_count - last_count)
                if pct_change > CHANGE_THRESHOLD_PERCENT or abs_change > CHANGE_THRESHOLD_ABSOLUTE:
                    delta = new_count - last_count
                    msg = f"🚨 <b>Big listener change!</b>\n\n<b>{artist}</b>: {last_count:,} → {new_count:,} ({delta:+,})\n{pct_change:.1f}% at {timestamp}"
                    send_telegram(msg)

    # Dashboard
    df_plot = df_history.reset_index()
    df_plot['timestamp'] = pd.to_datetime(df_plot['timestamp'])
    fig = px.line(df_plot, x='timestamp', y='monthly_listeners', color='artist',
                  markers=True, title='2222scouter Monthly Listener Tracker',
                  labels={'timestamp': 'Date & Time', 'monthly_listeners': 'Monthly Listeners'})
    fig.update_layout(hovermode='x unified', legend_title='Artist')
    fig.write_html('dashboard.html')
    print("Dashboard updated!")
