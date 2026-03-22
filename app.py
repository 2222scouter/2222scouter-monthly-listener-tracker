import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Tracker", layout="wide", initial_sidebar_state="collapsed")

# Off-white background, hide sidebar/header
st.markdown("""
    <style>
        section[data-testid="stSidebar"] {display: none;}
        .main .block-container {padding: 1rem 1rem 0rem !important;}
        body, .stApp {background-color: #f8f9fa !important;}
        .tiny-title {
            font-size: 11px;
            color: #aaa;
            text-align: center;
            margin: 20px 0 80px 0;
            letter-spacing: 1px;
        }
        .view-link {
            font-size: 18px;
            color: #555;
            text-decoration: none;
            padding: 10px 30px;
            margin: 0 40px;
            cursor: pointer;
            transition: color 0.2s;
        }
        .view-link:hover {color: #000;}
        .back-link {
            font-size: 13px;
            color: #888;
            text-decoration: none;
            position: absolute;
            top: 15px;
            left: 20px;
        }
        .back-link:hover {color: #333;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="tiny-title">2222scouter tracker</div>', unsafe_allow_html=True)

# Load data
@st.cache_data(ttl=300)
def load_data():
    url = "https://raw.githubusercontent.com/2222scouter/2222scouter-monthly-listener-tracker/main/spotify_listeners_history.csv"
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Replace NaN/None with 0 for gain columns
        gain_cols = [c for c in df.columns if 'change_' in c or 'pct_' in c]
        df[gain_cols] = df[gain_cols].fillna(0)
        return df
    except:
        return pd.DataFrame(columns=['timestamp', 'artist', 'monthly_listeners'])

df = load_data()

# Session state
if 'view' not in st.session_state:
    st.session_state.view = None

# Initial screen: small words
if st.session_state.view is None:
    st.markdown("""
        <div style="text-align: center; margin-top: 200px;">
            <a class="view-link" href="#" onclick="document.getElementById('graph_btn').click();">graph</a>
            <a class="view-link" href="#" onclick="document.getElementById('table_btn').click();">table</a>
        </div>
    """, unsafe_allow_html=True)

    if st.button("graph", key="graph_btn"):
        st.session_state.view = "graph"
        st.rerun()
    if st.button("table", key="table_btn"):
        st.session_state.view = "table"
        st.rerun()

# Graph view
elif st.session_state.view == "graph":
    st.markdown('<a class="back-link" href="#" onclick="history.back()">back</a>', unsafe_allow_html=True)
    if df.empty or len(df) == 0:
        st.text("no data yet")
    else:
        fig = px.line(df, x='timestamp', y='monthly_listeners', color='artist',
                      markers=True)
        fig.update_layout(showlegend=False, margin=dict(l=0,r=0,t=0,b=0), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# Table view - always show, 0 for missing gains
elif st.session_state.view == "table":
    st.markdown('<a class="back-link" href="#" onclick="history.back()">back</a>', unsafe_allow_html=True)
    if df.empty:
        st.text("no data yet")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "timestamp": "time",
                "artist": "artist",
                "monthly_listeners": "listeners",
                "change_since_yesterday": "change yesterday",
                "pct_since_yesterday": "pct yesterday",
                "change_day1_to_day2": "change day1→day2",
                "pct_day1_to_day2": "pct day1→day2",
                "change_day2_to_day3": "change day2→day3",
                "pct_day2_to_day3": "pct day2→day3",
            }
        )
