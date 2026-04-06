from datetime import datetime, timezone
import re
import pandas as pd
from playwright.sync_api import sync_playwright
import requests
import os

# Same sheet as before
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSa5tdG_4WSMrmGcaJhOZBwC_6oyXVSbpLjdrf8hfgRB_rHwm49rohMiE6ZATi42ScZDo5d1_fAW_Sw/pub?gid=0&single=true&output=csv"

# Load artists
try:
    df_artists = pd.read_csv(SHEET_CSV_URL)
    name_col = next((c for c in df_artists.columns if 'artist' in c.lower() or 'name' in c.lower()), df_artists.columns[0])
    url_col = next((c for c in df_artists.columns if 'url' in c.lower() or 'spotify' in c.lower()), df_artists.columns[1])
    ARTISTS = [{"name": str(r[name_col]).strip(), "url": str(r[url_col]).strip()} 
               for _, r in df_artists.iterrows() 
               if 'open.spotify.com/artist' in str(r[url_col])]
    print(f"Loaded {len(ARTISTS)} artists")
except:
    print("Could not load sheet, using fallback")
    ARTISTS = [
        {"name": "Grace Ives", "url": "https://open.spotify.com/artist/4TZieE5978SbTInJswaay2"},
        {"name": "King Kylie", "url": "https://open.spotify.com/artist/16PVIKGOsSoCCAIBANjgil"},
    ]

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
        print("✅ Telegram alert sent!")
    else:
        print("⚠️ Telegram not configured (check secrets)")

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

for a in ARTISTS:
    count = get_monthly_listeners(a["url"])
    if count is not None:
        print(f"✅ {a['name']}: {count:,} monthly listeners")

        # Simulate a big change for testing (remove this later)
        # For real test, we compare with previous data
        print(f"   → Would check change vs previous scan here")

print("\nTest scraper finished. Check if Telegram alert was sent.")
