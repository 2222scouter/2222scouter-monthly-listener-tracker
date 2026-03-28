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

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

new_listeners = []
new_streams = []
new_followers = []
new_popularity = []

for a in ARTISTS:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(a["url"], wait_until="networkidle", timeout=120000)
            page.wait_for_timeout(8000)

            # Scroll to load dynamic content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(6000)

            # 1. Monthly Listeners (most reliable)
            listeners = None
            try:
                elem = page.get_by_text(re.compile("monthly listeners", re.IGNORECASE)).first
                if elem:
                    text = elem.inner_text().strip()
                    match = re.search(r'([\d,]+)', text)
                    if match:
                        listeners = int(match.group(1).replace(',', ''))
            except:
                pass

            # 2. Total Streams
            streams = None
            try:
                page_text = page.text_content("body").lower()
                patterns = [r'([\d,]+)\s*total\s*streams?', r'([\d,]+)\s*streams?', r'all-time.*streams?\s*([\d,]+)']
                for pattern in patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        numbers = [int(m.replace(',', '')) for m in matches if m.replace(',', '').isdigit()]
                        if numbers:
                            streams = max(numbers)
                            break
            except:
                pass

            # 3. Followers
            followers = None
            try:
                elem = page.get_by_text(re.compile(r'(\d[\d,]*)\s*followers?', re.IGNORECASE)).first
                if elem:
                    text = elem.inner_text()
                    match = re.search(r'([\d,]+)', text)
                    if match:
                        followers = int(match.group(1).replace(',', ''))
            except:
                pass

            # 4. Popularity Score
            popularity = None
            try:
                text = page.text_content("body")
                match = re.search(r'(\d{1,2})\s*%?\s*popularity', text, re.IGNORECASE)
                if match:
                    popularity = int(match.group(1))
                else:
                    # Look for isolated 0-100 near top
                    match = re.search(r'\b(\d{1,2})\b', text[:1500])
                    if match and 0 <= int(match.group(1)) <= 100:
                        popularity = int(match.group(1))
            except:
                pass

            # Log results
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
            else:
                print(f"⚠️  {a['name']}: Could not find followers")

            if popularity is not None:
                print(f"✅ {a['name']}: Popularity {popularity}/100")
                new_popularity.append({"timestamp": timestamp, "artist": a["name"], "popularity": popularity})
            else:
                print(f"⚠️  {a['name']}: Could not find popularity score")

            browser.close()

    except Exception as e:
        print(f"❌ Error scraping {a['name']}: {e}")

# Save all histories
def save_history(filename, new_data):
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

save_history("spotify_listeners_history.csv", new_listeners)
save_history("spotify_streams_history.csv", new_streams)
save_history("spotify_followers_history.csv", new_followers)
save_history("spotify_popularity_history.csv", new_popularity)

print("Scraper finished!")
