from datetime import datetime, timezone
import re
import pandas as pd
from playwright.sync_api import sync_playwright
import os

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSa5tdG_4WSMrmGcaJhOZBwC_6oyXVSbpLjdrf8hfgRB_rHwm49rohMiE6ZATi42ScZDo5d1_fAW_Sw/pub?gid=0&single=true&output=csv"

try:
    df_artists = pd.read_csv(SHEET_CSV_URL)
    name_col = next((c for c in df_artists.columns if 'artist' in c.lower() or 'name' in c.lower()), df_artists.columns[0])
    url_col = next((c for c in df_artists.columns if 'url' in c.lower() or 'spotify' in c.lower()), df_artists.columns[1])
    ARTISTS = [{"name": str(r[name_col]).strip(), "url": str(r[url_col]).strip()} 
               for _, r in df_artists.iterrows() 
               if 'open.spotify.com/artist' in str(r[url_col])]
    print(f"Loaded {len(ARTISTS)} artists from sheet")
except:
    ARTISTS = [
        {"name": "Grace Ives", "url": "https://open.spotify.com/artist/4TZieE5978SbTInJswaay2"},
        {"name": "King Kylie", "url": "https://open.spotify.com/artist/16PVIKGOsSoCCAIBANjgil"},
    ]
    print("Sheet load failed, using fallback")

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

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

new_data = []

for a in ARTISTS:
    count = get_monthly_listeners(a["url"])
    if count is not None:
        print(f"✅ {a['name']}: {count:,} monthly listeners")
        new_data.append({"timestamp": timestamp, "artist": a["name"], "monthly_listeners": count})

# Save history (append + deduplicate)
if new_data:
    df_new = pd.DataFrame(new_data)
    try:
        df_old = pd.read_csv("spotify_listeners_history.csv")
        df = pd.concat([df_old, df_new], ignore_index=True)
    except FileNotFoundError:
        df = df_new
    df = df.drop_duplicates(subset=['timestamp', 'artist'], keep='last')
    df.to_csv("spotify_listeners_history.csv", index=False)
    print(f"✅ Saved {len(new_data)} listener entries")
else:
    print("No new data found")

print("Scraper finished!")
