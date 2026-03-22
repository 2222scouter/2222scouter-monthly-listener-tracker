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

# Load existing history (one row per artist)
try:
    df_history = pd.read_csv("spotify_listeners_history.csv")
    # Make artist the index for easy update
    df_history.set_index('artist', inplace=True)
except FileNotFoundError:
    df_history = pd.DataFrame(columns=[
        'artist', 'timestamp', 'monthly_listeners',
        'change_since_yesterday', 'pct_since_yesterday',
        'change_past_2_days', 'pct_past_2_days',
        'change_past_3_days', 'pct_past_3_days'
    ])
    df_history.set_index('artist', inplace=True)

new_rows = []
for artist in ARTISTS:
    try:
        count = get_monthly_listeners(artist["url"])
        if count is not None:
            new_rows.append({
                'artist': artist["name"],
                'timestamp': timestamp,
                'monthly_listeners': count
            })
            print(f"✅ {artist['name']}: {count:,} at {timestamp}")
    except Exception as e:
        print(f"Error for {artist['name']}: {e}")

if new_rows:
    df_new = pd.DataFrame(new_rows)
    df_new.set_index('artist', inplace=True)

    # Update history with new data
    for artist, row in df_new.iterrows():
        if artist in df_history.index:
            old_row = df_history.loc[artist]

            # Calculate changes
            delta = row['monthly_listeners'] - old_row['monthly_listeners']
            pct = (delta / old_row['monthly_listeners'] * 100) if old_row['monthly_listeners'] > 0 else 0

            # Update gains (since this is daily-ish, "since yesterday" is now the previous row)
            df_history.at[artist, 'change_since_yesterday'] = delta
            df_history.at[artist, 'pct_since_yesterday'] = round(pct, 1)

            # For past 2/3 days — we'd need more history; for now, leave as previous or blank
            # (you can expand later if you want to keep more history snapshots)

            # Update current values
            df_history.at[artist, 'timestamp'] = timestamp
            df_history.at[artist, 'monthly_listeners'] = row['monthly_listeners']
        else:
            # New artist — add row with blank gains
            df_history = pd.concat([df_history, pd.DataFrame({
                'timestamp': [timestamp],
                'monthly_listeners': [row['monthly_listeners']],
                'change_since_yesterday': [""],
                'pct_since_yesterday': [""],
                'change_past_2_days': [""],
                'pct_past_2_days': [""],
                'change_past_3_days': [""],
                'pct_past_3_days': [""]
            }, index=[artist])])

    # Save updated history (one row per artist)
    df_history.reset_index().to_csv("spotify_listeners_history.csv", index=False)

    # Dashboard (simple line plot still, but now based on history)
    df_plot = df_history.reset_index()
    df_plot['timestamp'] = pd.to_datetime(df_plot['timestamp'])
    fig = px.line(df_plot, x='timestamp', y='monthly_listeners', color='artist',
                  markers=True, title='2222scouter Monthly Listener Tracker',
                  labels={'timestamp': 'Date & Time', 'monthly_listeners': 'Monthly Listeners'})
    fig.update_layout(hovermode='x unified', legend_title='Artist')
    fig.write_html('dashboard.html')
    print("Dashboard updated!")

    # Alerts (on significant change)
    for artist, row in df_new.iterrows():
        if artist in df_history.index:
            old_row = df_history.loc[artist]
            last_count = old_row['monthly_listeners']
            new_count = row['monthly_listeners']
            if last_count > 0:
                pct_change = abs((new_count - last_count) / last_count * 100)
                abs_change = abs(new_count - last_count)
                if pct_change > CHANGE_THRESHOLD_PERCENT or abs_change > CHANGE_THRESHOLD_ABSOLUTE:
                    delta = new_count - last_count
                    msg = f"🚨 <b>Big listener change!</b>\n\n<b>{artist}</b>: {last_count:,} → {new_count:,} ({delta:+,})\n{pct_change:.1f}% at {timestamp}"
                    send_telegram(msg)
