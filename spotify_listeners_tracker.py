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

def get_monthly_listeners(page):
    elem = page.get_by_text(re.compile("monthly listeners", re.IGNORECASE)).first
    text = elem.inner_text().strip() if elem else ""
    match = re.search(r'([\d,]+)', text)
    return int(match.group(1).replace(',', '')) if match else None

def get_total_streams(page):
    page_text = page.text_content("body").lower()
    patterns = [
        r'([\d,]+)\s*total\s*streams?',
        r'([\d,]+)\s*streams?',
        r'all-time\s*streams?\s*([\d,]+)',
        r'streamed\s*([\d,]+)'
    ]
    for pattern in patterns:
        matches = re.findall(pattern, page_text)
        if matches:
            numbers = [int(m.replace(',', '')) for m in matches if m.replace(',', '').isdigit()]
            if numbers:
                return max(numbers)
    # Last resort: large numbers > 1M
    large = re.findall(r'\b(\d{1,3}(?:,\d{3})*)\b', page_text)
    for n in large:
        num = int(n.replace(',', ''))
        if num > 1_000_000:
            return num
    return None

def get_followers(page):
    elem = page.get_by_text(re.compile(r'(\d[\d,]*)\s*followers?', re.IGNORECASE)).first
    if elem:
        text = elem.inner_text()
        match = re.search(r'([\d,]+)', text)
        if match:
            return int(match.group(1).replace(',', ''))
    return None

def get_popularity(page):
    # Popularity is usually shown as "X% popularity" or just a number near the top
    text = page.text_content("body")
    match = re.search(r'(\d{1,2})%?\s*popularity', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    # Alternative: look for isolated 0-100 number near artist name
    match = re.search(r'\b(\d{1,2})\b', text[:1000])
    if match and int(match.group(1)) <= 100:
        return int(match.group(1))
    return None

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

new_listeners = []
new_streams = []
new_followers = []
new_popularity = []

for a in ARTISTS:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(a["url"], wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(8000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(4000)

        listeners = get_monthly_listeners(page)
        streams = get_total_streams(page)
        followers = get_followers(page)
        popularity = get_popularity(page)

        if listeners is not None:
            print(f"✅ {a['name']}: {listeners:,} monthly listeners")
            new_listeners.append({"timestamp": timestamp, "artist": a["name"], "monthly_listeners": listeners})

        if streams is not None:
            print(f"✅ {a['name']}: {streams:,} total streams")
            new_streams.append({"timestamp": timestamp, "artist": a["name"], "total_streams": streams})
        else:
            print(f"⚠️  {a['name']}: Could not find total streams")

        if followers is not None:
            print(f"✅ {a['name']}: {followers:,} followers")
            new_followers.append({"timestamp": timestamp, "artist": a["name"], "followers": followers})

        if popularity is not None:
            print(f"✅ {a['name']}: Popularity {popularity}/100")
            new_popularity.append({"timestamp": timestamp, "artist": a["name"], "popularity": popularity})

        browser.close()

# Save all four histories
def save_history(filename, new_data, column_name):
    if not new_data:
        return
    df_new = pd.DataFrame(new_data)
    try:
        df_old = pd.read_csv(filename)
        df_old = pd.concat([df_old, df_new], ignore_index=True)
    except FileNotFoundError:
        df_old = df_new
    df_old = df_old.drop_duplicates(subset=['timestamp', 'artist'], keep='last')
    df_old.to_csv(filename, index=False)
    print(f"✅ Saved {len(new_data)} entries to {filename}")

save_history("spotify_listeners_history.csv", new_listeners, "monthly_listeners")
save_history("spotify_streams_history.csv", new_streams, "total_streams")
save_history("spotify_followers_history.csv", new_followers, "followers")
save_history("spotify_popularity_history.csv", new_popularity, "popularity")

print("All scrapers finished!")
