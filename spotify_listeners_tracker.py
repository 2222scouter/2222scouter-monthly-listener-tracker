from datetime import datetime, timezone
import re
import pandas as pd
from playwright.sync_api import sync_playwright
import requests
import os

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
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})
        print("✅ Telegram alert sent")
    else:
        print("⚠️ Telegram not configured")

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
today_date = datetime.now(timezone.utc).date()

new_data = []

for a in ARTISTS:
    count = get_monthly_listeners(a["url"])
    if count is not None:
        print(f"✅ {a['name']}: {count:,} monthly listeners")
        new_data.append({"timestamp": timestamp, "artist": a["name"], "monthly_listeners": count, "date": today_date})

# Save and check for alerts
if new_data:
    df_new = pd.DataFrame(new_data)
    try:
        df_old = pd.read_csv("spotify_listeners_history.csv")
        df = pd.concat([df_old, df_new], ignore_index=True)
    except FileNotFoundError:
        df = df_new

    # Keep all history but drop exact duplicate timestamps
    df = df.drop_duplicates(subset=['timestamp', 'artist'], keep='last')
    df.to_csv("spotify_listeners_history.csv", index=False)

    # Alert logic: compare to the most recent scan from a PREVIOUS day
    for row in df_new.itertuples():
        artist = row.artist
        new_count = row.monthly_listeners
        new_date = row.date

        # Find the most recent scan from a different day
        prev_scans = df[(df['artist'] == artist) & (df['date'] < new_date)]
        if not prev_scans.empty:
            prev = prev_scans.iloc[-1]
            last_count = prev['monthly_listeners']
            if last_count > 0:
                pct_change = abs((new_count - last_count) / last_count * 100)
                if pct_change > CHANGE_THRESHOLD_PERCENT:
                    delta = new_count - last_count
                    msg = f"🚨 <b>Big Change Detected!</b>\n\n<b>{artist}</b>\n{last_count:,} → {new_count:,} ({delta:+,})\n{pct_change:.1f}% on {new_date}"
                    send_telegram(msg)

print("Scraper finished!")
