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
    df_hist = pd.read_csv("spotify_listeners_history.csv").set_index('artist')
except FileNotFoundError:
    df_hist = pd.DataFrame(columns=['artist', 'timestamp', 'monthly_listeners',
                                    'listeners_1day_ago', 'listeners_2days_ago', 'listeners_3days_ago',
                                    'change_since_yesterday', 'pct_since_yesterday',
                                    'change_day1_to_day2', 'pct_day1_to_day2',
                                    'change_day2_to_day3', 'pct_day2_to_day3'])

for a in ARTISTS:
    count = get_monthly_listeners(a["url"])
    if count is None: continue
    print(f"✅ {a['name']}: {count:,} at {timestamp}")

    artist = a["name"]
    if artist in df_hist.index:
        old = df_hist.loc[artist]

        # Shift history
        df_hist.at[artist, 'listeners_3days_ago'] = old.get('listeners_2days_ago')
        df_hist.at[artist, 'listeners_2days_ago'] = old.get('listeners_1day_ago')
        df_hist.at[artist, 'listeners_1day_ago'] = old.get('monthly_listeners')

        # Gains
        l1 = old.get('listeners_1day_ago')
        l2 = old.get('listeners_2days_ago')
        l3 = old.get('listeners_3days_ago')

        if pd.notnull(l1) and l1 > 0:
            delta = count - l1
            pct = round(delta / l1 * 100, 1)
            df_hist.at[artist, 'change_since_yesterday'] = delta
            df_hist.at[artist, 'pct_since_yesterday'] = pct

        if pd.notnull(l1) and pd.notnull(l2) and l2 > 0:
            delta = l1 - l2
            pct = round(delta / l2 * 100, 1)
            df_hist.at[artist, 'change_day1_to_day2'] = delta
            df_hist.at[artist, 'pct_day1_to_day2'] = pct

        if pd.notnull(l2) and pd.notnull(l3) and l3 > 0:
            delta = l2 - l3
            pct = round(delta / l3 * 100, 1)
            df_hist.at[artist, 'change_day2_to_day3'] = delta
            df_hist.at[artist, 'pct_day2_to_day3'] = pct

        # Update current
        df_hist.at[artist, 'timestamp'] = timestamp
        df_hist.at[artist, 'monthly_listeners'] = count
    else:
        df_hist = pd.concat([df_hist, pd.DataFrame({
            'timestamp': [timestamp], 'monthly_listeners': [count],
            'listeners_1day_ago': [None], 'listeners_2days_ago': [None], 'listeners_3days_ago': [None],
            'change_since_yesterday': [None], 'pct_since_yesterday': [None],
            'change_day1_to_day2': [None], 'pct_day1_to_day2': [None],
            'change_day2_to_day3': [None], 'pct_day2_to_day3': [None]
        }, index=[artist])])

    # Alerts
    old_count = df_hist.at[artist, 'monthly_listeners'] if artist in df_hist.index else None
    if pd.notnull(old_count) and old_count > 0:
        pct_change = abs((count - old_count) / old_count * 100)
        abs_change = abs(count - old_count)
        if pct_change > CHANGE_THRESHOLD_PERCENT or abs_change > CHANGE_THRESHOLD_ABSOLUTE:
            delta = count - old_count
            send_telegram(f"🚨 <b>Big change!</b>\n<b>{artist}</b>: {old_count:,} → {count:,} ({delta:+,})\n{pct_change:.1f}% at {timestamp}")

df_hist.reset_index().to_csv("spotify_listeners_history.csv", index=False)

# Dashboard
df_plot = df_hist.reset_index()
df_plot['timestamp'] = pd.to_datetime(df_plot['timestamp'])
fig = px.line(df_plot, x='timestamp', y='monthly_listeners', color='artist',
              markers=True, title='2222scouter Monthly Listener Tracker')
fig.update_layout(hovermode='x unified', legend_title='Artist')
fig.write_html('dashboard.html')
print("Dashboard updated!")
