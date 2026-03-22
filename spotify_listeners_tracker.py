from datetime import datetime, timezone, timedelta
import re
import pandas as pd
from playwright.sync_api import sync_playwright
import requests
import os
import plotly.express as px

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSa5tdG_4WSMrmGcaJhOZBwC_6oyXVSbpLjdrf8hfgRB_rHwm49rohMiE6ZATi42ScZDo5d1_fAW_Sw/pub?gid=0&single=true&output=csv"

try:
    df_artists = pd.read_csv(SHEET_CSV_URL)
    name_col = next((c for c in df_artists.columns if 'artist' in c.lower() or 'name' in c.lower()), df_artists.columns[0])
    url_col = next((c for c in df_artists.columns if 'url' in c.lower() or 'spotify' in c.lower()), df_artists.columns[1])
    ARTISTS = [{"name": str(r[name_col]).strip(), "url": str(r[url_col]).strip()} 
               for _, r in df_artists.iterrows() 
               if 'open.spotify.com/artist' in str(r[url_col])]
    print(f"Loaded {len(ARTISTS)} artists")
except:
    ARTISTS = [
        {"name": "Grace Ives", "url": "https://open.spotify.com/artist/4TZieE5978SbTInJswaay2"},
        {"name": "King Kylie", "url": "https://open.spotify.com/artist/16PVIKGOsSoCCAIBANjgil"},
    ]
    print("Sheet load failed, using fallback")

CHANGE_THRESHOLD_PERCENT = 5.0
CHANGE_THRESHOLD_ABSOLUTE = 15000

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

def send_telegram(msg):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})
        print("Alert sent")

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

try:
    df_hist = pd.read_csv("spotify_listeners_history.csv")
except FileNotFoundError:
    df_hist = pd.DataFrame(columns=['timestamp', 'artist', 'monthly_listeners',
                                    'change_since_yesterday', 'pct_since_yesterday',
                                    'change_day1_to_day2', 'pct_day1_to_day2',
                                    'change_day2_to_day3', 'pct_day2_to_day3'])

new_data = []
for a in ARTISTS:
    count = get_monthly_listeners(a["url"])
    if count is None: continue
    print(f"✅ {a['name']}: {count:,} at {timestamp}")
    new_data.append({"timestamp": timestamp, "artist": a["name"], "monthly_listeners": count})

if new_data:
    df_new = pd.DataFrame(new_data)
    
    has_old_data = False
    df_old = None
    
    try:
        df_old = pd.read_csv("spotify_listeners_history.csv")
        df = pd.concat([df_old, df_new], ignore_index=True)
        df = df.drop_duplicates(subset=['timestamp', 'artist'], keep='last')
        has_old_data = True
    except FileNotFoundError:
        df = df_new
        print("First run — no history yet, skipping alerts")
    except Exception as e:
        print(f"Error reading old CSV: {e}")
        df = df_new

    df.to_csv("spotify_listeners_history.csv", index=False)

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

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    fig = px.line(df, x='timestamp', y='monthly_listeners', color='artist',
                  markers=True, title='2222scouter Monthly Listener Tracker',
                  labels={'timestamp': 'Date & Time', 'monthly_listeners': 'Monthly Listeners'})
    fig.update_layout(hovermode='x unified', legend_title='Artist')
    fig.write_html('dashboard.html')
    print("Dashboard updated!")
