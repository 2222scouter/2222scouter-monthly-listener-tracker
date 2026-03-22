from datetime import datetime
import re
import pandas as pd
from playwright.sync_api import sync_playwright
import requests
import os
import plotly.express as px

# ============== EDIT THIS SECTION WITH YOUR ARTISTS ==============
ARTISTS = [
    {"name": "King Kylie", "url": "https://open.spotify.com/artist/16PVIKGOsSoCCAIBANjgil?si=M8POjTYTRQekxi5qfbXwnQ"},
    {"name": "Grace Ives", "url": "https://open.spotify.com/artist/4TZieE5978SbTInJswaay2?si=p0GimnJVTNCwVnRH8lMd7Q"},
    # Add more lines here for up to 10+ artists:
    # {"name": "Artist 3", "url": "https://open.spotify.com/artist/ANOTHER_ID"},
]

CHANGE_THRESHOLD_PERCENT = 5.0     # Alert if % change > this
CHANGE_THRESHOLD_ABSOLUTE = 15000  # OR if raw change > this
# ================================================================

def get_monthly_listeners(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)
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
        print("📨 Telegram alert sent!")

timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
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
    try:
        df_old = pd.read_csv("spotify_listeners_history.csv")
        df = pd.concat([df_old, df_new], ignore_index=True)
        df = df.drop_duplicates(subset=['timestamp', 'artist'], keep='last')
    except FileNotFoundError:
        df = df_new

    # Send alerts for big changes
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

    df.to_csv("spotify_listeners_history.csv", index=False)

    # Create branded dashboard
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    fig = px.line(df, x='timestamp', y='monthly_listeners', color='artist',
                  markers=True, title='2222scouter Monthly Listener Tracker',
                  labels={'timestamp': 'Date & Time', 'monthly_listeners': 'Monthly Listeners'})
    fig.update_layout(hovermode='x unified', legend_title='Artist')
    fig.write_html('dashboard.html')
    print("📈 Dashboard updated!")
