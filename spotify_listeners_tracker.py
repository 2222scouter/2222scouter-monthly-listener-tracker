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
    print(f"Loaded {len(ARTISTS)} artists")
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

def get_total_streams(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=90000)   # longer timeout
        page.wait_for_timeout(8000)
        
        # Multiple ways to find total streams
        page_text = page.text_content("body").lower()
        matches = re.findall(r'([\d,]+)\s*(?:total\s*)?streams?', page_text)
        
        if matches:
            numbers = [int(m.replace(',', '')) for m in matches]
            return max(numbers)
        
        # Try looking for large numbers near "streams"
        browser.close()
        return None

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

new_listeners = []
new_streams = []

for a in ARTISTS:
    listeners = get_monthly_listeners(a["url"])
    streams = get_total_streams(a["url"])
    
    if listeners is not None:
        print(f"✅ {a['name']}: {listeners:,} monthly listeners")
        new_listeners.append({"timestamp": timestamp, "artist": a["name"], "monthly_listeners": listeners})
    
    if streams is not None:
        print(f"✅ {a['name']}: {streams:,} total streams")
        new_streams.append({"timestamp": timestamp, "artist": a["name"], "total_streams": streams})
    else:
        print(f"⚠️  {a['name']}: Could not find total streams")

# Save listeners
if new_listeners:
    df_new_l = pd.DataFrame(new_listeners)
    try:
        df_listeners = pd.read_csv("spotify_listeners_history.csv")
        df_listeners = pd.concat([df_listeners, df_new_l], ignore_index=True)
    except FileNotFoundError:
        df_listeners = df_new_l
    df_listeners = df_listeners.drop_duplicates(subset=['timestamp', 'artist'], keep='last')
    df_listeners.to_csv("spotify_listeners_history.csv", index=False)

# Save streams
if new_streams:
    df_new_s = pd.DataFrame(new_streams)
    try:
        df_streams = pd.read_csv("spotify_streams_history.csv")
        df_streams = pd.concat([df_streams, df_new_s], ignore_index=True)
    except FileNotFoundError:
        df_streams = df_new_s
    df_streams = df_streams.drop_duplicates(subset=['timestamp', 'artist'], keep='last')
    df_streams.to_csv("spotify_streams_history.csv", index=False)
    print(f"✅ Saved {len(new_streams)} stream entries")
else:
    print("No stream data found this run")

print("Scraper finished!")
