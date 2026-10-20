# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: STYLING & CONFIGURATION (PART 1 OF 4)
# ==============================================================================
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import altair as alt
from datetime import datetime, timedelta
import pytz
import sys
import warnings
sys.modules['warnings'] = warnings
import base64

# Force wide layout and high visibility font scales cleanly
st.set_page_config(
    page_title="Mike's Share Market Dashboard", 
    layout="wide"
)

TARGETS_FILE = "portfolio_targets.json"
CACHE_FILE = "portfolio_market_cache.json"

# Load data directly from local hard drive storage
disk_memory = {}
if os.path.exists(TARGETS_FILE):
    try:
        with open(TARGETS_FILE, 'r') as f:
            disk_memory = json.load(f)
    except Exception:
        pass

# Extract structured matrix sections from local JSON
runtime_positions = disk_memory.get("positions", {})
runtime_watchlist = disk_memory.get("watchlist_tickers", [])
runtime_cash = disk_memory.get("wallet_cash", {"NZD": 0.00, "AUD": 0.00, "USD": 0.00})
runtime_sliders = disk_memory.get("sliders", {"fast_ma": 10, "slow_ma": 100, "roi_window": "1 Year", "graph_horizon": "1 Year"})

# --- STRICT 6+6 SLOT STRUCTURAL ENFORCEMENT ---
# Extract existing entries, pad remaining slots out to exact boundaries
portfolio_slots = list(runtime_positions.keys())[:6]
while len(portfolio_slots) < 6:
    portfolio_slots.append(f"EMPTY_PORT_{len(portfolio_slots)+1}")

watchlist_slots = [t for t in runtime_watchlist if t.strip()][:6]
while len(watchlist_slots) < 6:
    watchlist_slots.append(f"EMPTY_WATCH_{len(watchlist_slots)+1}")

# Default state synchronization for sidebar inputs
if "fast_ma" not in st.session_state: st.session_state["fast_ma"] = int(runtime_sliders.get("fast_ma", 10))
if "slow_ma" not in st.session_state: st.session_state["slow_ma"] = int(runtime_sliders.get("slow_ma", 100))
if "roi_window" not in st.session_state: st.session_state["roi_window"] = runtime_sliders.get("roi_window", "1 Year")
if "graph_horizon" not in st.session_state: st.session_state["graph_horizon"] = runtime_sliders.get("graph_horizon", "1 Year")
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: SIDEBAR RUNTIME CONTROLS (PART 2 OF 4)
# ==============================================================================
import requests

def push_targets_to_github(updated_data):
    # Pull credentials securely from local or cloud secrets memory
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")

    file_path = "portfolio_targets.json"
    
    # FIX: Direct connection to the official GitHub API endpoint instead of web URL
    clean_repo = repo.strip("/")
    url = f"https://api.github.com/repos/{clean_repo}/contents/{file_path}"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Fetch current file SHA hash to prevent overwrite conflicts
    try:
        response = requests.get(url, headers=headers)
        sha = None
        if response.status_code == 200:
            sha = response.json().get("sha")
        elif response.status_code != 404:
            print(f"\n[DEBUG GITHUB] GET SHA failed. Status code: {response.status_code}")
            print(f"[RAW ERROR RESPONSE] {response.text}\n")
            return False
    except Exception as e:
        print(f"\n[CRITICAL GITHUB] GET SHA Exception: {str(e)}\n")
        return False

    # Format JSON structure cleanly matching your layout matrix
    json_string = json.dumps(updated_data, indent=4)
    encoded_content = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")

    payload = {
        "message": "🔄 Automated portfolio boundary update via Cloud Dashboard",
        "content": encoded_content,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    try:
        put_response = requests.put(url, headers=headers, json=payload)
        # FIX: Clean comparison operators to completely bypass the prior syntax error
        if put_response.status_code == 200 or put_response.status_code == 201:
            return True
        else:
            # Prints the exact authentication or authorization error directly to your terminal
            print(f"\n[CRITICAL REJECTION] GitHub Server Response Code: {put_response.status_code}")
            print(f"[RAW JSON ERROR] Message payload: {put_response.text}\n")
            return False
    except Exception as e:
        print(f"\n[CRITICAL CONNECTION FAILURE] Error details: {str(e)}\n")
        return False
with st.sidebar:
    st.markdown("### 🛠️ Configuration Controls")
    
    # Clean high-speed cache reset engine anchored at the top
    if st.button("🔄 Clear App Cache Memory", use_container_width=True):
        if os.path.exists(CACHE_FILE):
            try: os.remove(CACHE_FILE)
            except: pass
        st.cache_data.clear()
        st.rerun()

    @st.fragment
    def render_isolated_sidebar_controls():
        # NOTICE: The legacy manual save button block and bulky banners have been cleanly scrubbed from here!
        st.selectbox("Chart & ROI grid timeframe", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], key="roi_window")
        st.selectbox("Fast MA Frame", [5, 10, 20, 50], index=[5, 10, 20, 50].index(st.session_state["fast_ma"]) if st.session_state["fast_ma"] in [5, 10, 20, 50] else 1, key="fast_ma")
        st.selectbox("Slow MA Frame", [25, 50, 100, 200], index=[25, 50, 100, 200].index(st.session_state["slow_ma"]) if st.session_state["slow_ma"] in [25, 50, 100, 200] else 2, key="slow_ma")
        
        st.markdown("---")
        st.markdown("### 💼 Sharesies Wallet Cash")
        st.number_input("Cash Held (NZD)", min_value=0.00, value=float(runtime_cash.get("NZD", 0.00)), step=1.00, format="%.2f", key="cash_nzd_input")
        st.number_input("Cash Held (AUD)", min_value=0.00, value=float(runtime_cash.get("AUD", 0.00)), step=1.00, format="%.2f", key="cash_aud_input")
        st.number_input("Cash Held (USD)", min_value=0.00, value=float(runtime_cash.get("USD", 0.00)), step=1.00, format="%.2f", key="cash_usd_input")
        
        st.markdown("---")
        st.markdown("### 📐 Layer A: Fixed Portfolio Slots")
        for i in range(6):
            ticker = portfolio_slots[i]
            stored = runtime_positions.get(ticker, {}) if "EMPTY" not in ticker else {}
            display_label = ticker if "EMPTY" not in ticker else "Empty Slot"
            with st.expander(f"Slot {i+1}: {display_label}", expanded=False):
                st.text_input(f"Ticker Symbol", value="" if "EMPTY" in ticker else ticker, key=f"port_slot_{i}")
                st.number_input("Number of Shares", min_value=0.0000, value=float(stored.get("shares", 0.0)), step=0.0001, format="%.4f", key=f"shares_{i}")
                st.number_input("My Entry Price ($)", min_value=0.0, value=float(stored.get("entry", 0.0)), key=f"entry_{i}")
                st.number_input("Upper Target ($)", min_value=0.0, value=float(stored.get("upper", 0.0)), key=f"up_{i}")
                st.number_input("Fixed Stop Distance ($)", min_value=0.0, value=float(stored.get("fixed_stop_distance", 15.0)), key=f"fixed_stop_{i}")

        st.markdown("---")
        st.markdown("### 🛰️ Layer B: Watchlist Tickers (Symbols Only)")
        for i in range(6):
            ticker = watchlist_slots[i]
            val_to_show = "" if "EMPTY" in ticker else ticker
            st.text_input(f"Watchlist Slot {i+1}", value=val_to_show, key=f"watch_slot_{i}")

    render_isolated_sidebar_controls()

selected_timeframe = st.session_state["roi_window"]
chart_timeframe_choice = st.session_state["roi_window"] # Both systems now look at the same master switch!
fast_ma_input = st.session_state["fast_ma"]
slow_ma_input = st.session_state["slow_ma"]
cash_nzd = float(st.session_state.get("cash_nzd_input", runtime_cash.get("NZD", 0.00)))
cash_aud = float(st.session_state.get("cash_aud_input", runtime_cash.get("AUD", 0.00)))
cash_usd = float(st.session_state.get("cash_usd_input", runtime_cash.get("USD", 0.00)))
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: FX ENGINE & DATA BATCHING (PART 3A)
# ==============================================================================
def get_exchange_status_badge(tz_name, open_hour=9, open_min=30, close_hour=16, close_min=0, is_nz_au=False):
    if is_nz_au: open_hour, open_min = 10, 0
    try:
        target_tz = pytz.timezone(tz_name)
        tz_now = datetime.now(target_tz)
        if tz_now.weekday() >= 5: return "<span style='color: #dc3545; font-weight: bold;'>🔴 CLOSED</span>"
        start_time = tz_now.replace(hour=open_hour, minute=open_min, second=0, microsecond=0)
        end_time = tz_now.replace(hour=close_hour, minute=close_min, second=0, microsecond=0)
        if start_time <= tz_now <= end_time: return "<span style='color: #28a745; font-weight: bold;'>🟢 OPEN</span>"
        return "<span style='color: #dc3545; font-weight: bold;'>🔴 CLOSED</span>"
    except: return "N/A"

from zoneinfo import ZoneInfo
us_status = get_exchange_status_badge('America/New_York')
au_status = get_exchange_status_badge('Australia/Sydney', is_nz_au=True)
nz_status = get_exchange_status_badge('Pacific/Auckland', is_nz_au=True)

# Format the current local clock for your high-visibility status banner
nz_now_time = datetime.now(ZoneInfo("Pacific/Auckland")).strftime("%d %b %Y, %I:%M %p %Z")

st.markdown(f"""
    <div style='background-color: #161A22; padding: 6px 12px; border-radius: 4px; display: flex; justify-content: center; gap: 40px; font-size: 1.1rem; font-weight: bold; margin-bottom: 15px; border: 1px solid #2d3139;'>
        <span style='color: #FFFFFF;'>🇺🇸 NYSE US: {us_status}</span>
        <span style='color: #FFFFFF;'>🇦🇺 ASX AUS: {au_status}</span>
        <span style='color: #FFFFFF;'>🇳🇿 NZX NZ: {nz_status}</span>
        </div>
    <div style='text-align: center; font-size: 0.9rem; color: #8B949E; margin-bottom: 15px;'>
        🕒 Your Trading Desk Local Time: <strong>{nz_now_time}</strong>
        </div>
       """, unsafe_allow_html=True)

# SURGICAL ADDITION: STICKY FLOATING WORKSPACE CONTROL BAR (SCROLL-RESISTANT)
# ==============================================================================
# Inject the CSS to pin this container to the top view screen and forcefully align inner text blocks
st.markdown("""
    <style>
        /* 1. Force the target container block to stick to the absolute top viewport ceiling without blocking navigation buttons */
        div[data-testid="stVerticalBlock"] > div:has(div.floating-action-toolbar) {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: calc(100% - 20px) !important; 
            z-index: 99 !important; /* UPGRADE: Lowered to allow the sidebar navigation toggle to float cleanly on top */
            background-color: #0E1117 !important; 
            padding: 8px 40px !important;
            border-bottom: 1px solid #30363D !important;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.5) !important;
        }
        
        /* 2. FORCE PERFECT VERTICAL CENTER AXIS VIA DIRECT INNER PARAGRAPH OVERRIDES */
        div:has(div.floating-action-toolbar) button p {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.0 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        /* 3. Push the standard content layout down a fraction so it isn't hidden under our bar */
        div[data-testid="stAppViewBlockContainer"] {
            padding-top: 5.2rem !important;
        }

        /* 4. HIGH-DENSITY CRUNCH: Force compact vertical spacing inside Streamlit inputs and expanders */
        div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
            padding-top: 1px !important;
            padding-bottom: 1px !important;
            margin-top: 0px !important;
            margin-bottom: 0px !important;
        }
        div[data-testid="stSidebar"] .stNumberInput, div[data-testid="stSidebar"] .stTextInput, div[data-testid="stSidebar"] .stSelectbox {
            margin-bottom: 2px !important;
        }
        div[data-testid="stSidebar"] [data-testid="stExpander"] {
            margin-bottom: 2px !important;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🌟 UNBREAKABLE ARCHITECTURE: PRODUCTION STICKY DASHBOARD HEADER Row
# ==============================================================================
last_save_time = st.session_state.get("last_cloud_save_time", None)

if last_save_time:
    if "⚠️" in last_save_time:
        status_html = f"<div style='background-color: #dc3545; color: #FFFFFF; padding: 8px 12px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 0.85rem; border: 1px solid #bd2130; height: 38px; display: flex; align-items: center; justify-content: center; box-sizing: border-box;'>{last_save_time}</div>"
    else:
        status_html = f"<div style='background-color: #28a745; color: #FFFFFF; padding: 4px 12px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 0.82rem; border: 1px solid #1e7e34; line-height: 1.2; height: 38px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-sizing: border-box;'>✅ SYNCED TO GITHUB LIVE<span style='font-size: 0.70rem; font-weight: normal; opacity: 0.85; margin-top: 1px;'>Time: {last_save_time}</span></div>"
else:
    status_html = "<div style='background-color: #1C212A; color: #8B949E; padding: 10px 12px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 0.85rem; border: 1px solid #30363D; height: 38px; display: flex; align-items: center; justify-content: center; box-sizing: border-box;'>📁 Database Standby: Connected</div>"

# Inject precision styling targeting ONLY the immediate container wrapper block
# Inject precision styling targeting ONLY the immediate container wrapper block
# Inject precision styling targeting ONLY the immediate container wrapper block
st.markdown("""
    <style>
        /* 1. Target the vertical container block that contains our unique element marker */
        div[data-testid="stVerticalBlock"] > div:has(span#mike-sticky-marker) {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            z-index: 999991 !important;
            background-color: #0E1117 !important;
            padding: 12px 40px !important; /* Balanced padding that ensures visibility */
            border-bottom: 1px solid #30363D !important;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.5) !important;
            box-sizing: border-box !important;
        }

        /* 2. Handle simple flex layout mapping across the row grid */
        div[data-testid="stVerticalBlock"] > div:has(span#mike-sticky-marker) div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            align-items: center !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            gap: 1rem !important;
        }

        /* 3. PRECISION ALIGNMENT: Nudge button downward to match the text center line */
        div[data-testid="stVerticalBlock"] > div:has(span#mike-sticky-marker) .stButton {
            margin: 0 !important;
            padding: 0 !important;
            position: relative !important;
            top: 3px !important; /* Moves the button down perfectly into the center axis */
        }
        
        div[data-testid="stVerticalBlock"] > div:has(span#mike-sticky-marker) .stButton > button {
            height: 38px !important;
            font-size: 0.85rem !important;
            font-weight: bold !important;
            text-transform: uppercase !important;
            margin: 0 !important;
        }

        /* 4. Keep standard page data columns shifted down away from under the ceiling bar */
        div[data-testid="stAppViewBlockContainer"] {
            padding-top: 6.5rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Create an isolated container row acting as our floating dashboard window ceiling anchors
with st.container():
    # Inject a distinct hidden inline anchor marker to map our CSS positioning targets safely
    st.markdown('<span id="mike-sticky-marker" style="display:none;"></span>', unsafe_allow_html=True)
    
    head_col1, head_col2, head_col3 = st.columns([2, 1.5, 1.2])
    
    with head_col1:
        st.markdown("<h3 style='margin: 0; padding: 0; font-size: 1.30rem; color: #4A90E2; line-height: 1.2;'>⚡ Live Matrix Workspace Viewport Ledger</h3>", unsafe_allow_html=True)
        
    with head_col2:
        st.markdown(status_html, unsafe_allow_html=True)
        
    with head_col3:
        trigger_sync_active = st.button("💾 SAVE & SYNC WORKSPACE", use_container_width=True, type="primary")

if trigger_sync_active:
    live_sidebar_bounds = {
        "wallet_cash": {
            "NZD": float(st.session_state.get("cash_nzd_input", runtime_cash.get("NZD", 0.00))),
            "AUD": float(st.session_state.get("cash_aud_input", runtime_cash.get("AUD", 0.00))),
            "USD": float(st.session_state.get("cash_usd_input", runtime_cash.get("USD", 0.00))),
        },
        "sliders": {
            "fast_ma": int(st.session_state.get("fast_ma", 10)),
            "slow_ma": int(st.session_state.get("slow_ma", 100)),
            "roi_window": st.session_state.get("roi_window", "1 Year"),
            "graph_horizon": st.session_state.get("roi_window", "1 Year")
        },
        "positions": {},
        "watchlist_tickers": []
    }
    
    for idx in range(6):
        t_input = st.session_state.get(f"port_slot_{idx}", portfolio_slots[idx]).upper().strip()
        if t_input and "EMPTY" not in t_input:
            live_sidebar_bounds["positions"][t_input] = {
                "shares": float(st.session_state.get(f"shares_{idx}", 0.0000)),
                "entry": float(st.session_state.get(f"entry_{idx}", 0.00)),
                "upper": float(st.session_state.get(f"up_{idx}", 0.00)),
                "fixed_stop_distance": float(st.session_state.get(f"fixed_stop_{idx}", 15.00))
            }
    
    for idx in range(6):
        w_input = st.session_state.get(f"watch_slot_{idx}", watchlist_slots[idx]).upper().strip()
        if w_input and "EMPTY" not in w_input:
            live_sidebar_bounds["watchlist_tickers"].append(w_input)
    
    with open(TARGETS_FILE, 'w') as f:
        json.dump(live_sidebar_bounds, f, indent=4)
    
    synced_ok = push_targets_to_github(live_sidebar_bounds)
    
    if synced_ok:
        from zoneinfo import ZoneInfo
        nz_tz = ZoneInfo("Pacific/Auckland")
        st.session_state["last_cloud_save_time"] = datetime.now(nz_tz).strftime("%I:%M:%S %p %Z")
        st.toast("Matrix parameters committed and synced successfully!")
    else:
        st.session_state["last_cloud_save_time"] = "⚠️ Connection Refused by GitHub"
        
    st.cache_data.clear()
    st.rerun()

st.markdown("---")

def get_live_fx_rates():
    nzd_rate, aud_rate = 1.6500, 1.1000  
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                c_data = json.load(f)
                for k, v in c_data.items():
                    if "NZD=X" in k and v:
                        timestamps = sorted(list(v.keys()))
                        if timestamps:
                            raw_usd_nzd = float(v[timestamps[-1]])
                            if 0 < raw_usd_nzd < 1.0: nzd_rate = float(1.0 / raw_usd_nzd)
                            elif raw_usd_nzd >= 1.0: nzd_rate = raw_usd_nzd
                    if "AUDNZD=X" in k and v:
                        timestamps = sorted(list(v.keys()))
                        if timestamps: aud_rate = float(v[timestamps[-1]])
        except Exception: pass
    try:
        if nzd_rate == 1.6500:
            raw_usd_nzd = float(yf.Ticker("NZD=X").history(period="1d")['Close'].dropna().iloc[-1])
            if 0 < raw_usd_nzd < 1.0: nzd_rate = float(1.0 / raw_usd_nzd)
            elif raw_usd_nzd >= 1.0: nzd_rate = raw_usd_nzd
        if aud_rate == 1.1000:
            raw_aud_nzd = float(yf.Ticker("AUDNZD=X").history(period="1d")['Close'].dropna().iloc[-1])
            if raw_aud_nzd > 0: aud_rate = float(raw_aud_nzd)
    except Exception: pass 
    return nzd_rate, aud_rate

usd_to_nzd_rate, aud_to_nzd_rate = get_live_fx_rates()
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: DATA BATCHING & INDICATORS (PART 3B - HALF 1)
# ==============================================================================
def fetch_all_market_data_batch(ticker_list, start_date):
    if os.path.exists(CACHE_FILE):
        try:
            df_cached = pd.read_json(CACHE_FILE)
            df_cached.index = pd.to_datetime(df_cached.index)
            df_cached.columns = pd.MultiIndex.from_tuples([eval(col) if isinstance(col, str) and col.startswith("(") else (col, "Close") for col in df_cached.columns])
            st.sidebar.success("✅ Connected via Local Cache Storage")
            return df_cached
        except Exception: pass
    try:
        valid_tickers = [t for t in ticker_list if t and "EMPTY" not in t]
        if valid_tickers:
            df_live = yf.download(valid_tickers, start=start_date, progress=False)
            if not df_live.empty:
                df_live = df_live.swaplevel(0, 1, axis=1)
                df_live = df_live.sort_index(axis=1, level=0)
                return df_live
    except Exception: pass
    return pd.DataFrame()

def extract_ticker_dataframe(df_all, ticker):
    try:
        if df_all.empty or ticker not in df_all.columns.get_level_values(0):
            return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        df = df_all[ticker].copy()
        df.columns = [str(c).title() for c in df.columns]
        return df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    except: return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

def calculate_indicators_only(df, fast_ma, slow_ma):
    df = df.copy()
    if df.empty or len(df) < 5: return df
    actual_fast, actual_slow, actual_atr = min(int(fast_ma), len(df)), min(int(slow_ma), len(df)), min(14, len(df))
    close_series, high_series, low_series = df['Close'].astype(float), df['High'].astype(float), df['Low'].astype(float)
    
    df['Fast_MA'] = close_series.rolling(window=actual_fast, min_periods=1).mean()
    df['Slow_MA'] = close_series.rolling(window=actual_slow, min_periods=1).mean()
    
    tr1 = high_series - low_series
    tr2, tr3 = (high_series - close_series.shift(1)).abs(), (low_series - close_series.shift(1)).abs()
    df['True_Range'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = df['True_Range'].rolling(window=actual_atr, min_periods=1).mean()
    
    delta = close_series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=actual_atr, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=actual_atr, min_periods=1).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)))).fillna(50)
    df['MACD'] = close_series.ewm(span=min(12, len(df)), adjust=False).mean() - close_series.ewm(span=min(26, len(df)), adjust=False).mean()
    df['Signal_Line'] = df['MACD'].ewm(span=min(9, len(df)), adjust=False).mean()
    return df
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: TICKER PROCESSING LOOPS (PART 3B - HALF 2)
# ==============================================================================
def apply_market_signal_theme(df):
    def style_metric_cells(row):
        styles = [''] * len(row)
        if 'Alert status' in row.index:
            val = row['Alert status']
            idx = row.index.get_loc('Alert status')
            if val == "🌟 STRONG BUY": styles[idx] = 'background-color: #007bff; color: #ffffff; font-weight: bold;'
            elif val == "🟩 BULLISH LONG": styles[idx] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == "🟨 MOMENTUM WARNING": styles[idx] = 'background-color: #ffe8a1; color: #856404; font-weight: bold;'
            elif val == "⬜ CASH FLAT": styles[idx] = 'background-color: #f8f9fa; color: #6c757d;'
        return styles
    return df.style.apply(style_metric_cells, axis=1)

# --- WORKSPACE RESOLUTION & UNIFICATION ---
master_unified_rows, active_live_positions, operational_dfs = [], [], {}
lookback_days_map = {"1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365, "2 Years": 730}
# Force the data download window to always use 2 Years so the chart engine never starves
lookback_start_date = datetime.now() - timedelta(days=lookback_days_map["2 Years"] + 250)
macro_sector_rows = []
sector_mapping_dictionary = {"SPY": "🇺🇸 S&P 500 Index", "XLK": "💻 Technology", "XLY": "📦 Consumer Discretionary", "XLC": "🗣️ Communication", "XLF": "🏦 Financials", "XLV": "🩺 Healthcare", "XLP": "🛒 Consumer Staples", "XLI": "🏗️ Industrials", "XLE": "🛢️ Energy", "XLB": "🧱 Materials", "XLU": "⚡ Utilities", "XLRE": "🏢 Real Estate"}

clean_portfolio_list = [t for t in portfolio_slots if t and "EMPTY" not in t]
clean_watchlist_list = [t for t in watchlist_slots if t and "EMPTY" not in t]

# STRICT PERSISTENT SEQUENCE ORDER ENFORCEMENT
all_active_workspace_tickers = []
# 1. Loop through clean portfolio items first to preserve active workspace slots
for t in clean_portfolio_list:
    if t not in all_active_workspace_tickers:
        all_active_workspace_tickers.append(t)
# 2. Append secondary watchlist rows next without duplicating elements
for t in clean_watchlist_list:
    if t not in all_active_workspace_tickers:
        all_active_workspace_tickers.append(t)

extended_fetching_tickers = list(set(all_active_workspace_tickers + list(sector_mapping_dictionary.keys())))
RAW_MARKET_BATCH = fetch_all_market_data_batch(extended_fetching_tickers, lookback_start_date)

asset_sector_tags = {
    "AAPL": "XLK", "NVDA": "XLK", "TEAM": "XLK", "ARM": "XLK", "INTC": "XLK", "AMD": "XLK", "SMCI": "XLK",
    "JPM": "XLF", "BAC": "XLF", "GS": "XLF", "COIN": "XLF", "MSTR": "XLF", "CRWD": "XLK",
    "XLE": "XLE", "SPY": "SPY", "QQQ": "QQQ", "DUK": "XLU", "NEM": "XLB", "PLD": "XLRE", "LIN": "XLB"
}

roi_cutoff_date = datetime.now() - timedelta(days=lookback_days_map[selected_timeframe])

for sector_symbol, descriptive_name in sector_mapping_dictionary.items():
    s_hist = extract_ticker_dataframe(RAW_MARKET_BATCH, sector_symbol)
    if not s_hist.empty and len(s_hist) >= 5:
        # SLICE FIX: Filter sector data index to match the ROI timeframe
        localized_s_cutoff = roi_cutoff_date.tz_localize(s_hist.index.tz) if s_hist.index.tz else roi_cutoff_date
        s_hist_sliced = s_hist[s_hist.index >= localized_s_cutoff]
        if s_hist_sliced.empty or len(s_hist_sliced) < 5: s_hist_sliced = s_hist
        
        s_calc = calculate_indicators_only(s_hist_sliced, fast_ma_input, slow_ma_input)
        s_close = float(s_calc['Close'].iloc[-1])
        s_rsi = float(s_calc['RSI'].iloc[-1]) if 'RSI' in s_calc.columns else 50.0
        rsi_label = f"{s_rsi:.1f} 🔴 OVERBOUGHT" if s_rsi >= 70.0 else (f"{s_rsi:.1f} 🟢 OVERSOLD" if s_rsi <= 30.0 else f"{s_rsi:.1f} ⚪ Healthy")
        macro_sector_rows.append({"Sector Symbol": sector_symbol, "Sector Domain Name": descriptive_name, "Closing Price": s_close, "RSI Status Value": s_rsi, "RSI Speedometer": rsi_label})

local_name_map = {
    "AAPL": "Apple Inc.", "AMD": "Advanced Micro Devices", "CRWD": "CrowdStrike Holdings", "NVDA": "NVIDIA Corp",
    "BAC": "Bank of America", "GS": "Goldman Sachs", "JPM": "JPMorgan Chase", "LIN": "Linde plc", "NEM": "Newmont Corp",
    "DUK": "Duke Energy", "PLD": "Prologis Inc", "QQQ": "Nasdaq 100 ETF", "SPY": "S&P 500 ETF", "XLE": "Energy Select ETF"
}

# Create a cutoff timestamp based on your sidebar's active ROI window choice
roi_cutoff_date = datetime.now() - timedelta(days=lookback_days_map[selected_timeframe])

for ticker in all_active_workspace_tickers:
    hist_df = extract_ticker_dataframe(RAW_MARKET_BATCH, ticker)
    if hist_df.empty or len(hist_df) < 5: continue
    
    # UPGRADE FIX: Run technical indicators on the full dataset so the engine never starves!
    df_calc = calculate_indicators_only(hist_df, fast_ma_input, slow_ma_input)
    operational_dfs[ticker] = df_calc
    
    # Create the short timeframe slice strictly for frontend ROI display calculations
    localized_cutoff = roi_cutoff_date.tz_localize(df_calc.index.tz) if df_calc.index.tz else roi_cutoff_date
    hist_df_sliced = df_calc[df_calc.index >= localized_cutoff]
    if hist_df_sliced.empty or len(hist_df_sliced) < 2:
        hist_df_sliced = df_calc

        # Check your custom overrides first, then cross-reference yfinance metadata, defaulting to the raw symbol if empty
    resolved_name = disk_memory.get("local_name_map", {}).get(ticker, local_name_map.get(ticker, None))
    if not resolved_name:
        try:
            # Safely pulls the live registration identity recorded on Yahoo Finance
            resolved_name = yf.Ticker(ticker).info.get('longName', f"{ticker}")
        except Exception:
            resolved_name = f"{ticker}"
    last_close = float(df_calc['Close'].iloc[-1])
    fast_ma_val = float(df_calc['Fast_MA'].iloc[-1]) if 'Fast_MA' in df_calc.columns else last_close
    slow_ma_val = float(df_calc['Slow_MA'].iloc[-1]) if 'Slow_MA' in df_calc.columns else last_close
    rsi_val = float(df_calc['RSI'].iloc[-1]) if 'RSI' in df_calc.columns else 50.0
    macd_val = float(df_calc['MACD'].iloc[-1]) if 'MACD' in df_calc.columns else 0.0
    sig_val = float(df_calc['Signal_Line'].iloc[-1]) if 'Signal_Line' in df_calc.columns else 0.0
    atr_val = float(df_calc['ATR'].iloc[-1]) if 'ATR' in df_calc.columns else 1.0
    
    # --- CALCULATE VOLATILITY-ADJUSTED ENTRY AND EXIT TRAILING LIMITS ---
    safe_daily_limit_target = round(last_close - (1.0 * atr_val), 2)
    safe_take_profit_target = round((last_close + (2.0 * atr_val)) * 1.012, 2)
    
    # --- CALCULATE TRUE TIMEFRAME PERFORMANCE ROI ---
    if not hist_df_sliced.empty and len(hist_df_sliced) >= 2:
        window_start_price = float(hist_df_sliced['Close'].dropna().iloc[0])
        ticker_timeframe_roi = ((last_close - window_start_price) / window_start_price) * 100
    else:
        ticker_timeframe_roi = 0.0

    # --- 4-TIER VOLUME-VERIFIED STATUS ENGINE ---
    try:
        current_price = float(last_close)
        f_ma = float(fast_ma_val)
        s_ma = float(slow_ma_val)
        if not df_calc.empty and 'Volume' in df_calc.columns and len(df_calc) >= 20:
            vol_twenty_avg = df_calc['Volume'].rolling(window=20).mean().iloc[-1]
            v_surge = float(df_calc['Volume'].iloc[-1] / vol_twenty_avg) if vol_twenty_avg > 0 else 1.0
        else:
            v_surge = 1.0
    except (ValueError, TypeError):
        current_price, f_ma, s_ma, v_surge = last_close, fast_ma_val, slow_ma_val, 1.0

    if current_price > f_ma and current_price > s_ma:
        strategy_status = "🌟 STRONG BUY" if v_surge >= 1.5 else "🟡 Bullish Turning (Low Volume)"
    elif current_price > f_ma and current_price <= s_ma:
        strategy_status = "🟢 Bullish Turning (High Volume)" if v_surge >= 1.5 else "🟡 Bullish Turning (Low Volume)"
    elif current_price <= f_ma and current_price > s_ma:
        strategy_status = "🟡 Bullish Turning (Low Volume)"
    else:
        strategy_status = "🔴 Structural Bear"
    
    assigned_sector = asset_sector_tags.get(ticker, "Other")
    
    # Append to Master Comparison Grid
    master_unified_rows.append({
        "Ticker": ticker, "Sector": assigned_sector, "Company Name": resolved_name, 
        "Closing": last_close, "Limit Entry Target": safe_daily_limit_target, 
        "Take Profit Target": safe_take_profit_target, 
        "Timeframe ROI %": ticker_timeframe_roi, 
        "Alert status": strategy_status, "Fast MA": fast_ma_val, 
        "Slow MA": slow_ma_val, "RSI": rsi_val, "ATR": atr_val
    })
    
    # Append to Active Portfolio Grid if owned
    if ticker in clean_portfolio_list:
        stored_block = runtime_positions.get(ticker, {})
        custom_saved_shares = float(stored_block.get("shares", 0.0))
        entry_p = float(stored_block.get("entry", 0.0))
        if custom_saved_shares > 0.0:
            implied_investment_local = custom_saved_shares * entry_p
            hist_365 = df_calc[df_calc.index >= pd.to_datetime(datetime.now() - timedelta(days=365)).tz_localize(df_calc.index.tz)] if not df_calc.empty else df_calc
            true_52w_high = float(hist_365['High'].max()) if not hist_365.empty else last_close
            
            is_us_asset = not (ticker.endswith(".NZ") or ticker.endswith(".AX"))
            native_currency_label = "USD" if is_us_asset else ("AUD" if ticker.endswith(".AX") else "NZD")
            currency_multiplier = usd_to_nzd_rate if native_currency_label == "USD" else (aud_to_nzd_rate if native_currency_label == "AUD" else 1.0)

            calculated_trailing_floor = true_52w_high - (2.0 * atr_val)
            if calculated_trailing_floor < (entry_p - (2.0 * atr_val)): calculated_trailing_floor = entry_p - (2.0 * atr_val)
            if calculated_trailing_floor >= last_close: calculated_trailing_floor = last_close - (2.0 * atr_val)
            
            current_value_local = custom_saved_shares * last_close
            active_live_positions.append({
                "Ticker": ticker, 
                "Company Name": resolved_name,
                "Shares": custom_saved_shares, 
                "Currency": native_currency_label,
                "My Entry Price": entry_p, 
                "Live Market Price": last_close, 
                "Daily Pullback Limit": safe_daily_limit_target,   
                "Take-Profit Target": safe_take_profit_target,    
                "Investment (Local)": implied_investment_local,
                "Investment (NZD)": implied_investment_local * currency_multiplier, 
                "Current Value (Local)": current_value_local,
                "Current Value (NZD)": current_value_local * currency_multiplier, 
                "Trailing Floor": calculated_trailing_floor
            })

# ==============================================================================
st.markdown("#### 💼 Layer A: My Portfolio Ledger")
if active_live_positions:
    p_df = pd.DataFrame(active_live_positions)
    p_df["Net Profit (NZD)"] = p_df["Current Value (NZD)"] - p_df["Investment (NZD)"]
    p_df["Live ROI"] = (p_df["Net Profit (NZD)"] / p_df["Investment (NZD)"]) * 100
    
    database_names = disk_memory.get("local_name_map", {})
    # Check your local targets first, then your hardcoded map, and fall back cleanly to just the raw ticker symbol
    
    cols_layer_a = [
        "Ticker", "Company Name", "Shares", "Currency", "My Entry Price", 
        "Live Market Price", "Daily Pullback Limit", "Take-Profit Target",
        "Investment (Local)", "Investment (NZD)", "Current Value (Local)", 
        "Current Value (NZD)", "Trailing Floor", "Net Profit (NZD)", "Live ROI"
    ]
    p_df = p_df[[c for c in cols_layer_a if c in p_df.columns]]
    
    st.dataframe(
        p_df, use_container_width="stretch", hide_index=True, height=200,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Company Name": st.column_config.TextColumn("Asset Name", width="small"),
            "Shares": st.column_config.NumberColumn("Shares", format="%.2f", width="small"),
            "Currency": st.column_config.TextColumn("CCY", width="small"),
            "My Entry Price": st.column_config.NumberColumn("Entry", format="$%.2f", width="small"),
            "Live Market Price": st.column_config.NumberColumn("Live", format="$%.2f", width="small"),
            "Daily Pullback Limit": st.column_config.NumberColumn("Pull Limit", format="$%.2f", width="small"),
            "Take-Profit Target": st.column_config.NumberColumn("T/P Exit", format="$%.2f", width="small"),
            "Investment (Local)": st.column_config.NumberColumn("Cost (Loc)", format="$%.2f", width="small"),
            "Investment (NZD)": st.column_config.NumberColumn("Cost (NZD)", format="$%.2f", width="small"),
            "Current Value (Local)": st.column_config.NumberColumn("Val (Loc)", format="$%.2f", width="small"),
            "Current Value (NZD)": st.column_config.NumberColumn("Val (NZD)", format="$%.2f", width="small"),
            "Trailing Floor": st.column_config.NumberColumn("ATR Floor", format="$%.2f", width="small"),
            "Net Profit (NZD)": st.column_config.NumberColumn("P&L (NZD)", format="$%.2f", width="small"),
            "Live ROI": st.column_config.NumberColumn("ROI", format="%.2f%%", width="small")
        }
    )

    total_investment_nzd, total_equity_nzd = p_df["Investment (NZD)"].sum(), p_df["Current Value (NZD)"].sum()
    total_equity_profit_nzd = total_equity_nzd - total_investment_nzd
    total_roi_nzd = (total_equity_profit_nzd / total_investment_nzd) * 100 if total_investment_nzd > 0 else 0.0
    integrated_cash_nzd = cash_nzd + (cash_aud * aud_to_nzd_rate) + (cash_usd * usd_to_nzd_rate)
    total_app_value = total_equity_nzd + integrated_cash_nzd
    pnl_color, pnl_sign = ("#28a745", "+") if total_equity_profit_nzd >= 0 else ("#dc3545", "")
    st.markdown(f"""<div style='background-color: #f8f9fa; padding: 10px 14px; border-radius: 4px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; font-size: 0.88rem; font-weight: bold; margin-bottom: 20px; border: 1px solid #e9ecef;'><div>🌎 FX: <span style='color: #007bff;'>US/NZD: {usd_to_nzd_rate:.4f}</span></div><div>📋 Invested: <span style='color: #333333;'>${total_investment_nzd:,.2f} NZD</span></div><div>💰 Cash: <span style='color: #007bff;'>${integrated_cash_nzd:,.2f} NZD</span></div><div style='background-color: #eef1f6;'>👑 TOTAL VALUE:<br><span style='color: #111111; font-size: 1.15rem;'>${total_app_value:,.2f} NZD</span></div><div>📈 Return: <span style='color: {pnl_color};'>{pnl_sign}${total_equity_profit_nzd:,.2f} ({pnl_sign}{total_roi_nzd:.2f}%)</span></div></div>""", unsafe_allow_html=True)
else:
    st.info("💡 Your Portfolio Ledger is currently empty. Populate tickers in your Layer A sidebar slots to track your invested capital positions.")
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: CHART ANALYTICS (PART 4B)
# ==============================================================================
st.markdown("---")
st.markdown("#### 🔍 Core System Chart Analytics")

# Merge active portfolio and watchlist items into a clean, duplicate-free select array
owned_tickers = p_df["Ticker"].tolist() if active_live_positions else []
grid_tickers = [row["Ticker"] for row in master_unified_rows] if master_unified_rows else []
# Inherit the exact sequence from all_active_workspace_tickers instead of sorting alphabetically
unified_chart_list = [t for t in all_active_workspace_tickers if t in operational_dfs]
unified_chart_list = [t for t in unified_chart_list if t and "EMPTY" not in t]

if unified_chart_list:
    selected_portal_ticker = st.radio("🛰️ **Global Chart Engine Quick-Link Bar:**", options=unified_chart_list, horizontal=True)
    if operational_dfs and selected_portal_ticker in operational_dfs:
        full_df = operational_dfs[selected_portal_ticker]
        chart_tz = full_df.copy()
            # 1. Strip timezone cleanly if it exists, otherwise keep it as-is
    if chart_tz.index.tz is not None:
        chart_tz.index = chart_tz.index.tz_localize(None)
    
    # 2. Slice the dataframe (Un-indented so it ALWAYS runs!)
    chart_sliced = chart_tz[chart_tz.index >= (datetime.now() - timedelta(days=lookback_days_map[chart_timeframe_choice]))].copy().reset_index()

    if 'index' in chart_sliced.columns:
            chart_sliced = chart_sliced.rename(columns={'index': 'Date'})
            
    if not chart_sliced.empty and 'Fast_MA' in chart_sliced.columns:
            chart_sliced['Date'] = pd.to_datetime(chart_sliced['Date']).dt.strftime('%Y-%m-%d')
            
            last_row = chart_sliced.iloc[-1]
            current_close = float(last_row['Close'])
            current_atr = float(last_row['ATR']) if 'ATR' in last_row else 0.0
            atr_floor_value = current_close - (2.0 * current_atr)
            atr_pct_of_price = ((2.0 * current_atr) / current_close) * 100
            
            st.markdown(f"""<div style='padding: 6px 12px; background-color: #161A22; border-radius: 4px; border-left: 5px solid #FF9900; margin-bottom: 15px; font-size: 1.0rem; font-weight: bold;'>⚠️ <span style='color: #FF9900;'>{selected_portal_ticker} Safety Stops:</span> Current 2x ATR Noise Buffer is <span style='color: #FFFFFF;'>${2.0*current_atr:.2f}</span> (<span style='color: #4A90E2;'>{atr_pct_of_price:.2f}%</span> Volatility Spread). Dynamic Risk Floor sits at <span style='color: #00FF66;'>${atr_floor_value:.2f}</span>.</div>""", unsafe_allow_html=True)

            y_min, y_max = float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].min().min()), float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].max().max())
            y_min = min(y_min, atr_floor_value)
            y_scale = alt.Scale(domain=[y_min * 0.97, y_max * 1.02], clamp=True)
            
            pointer_selection = alt.selection_point(on='mousemove', nearest=True, fields=['Date'], empty='none', clear='mouseout')
            base_plot = alt.Chart(chart_sliced).encode(x=alt.X('Date:T', title=None)).properties(width='container', height=320)
            shared_tooltips = [alt.Tooltip('Date:T'), alt.Tooltip('Close:Q'), alt.Tooltip('Fast_MA:Q'), alt.Tooltip('Slow_MA:Q')]
            
            close_tr = base_plot.mark_line(color='#4A90E2', strokeWidth=3.5).encode(y=alt.Y('Close:Q', scale=y_scale), tooltip=shared_tooltips)
            fast_tr = base_plot.mark_line(color='#00FF66', strokeWidth=3.0).encode(y=alt.Y('Fast_MA:Q'))
            slow_tr = base_plot.mark_line(color='#FF3333', strokeWidth=3.0).encode(y=alt.Y('Slow_MA:Q'))
            
            atr_stop_line = alt.Chart(pd.DataFrame({'y': [atr_floor_value]})).mark_rule(color='#FF9900', strokeWidth=2.2, strokeDash=[6, 4]).encode(y='y:Q')
            hover_sensor = base_plot.mark_rule(opacity=0).add_params(pointer_selection).encode(tooltip=shared_tooltips)
            vertical_ind = base_plot.mark_rule(color='#B0BEC5', strokeWidth=1.2).encode(opacity=alt.condition(pointer_selection, alt.value(0.6), alt.value(0))).transform_filter(pointer_selection)
            
            st.altair_chart(alt.layer(close_tr, fast_tr, slow_tr, atr_stop_line, hover_sensor, vertical_ind), use_container_width=True)
else:
    st.info("💡 No assets available to plot. Add symbols to your Portfolio or Watchlist slots via the sidebar menu.")
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: COMPARISON GRIDS (PART 4C)
# ==============================================================================
st.markdown("---")
st.markdown("#### 📊 Layer B: Asset Comparison Grid")
if master_unified_rows:
    master_df = pd.DataFrame(master_unified_rows)
    
    columns_to_show = [
        "Ticker", "Sector", "Company Name", "Closing", "Timeframe ROI %", 
        "Limit Entry Target", "Take Profit Target", "Alert status", 
        "Fast MA", "Slow MA", "RSI", "ATR"
    ]
    master_df = master_df[columns_to_show]
    
    st.dataframe(
        apply_market_signal_theme(master_df), use_container_width="stretch", hide_index=True, height=200, 
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Sector": st.column_config.TextColumn("Sector", width="small"),
            "Company Name": st.column_config.TextColumn("Asset Name", width="small"),
            "Closing": st.column_config.NumberColumn("Price", format="$%.2f", width="small"), 
            "Timeframe ROI %": st.column_config.NumberColumn("Return", format="%.2f%%", width="small"),
            "Limit Entry Target": st.column_config.NumberColumn("Pull Limit", format="$%.2f", width="small"), 
            "Take Profit Target": st.column_config.NumberColumn("T/P Exit", format="$%.2f", width="small"), 
            "Alert status": st.column_config.TextColumn("Status", width="medium"),
            "Fast MA": st.column_config.NumberColumn("Fast MA", format="$%.2f", width="small"), 
            "Slow MA": st.column_config.NumberColumn("Slow MA", format="$%.2f", width="small"), 
            "RSI": st.column_config.NumberColumn("RSI", format="%.1f", width="small"),
            "ATR": st.column_config.NumberColumn("ATR", format="$%.2f", width="small")
        }
    )

# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: LAYER C POSITION CALCULATOR
# ==============================================================================
st.markdown("---")

st.markdown(
    """
    <style>
    div[data-testid="stMetricLabel"] p {
        font-size: 0.95rem !important;
        color: #475569 !important; 
        font-weight: 600 !important;
        text-transform: uppercase;
    }
    div[data-testid="stMetricValue"] div {
        font-size: 1.85rem !important; 
        font-weight: 700 !important;
        color: #0F172A !important;
    }
    .custom-funding-list {
        margin-top: 12px;
        margin-bottom: 16px;
        font-family: inherit;
    }
    .custom-funding-item {
        font-size: 1.05rem !important;
        color: #1E293B !important;
        margin-bottom: 8px;
        line-height: 1.6;
    }
    .custom-funding-highlight {
        color: #0F172A !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("#### 📐 Layer C: Volatility-Adjusted Position Sizing Calculator")

calculator_tickers = [t for t in all_active_workspace_tickers if t in operational_dfs]
calculator_tickers = [t for t in calculator_tickers if t and "EMPTY" not in t]

if calculator_tickers:
    calc_col1, calc_col2 = st.columns([1, 2])
    
    with calc_col1:
        st.markdown("<p style='font-size: 1.1rem; font-weight: bold; color: #4A90E2; margin-bottom: 2px;'>⚙️ Risk Parameters</p>", unsafe_allow_html=True)
        
        selected_calc_ticker = st.selectbox(
            "Target Execution Asset:", 
            options=calculator_tickers, 
            key="layer_c_ticker_select"
        )
        
        max_risk_nzd = st.number_input(
            "Max Account Risk Allowed (NZD $):", 
            min_value=5.00, max_value=5000.00, value=150.00, step=25.00, 
            format="%.2f", key="layer_c_max_risk_input"
        )
        
        st.markdown("---")
        st.markdown("📋 **Your Available Funding Vaults:**")
        st.markdown(f"• **NZD Wallet:** ${cash_nzd:,.2f}")
        st.markdown(f"• **AUD Wallet:** ${cash_aud:,.2f}")
        st.markdown(f"• **USD Wallet:** ${cash_usd:,.2f}")

    asset_df = operational_dfs[selected_calc_ticker]
    latest_bar = asset_df.iloc[-1]
    
    calc_close = float(latest_bar['Close'])
    calc_atr = float(latest_bar['ATR']) if 'ATR' in latest_bar else (calc_close * 0.02)
    calc_fast_ma = float(latest_bar['Fast_MA']) if 'Fast_MA' in latest_bar else calc_close
    calc_slow_ma = float(latest_bar['Slow_MA']) if 'Slow_MA' in latest_bar else calc_close
    
    is_nz = selected_calc_ticker.endswith(".NZ")
    is_au = selected_calc_ticker.endswith(".AX")
    is_us = not (is_nz or is_au)
    
    native_currency = "USD" if is_us else ("AUD" if is_au else "NZD")
    fx_multiplier = usd_to_nzd_rate if is_us else (aud_to_nzd_rate if is_au else 1.0)
    
    stop_loss_distance_native = 2.0 * calc_atr
    risk_per_share_nzd = stop_loss_distance_native * fx_multiplier
    
    computed_shares = max_risk_nzd / risk_per_share_nzd if risk_per_share_nzd > 0 else 0.0
    total_capital_required_native = computed_shares * calc_close
    total_capital_required_nzd = total_capital_required_native * fx_multiplier
    
    limit_entry_target = round(calc_close - (0.75 * calc_atr), 2)
    stop_floor_target = round(calc_close - stop_loss_distance_native, 2)
    with calc_col2:
        st.markdown(f"<p style='font-size: 1.1rem; font-weight: bold; color: #00FF66; margin-bottom: 2px;'>⚡ Mathematical Sizing Blueprint ({selected_calc_ticker})</p>", unsafe_allow_html=True)
        
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("Optimal Execution Size", f"{computed_shares:.4f} Shares")
        with m_col2:
            st.metric("Limit Entry Trigger", f"${limit_entry_target:.2f} {native_currency}")
        with m_col3:
            st.metric("2x ATR Protective Stop", f"${stop_floor_target:.2f} {native_currency}")
            
        st.markdown("### 🧮 Position Funding & Capital Breakdown")
        
        available_native_cash = cash_usd if is_us else (cash_aud if is_au else cash_nzd)
        cash_gap_native = total_capital_required_native - available_native_cash
        
        if cash_gap_native <= 0:
            funding_status = f"🟩 <span class='custom-funding-highlight'>Vault Verified:</span> Your native {native_currency} cash wallet handles this full size comfortably."
        else:
            cash_gap_nzd = cash_gap_native * fx_multiplier
            funding_status = f"🟨 <span class='custom-funding-highlight'>FX Conversion Buffer Needed:</span> Convert an additional ${cash_gap_nzd:,.2f} NZD inside Sharesies to cover this setup."

        st.markdown(
            f"""
            <div class="custom-funding-list">
                <div class="custom-funding-item">
                    • <b>Total Position Capital Sizing:</b> 
                    <span class="custom-funding-highlight">${total_capital_required_native:,.2f} {native_currency}</span> 
                    (Equivalent to <span class="custom-funding-highlight">${total_capital_required_nzd:,.2f} NZD</span>)
                </div>
                <div class="custom-funding-item">
                    • <b>Cushion Distance Risk:</b> 
                    <span class="custom-funding-highlight">${stop_loss_distance_native:.2f} {native_currency}</span> per share down to structural floor.
                </div>
                <div class="custom-funding-item">
                    • <b>Portfolio Funding Status:</b> {funding_status}
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        if calc_close > calc_fast_ma and calc_close > calc_slow_ma:
            st.markdown("""<div style='padding: 8px; background-color: #1A2E3B; border-left: 5px solid #38BDF8; font-size: 0.95rem; font-weight: bold; color: #FFFFFF;'>🌟 ASSET RUNNING CONSTRUCTIVE MOMENTUM: Execution blueprint calibrated to buy structural pullbacks.</div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div style='padding: 8px; background-color: #2E1A1A; border-left: 5px solid #EF4444; font-size: 0.95rem; font-weight: bold; color: #FFFFFF;'>⚠️ STRUCTURAL BEAR WARNING: Asset is trading underneath core moving average baselines. Scaledown deployment sizes recommended.</div>""", unsafe_allow_html=True)
else:
    st.info("💡 Layer C Standby: Add active stock tickers into your Portfolio or Watchlist sidebar slots to run sizing risk simulations.")

# ==============================================================================
# LINEAR FOOTER: LAYER D INSTITUTIONAL SECTOR MONEY FLOW
# ==============================================================================
st.markdown("---")
st.markdown("#### 🔄 Layer D: Institutional Sector Money Flow")
if macro_sector_rows:
    sector_df = pd.DataFrame(macro_sector_rows).sort_values(by="RSI Status Value", ascending=False)
    
    # FIXED EXPANDED HEIGHT ENGINE: 480px cleanly presents all 12 sectors inline
    st.dataframe(
        sector_df, 
        use_container_width="stretch", 
        hide_index=True,
        height=480,
        column_config={
            "Closing Price": st.column_config.NumberColumn(format="$%.2f"),
            "RSI Status Value": st.column_config.NumberColumn("RSI Value", format="%.1f"),
            "RSI Speedometer": st.column_config.TextColumn("Velocity Status")
        }
    )
