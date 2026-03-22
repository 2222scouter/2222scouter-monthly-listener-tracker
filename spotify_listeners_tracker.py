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

new_data = []
for artist in ARTISTS:
    try:
        count = get_monthly_listeners(artist["url"])
        if count is not None:
            new_data.append({"timestamp": timestamp, "artist": artist["name"], "monthly_listeners": count})
            print(f"✅ {artist['name']}: {count:,} at {timestamp}")
    except Exception as e:
        print(f"Error for {artist['name']}: {e}")

if new_data:
    df_new = pd.DataFrame(new_data)
    df_new['timestamp_dt'] = pd.to_datetime(df_new['timestamp'], utc=True)
    
    has_old_data = False
    df_old = None
    
    try:
        df_old = pd.read_csv("spotify_listeners_history.csv")
        df_old['timestamp_dt'] = pd.to_datetime(df_old['timestamp'], utc=True)
        df = pd.concat([df_old, df_new], ignore_index=True)
        df = df.drop_duplicates(subset=['timestamp', 'artist'], keep='last')
        has_old_data = True
    except FileNotFoundError:
        df = df_new
        print("First run — no history yet, skipping alerts")
    except Exception as e:
        print(f"Error reading old CSV: {e}")
        df = df_new

    # Calculate gains for new rows
    df['change_since_yesterday'] = ""
    df['change_past_2_days'] = ""
    df['change_past_3_days'] = ""

    if has_old_data:
        df = df.sort_values(['artist', 'timestamp_dt'])
        for artist in df['artist'].unique():
            artist_df = df[df['artist'] == artist].copy()
            for i in range(1, len(artist_df)):
                idx = artist_df.index[i]
                current_count = artist_df.iloc[i]['monthly_listeners']
                current_time = artist_df.iloc[i]['timestamp_dt']

                # Change since yesterday (~24h ago)
                yesterday = current_time - timedelta(days=1)
                prev_yesterday = artist_df[artist_df['timestamp_dt'] <= yesterday]
                if not prev_yesterday.empty:
                    closest = prev_yesterday.iloc[-1]
                    df.at[idx, 'change_since_yesterday'] = current_count - closest['monthly_listeners']

                # Change past 2 days (~48h ago)
                two_days_ago = current_time - timedelta(days=2)
                prev_2days = artist_df[artist_df['timestamp_dt'] <= two_days_ago]
                if not prev_2days.empty:
                    closest = prev_2days.iloc[-1]
                    df.at[idx, 'change_past_2_days'] = current_count - closest['monthly_listeners']

                # Change past 3 days (~72h ago)
                three_days_ago = current_time - timedelta(days=3)
                prev_3days = artist_df[artist_df['timestamp_dt'] <= three_days_ago]
                if not prev_3days.empty:
                    closest = prev_3days.iloc[-1]
                    df.at[idx, 'change_past_3_days'] = current_count - closest['monthly_listeners']

    # Save CSV without temp column
    df_save = df.drop(columns=['timestamp_dt'], errors='ignore')
    df_save.to_csv("spotify_listeners_history.csv", index=False)

    # Alerts (unchanged)
    if has_old_data and df_old is not None:
        for row in df_new.itertuples():
            artist_name = row.artist
            new_count = row.monthly_listeners
            prev = df_old[df_old['artist'] == artist_name]
            if not prev.empty:
                last_count = prev.iloc[-1]['monthly_listeners']
                if last_count > 0:
                    pct_change = abs((new_count - last_count) / last_count * 100)
                    abs_change = abs(new_count - last_count)
                    if pct_change > CHANGE_THRESHOLD_PERCENT or abs_change > CHANGE_THRESHOLD_ABSOLUTE:
                        delta = new_count - last_count
                        msg = f"🚨 <b>Big listener change!</b>\n\n<b>{artist_name}</b>: {last_count:,} → {new_count:,} ({delta:+,})\n{pct_change:.1f}% at {timestamp}"
                        send_telegram(msg)

    # Dashboard
    df_plot = df.drop(columns=['timestamp_dt'], errors='ignore')
    df_plot['timestamp'] = pd.to_datetime(df_plot['timestamp'])
    fig = px.line(df_plot, x='timestamp', y='monthly_listeners', color='artist',
                  markers=True, title='2222scouter Monthly Listener Tracker',
                  labels={'timestamp': 'Date & Time', 'monthly_listeners': 'Monthly Listeners'})
    fig.update_layout(hovermode='x unified', legend_title='Artist')
    fig.write_html('dashboard.html')
    print("Dashboard updated!")
