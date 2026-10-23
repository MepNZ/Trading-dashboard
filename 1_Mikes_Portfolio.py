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

st.set_page_config(
    page_title="Mike's Share Market Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

TARGETS_FILE = "portfolio_targets.json"
CACHE_FILE = "portfolio_market_cache.json"

disk_memory = {}
if os.path.exists(TARGETS_FILE):
    try:
        with open(TARGETS_FILE, 'r') as f: disk_memory = json.load(f)
    except Exception: pass

runtime_positions = disk_memory.get("positions", {})
runtime_watchlist = disk_memory.get("watchlist_tickers", [])
runtime_cash = disk_memory.get("wallet_cash", {"NZD": 0.00, "AUD": 0.00, "USD": 0.00})
runtime_sliders = disk_memory.get("sliders", {"fast_ma": 10, "slow_ma": 100, "roi_window": "1 Year", "graph_horizon": "1 Year"})

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem !important; padding-bottom: 0rem !important; }
        div[data-testid="stVerticalBlock"] > div { margin-top: 0px !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 16px !important; margin-bottom: 30px !important; height: auto !important; }
        .stTabs [data-baseweb="tab-panel"] { padding-top: 25px !important; }
        div[data-testid="element-container"]:has(.exchange-status-banner) + div { margin-top: 15px !important; }
    </style>
    """,
    unsafe_allow_html=True
)

portfolio_slots = list(runtime_positions.keys())[:6]
while len(portfolio_slots) < 6:
    portfolio_slots.append(f"EMPTY_PORT_{len(portfolio_slots)+1}")

watchlist_slots = [t for t in runtime_watchlist if t.strip()][:6]
while len(watchlist_slots) < 6:
    watchlist_slots.append(f"EMPTY_WATCH_{len(watchlist_slots)+1}")

if "fast_ma" not in st.session_state: st.session_state["fast_ma"] = int(runtime_sliders.get("fast_ma", 10))
if "slow_ma" not in st.session_state: st.session_state["slow_ma"] = int(runtime_sliders.get("slow_ma", 100))
if "roi_window" not in st.session_state: st.session_state["roi_window"] = runtime_sliders.get("roi_window", "1 Year")
if "graph_horizon" not in st.session_state: st.session_state["graph_horizon"] = runtime_sliders.get("graph_horizon", "1 Year")
# ==============================================================================
# GITHUB LIVE REPOSITORY SYNC AND TIMEFRAME BOUNDS CONTROL DESK (PART 2A)
# ==============================================================================
import requests

def push_targets_to_github(updated_data):
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    file_path = "portfolio_targets.json"
    if not token or not repo: return False
    clean_repo = repo.strip("/")
    url = f"https://github.com{clean_repo}/contents/{file_path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    try:
        response = requests.get(url, headers=headers)
        sha = response.json().get("sha") if response.status_code == 200 else None
    except: return False

    json_string = json.dumps(updated_data, indent=4)
    encoded_content = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")
    payload = {"message": "🔄 Automated updates via Cloud Dashboard", "content": encoded_content, "branch": "main"}
    if sha: payload["sha"] = sha

    try:
        put_response = requests.put(url, headers=headers, json=payload)
        return put_response.status_code in [200, 201]
    except: return False

selected_timeframe = st.session_state["roi_window"]
chart_timeframe_choice = st.session_state["roi_window"]
fast_ma_input = st.session_state["fast_ma"]
slow_ma_input = st.session_state["slow_ma"]
cash_nzd = float(st.session_state.get("cash_nzd_input", runtime_cash.get("NZD", 0.00)))
cash_aud = float(st.session_state.get("cash_aud_input", runtime_cash.get("AUD", 0.00)))
cash_usd = float(st.session_state.get("cash_usd_input", runtime_cash.get("USD", 0.00)))

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
nz_now_time = datetime.now(ZoneInfo("Pacific/Auckland")).strftime("%d %b %Y, %I:%M %p %Z")
# ==============================================================================
# WORKSPACE CONTROL DESK TABS AND COMMAND SIDEBAR FLUSH ENGINE (PART 2B)
# ==============================================================================

st.markdown(f"""
    <style>
    header[data-testid="stHeader"], header.stAppHeader {{ background-color: transparent !important; background: transparent !important; border: none !important; box-shadow: none !important; }}
    div[data-testid="stSidebarCollapse"] {{ background-color: #161A22 !important; border: 1px solid #2d3139 !important; border-radius: 4px !important; margin-top: 5px !important; margin-left: 5px !important; }}
    div[data-testid="stAppViewBlockContainer"] {{ padding-top: 0.2rem !important; margin-top: 0px !important; }}
    </style>
    <div style='background-color: #161A22; padding: 6px 12px; border-radius: 4px; display: flex; justify-content: center; gap: 40px; font-size: 1.1rem; font-weight: bold; margin-bottom: 10px; border: 1px solid #2d3139;'>
        <span style='color: #FFFFFF;'>🇺🇸 NYSE US: {us_status}</span>
        <span style='color: #FFFFFF;'>🇦🇺 ASX AUS: {au_status}</span>
        <span style='color: #FFFFFF;'>🇳🇿 NZX NZ: {nz_status}</span>
    </div>
    <div style='text-align: center; font-size: 0.9rem; color: #8B949E; margin-bottom: 5px;'>🕒 Desk Local Time: <strong>{nz_now_time}</strong></div>
    """, unsafe_allow_html=True)

st.markdown("### 🛠️ Live Workspace Control Desk")
control_tab1, control_tab2, control_tab3 = st.tabs(["⚙️ Parameters", "📐 Portfolio Slots", "🧪 Paper Trading"])

with control_tab1:
    c_col1, c_col2, c_col3 = st.columns(3)
    with c_col1:
        st.markdown("#### 🕒 Horizons")
        timeframe_options = ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"]
        if "roi_window" not in st.session_state:
            st.session_state["roi_window"] = runtime_sliders.get("roi_window", "1 Year")
        st.selectbox("Timeframe", timeframe_options, key="roi_window")
        if st.button("🔄 Clear Cache Memory", use_container_width=True):
            if os.path.exists(CACHE_FILE):
                try: os.remove(CACHE_FILE)
                except: pass
            st.cache_data.clear()
            st.rerun()
    with c_col2:
        st.markdown("#### 📈 Analysis")
        st.slider("Fast Moving Average (MA)", min_value=5, max_value=30, value=st.session_state["fast_ma"], step=1, key="fast_ma")
        st.slider("Slow Moving Average (MA)", min_value=20, max_value=200, value=st.session_state["slow_ma"], step=5, key="slow_ma")
    with c_col3:
        st.markdown("#### 💼 Sharesies Vault")
        st.number_input("NZD $ Wallet", min_value=0.00, value=float(runtime_cash.get("NZD", 0.00)), step=1.00, format="%.2f", key="cash_nzd_input")
        st.number_input("AUD $ Wallet", min_value=0.00, value=float(runtime_cash.get("AUD", 0.00)), step=1.00, format="%.2f", key="cash_aud_input")
        st.number_input("USD $ Wallet", min_value=0.00, value=float(runtime_cash.get("USD", 0.00)), step=1.00, format="%.2f", key="cash_usd_input")

with control_tab2:
    slot_cols = st.columns(3)
    for i in range(6):
        ticker = portfolio_slots[i]
        stored = runtime_positions.get(ticker, {}) if "EMPTY" not in ticker else {}
        display_label = ticker if "EMPTY" not in ticker else "Empty Slot"
        with slot_cols[i % 3]:
            with st.expander(f"Slot {i+1}: {display_label}", expanded=False):
                st.text_input(f"Ticker", value="" if "EMPTY" in ticker else ticker, key=f"port_slot_{i}")
                st.number_input("Shares Owned", min_value=0.0000, value=float(stored.get("shares", 0.0)), step=0.0001, format="%.4f", key=f"shares_{i}")
                st.number_input("Entry Price", min_value=0.0, value=float(stored.get("entry", 0.0)), key=f"entry_{i}")
                st.number_input("Upper Target", min_value=0.0, value=float(stored.get("upper", 0.0)), key=f"up_{i}")
                st.number_input("Stop Distance", min_value=0.0, value=float(stored.get("fixed_stop_distance", 15.0)), key=f"fixed_stop_{i}")

with control_tab3:
    runtime_paper = disk_memory.get("paper_positions", {})
    paper_slots = list(runtime_paper.keys())[:6]
    while len(paper_slots) < 6: paper_slots.append(f"EMPTY_PAPER_{len(paper_slots)+1}")
    paper_cols = st.columns(3)
    for i in range(6):
        p_ticker = paper_slots[i]
        p_stored = runtime_paper.get(p_ticker, {}) if "EMPTY" not in p_ticker else {}
        p_display = p_ticker if "EMPTY" not in p_ticker else "Empty Paper Slot"
        stored_date_str = p_stored.get("entry_date", None)
        try: default_date = datetime.strptime(stored_date_str, "%Y-%m-%d").date() if stored_date_str else datetime.today().date()
        except: default_date = datetime.today().date()
        with paper_cols[i % 3]:
            with st.expander(f"Paper Slot {i+1}: {p_display}", expanded=False):
                st.text_input(f"Paper Ticker Symbol", value="" if "EMPTY" in p_ticker else p_ticker, key=f"paper_slot_{i}")
                st.number_input("Paper Entry Price", min_value=0.0, value=float(p_stored.get("entry", 0.0)), key=f"paper_entry_{i}")
                st.date_input("Calendar Date", value=default_date, key=f"paper_date_{i}")

last_save_time = st.session_state.get("last_cloud_save_time", None)
status_html = f"<div style='background-color: #28a745; color: #FFFFFF; padding: 6px 12px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 0.80rem;'>✅ SYNCED: {last_save_time}</div>" if last_save_time else "<div style='background-color: #1C212A; color: #8B949E; padding: 10px 12px; border-radius: 4px; text-align: center; font-weight: bold;'>📁 Standby Mode</div>"

with st.sidebar:
    st.markdown("### ⚡ System Command Desk")
    st.markdown(f'<div style="margin-bottom: 12px;">{status_html}</div>', unsafe_allow_html=True)
    if st.button("💾 SAVE & SYNC WORKSPACE", type="primary", use_container_width=True):
        live_sidebar_bounds = {
            "wallet_cash": {"NZD": cash_nzd, "AUD": cash_aud, "USD": cash_usd},
            "sliders": {"fast_ma": int(fast_ma_input), "slow_ma": int(slow_ma_input), "roi_window": selected_timeframe, "graph_horizon": selected_timeframe},
            "positions": {}, "watchlist_tickers": [], "paper_positions": {}
        }
        for idx in range(6):
            t_input = st.session_state.get(f"port_slot_{idx}", portfolio_slots[idx]).upper().strip()
            if t_input and "EMPTY" not in t_input:
                live_sidebar_bounds["positions"][t_input] = {
                    "shares": float(st.session_state.get(f"shares_{idx}", 0.0)),
                    "entry": float(st.session_state.get(f"entry_{idx}", 0.0)),
                    "upper": float(st.session_state.get(f"up_{idx}", 0.0)),
                    "fixed_stop_distance": float(st.session_state.get(f"fixed_stop_{idx}", 15.0))
                }
        paper_positions_to_save = {}
        for idx in range(6):
            slot_ticker = st.session_state.get(f"paper_slot_{idx}", "").strip().upper()
            if slot_ticker and "EMPTY" not in slot_ticker:
                slot_date = st.session_state.get(f"paper_date_{idx}", datetime.today().date())
                paper_positions_to_save[slot_ticker] = {
                    "shares": 1.0, "entry": float(st.session_state.get(f"paper_entry_{idx}", 0.0)),
                    "entry_date": slot_date.strftime("%Y-%m-%d") if hasattr(slot_date, "strftime") else str(slot_date)
                }
        live_sidebar_bounds["paper_positions"] = paper_positions_to_save
        with open(TARGETS_FILE, 'w') as f: json.dump(live_sidebar_bounds, f, indent=4)
        st.session_state["last_cloud_save_time"] = datetime.now().strftime("%I:%M:%S %p")
        st.cache_data.clear()
        st.rerun()
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: DATA BATCHING & INDICATORS (PART 3 OF 4)
# ==============================================================================

def get_live_fx_rates():
    nzd_rate, aud_rate = 1.6500, 1.1000  
    try:
        nzd_rate = float(yf.Ticker("NZD=X").history(period="1d")['Close'].dropna().iloc[-1])
        if nzd_rate < 1.0: nzd_rate = 1.0 / nzd_rate
        aud_rate = float(yf.Ticker("AUDNZD=X").history(period="1d")['Close'].dropna().iloc[-1])
    except: pass
    return nzd_rate, aud_rate

usd_to_nzd_rate, aud_to_nzd_rate = get_live_fx_rates()

@st.cache_data(ttl=28800)
def fetch_all_market_data_batch_cached(ticker_list, start_date, execution_day_token):
    """Holds historical matrix frames in RAM to terminate slider lag spikes entirely."""
    try:
        valid_tickers = [t for t in ticker_list if t and "EMPTY" not in t]
        if valid_tickers:
            df_live = yf.download(valid_tickers, start=start_date, progress=False)
            if not df_live.empty:
                df_live = df_live.swaplevel(0, 1, axis=1) if isinstance(df_live.columns, pd.MultiIndex) else df_live
                return df_live.sort_index(axis=1, level=0)
    except: pass
    return pd.DataFrame()

# Fallback wrapper supporting the original signature rules
def fetch_all_market_data_batch(ticker_list, start_date):
    today_token = datetime.today().strftime("%Y-%m-%d")
    return fetch_all_market_data_batch_cached(ticker_list, start_date, today_token)

def extract_ticker_dataframe(df_all, ticker):
    try:
        if df_all.empty: return pd.DataFrame()
        if isinstance(df_all.columns, pd.MultiIndex):
            if ticker in df_all.columns.get_level_values(0):
                df = df_all[ticker].copy()
                df.columns = [str(c).title() for c in df.columns]
                return df.dropna(subset=['Close'])
        else:
            if ticker in df_all.columns:
                return pd.DataFrame({'Close': df_all[ticker]}).dropna()
    except: pass
    return pd.DataFrame()

def calculate_indicators_only(df, fast_ma, slow_ma):
    df = df.copy()
    if df.empty or len(df) < 5: return df
    
    # Secure string-to-integer translation handling
    f_ma = min(int(fast_ma), len(df))
    s_ma = min(int(slow_ma), len(df))
    
    close_series = df['Close'].astype(float)
    high_series = df['High'].astype(float)
    low_series = df['Low'].astype(float)
    
    df['Fast_MA'] = close_series.rolling(window=f_ma, min_periods=1).mean()
    df['Slow_MA'] = close_series.rolling(window=s_ma, min_periods=1).mean()
    
    df['True_Range'] = pd.concat([
        (high_series - low_series), 
        (high_series - close_series.shift(1)).abs(), 
        (low_series - close_series.shift(1)).abs()
    ], axis=1).max(axis=1)
    
    df['ATR'] = df['True_Range'].rolling(window=min(14, len(df)), min_periods=1).mean()
    
    delta = close_series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=min(14, len(df)), min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=min(14, len(df)), min_periods=1).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)))).fillna(50)
    
    df['MACD'] = close_series.ewm(span=min(12, len(df)), adjust=False).mean() - close_series.ewm(span=min(26, len(df)), adjust=False).mean()
    df['Signal_Line'] = df['MACD'].ewm(span=min(9, len(df)), adjust=False).mean()
    return df
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: FULL SECTOR TAXONOMY & MATRIX POOLS (PART 4A)
# ==============================================================================

def apply_market_signal_theme(df):
    def style_metric_cells(row):
        styles = [''] * len(row)
        if 'Alert status' in row.index:
            val = row['Alert status']
            idx = row.index.get_loc('Alert status')
            if val == "🌟 STRONG BUY": styles[idx] = 'background-color: #007bff; color: #ffffff; font-weight: bold;'
            elif val == "🟩 BULLISH BREAKOUT": styles[idx] = 'background-color: #1a2e3b; color: #38bdf8; font-weight: bold;'
            elif val == "🟢 Bullish Turning (High Volume)": styles[idx] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == "🟨 MOMENTUM WARNING": styles[idx] = 'background-color: #ffe8a1; color: #856404; font-weight: bold;'
            elif val == "🔴 Structural Bear": styles[idx] = 'background-color: #3a1e1e; color: #e74c3c; font-weight: bold;'
        return styles
    return df.style.apply(style_metric_cells, axis=1)

master_unified_rows, active_live_positions, operational_dfs = [], [], {}
lookback_days_map = {"1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365, "2 Years": 730}
lookback_start_date = datetime.now() - timedelta(days=lookback_days_map["2 Years"] + 250)
macro_sector_rows = []
sector_mapping_dictionary = {
    "SPY": "🇺🇸 S&P 500 Index", "XLK": "💻 Technology", "XLY": "📦 Consumer Discretionary", 
    "XLC": "🗣️ Communication", "XLF": "🏦 Financials", "XLV": "🩺 Healthcare", 
    "XLP": "🛒 Consumer Staples", "XLI": "🏗️ Industrials", "XLE": "🛢️ Energy", 
    "XLB": "🧱 Materials", "XLU": "⚡ Utilities", "XLRE": "🏢 Real Estate"
}

clean_portfolio_list = [t for t in portfolio_slots if t and "EMPTY" not in t]
clean_paper_list = [t for t in runtime_paper.keys() if t and "EMPTY" not in t]

all_active_workspace_tickers = list(dict.fromkeys(clean_portfolio_list + clean_paper_list))
extended_fetching_tickers = list(set(all_active_workspace_tickers + list(sector_mapping_dictionary.keys())))
RAW_MARKET_BATCH = fetch_all_market_data_batch(extended_fetching_tickers, lookback_start_date)

# SYNTAX FIXED: "NFLX" and "DIS" now have their explicit sector key-value colons intact
asset_sector_tags = {
    "AAPL": "XLK", "MSFT": "XLK", "GOOGL": "XLC", "AMZN": "XLY", "META": "XLC", "BRK-B": "XLF", "JNJ": "XLV", 
    "V": "XLF", "PG": "XLP", "WMT": "XLP", "LLY": "XLV", "UNH": "XLV", "HD": "XLY", "XOM": "XLE", 
    "CVX": "XLE", "MA": "XLF", "MRK": "XLV", "PEP": "XLP", "KO": "XLP", "COST": "XLP", "NVDA": "XLK", 
    "AMD": "XLK", "AVGO": "XLK", "QCOM": "XLK", "ASML": "XLK", "INTC": "XLK", "MU": "XLK", "ARM": "XLK", 
    "SMCI": "XLK", "PLTR": "XLK", "CRM": "XLK", "NOW": "XLK", "WDAY": "XLK", "SNOW": "XLK", "NET": "XLK", 
    "DDOG": "XLK", "CRWD": "XLK", "PANW": "XLK", "FTNT": "XLK", "ZS": "XLK", "TSLA": "XLY", "MSTR": "XLF", 
    "COIN": "XLF", "HOOD": "XLF", "DKNG": "XLY", "SHOP": "XLK", "NFLX": "XLY", "DIS": "XLC", "JPM": "XLF", 
    "BAC": "XLF", "F": "XLY", "GM": "XLY", "AAL": "XLI", "DAL": "XLI", "UAL": "XLI", "KRE": "XLF", 
    "XBI": "XLV", "PFE": "XLV", "KVUE": "XLP", "T": "XLC", "VZ": "XLC", "CMCSA": "XLC", "HPQ": "XLK", 
    "HPE": "XLK", "BMY": "XLV", "NEM": "XLB", "GOLD": "XLB", "HBAN": "XLF", "KEY": "XLF", "RF": "XLF", 
    "FITB": "XLF", "NYCB": "XLF", "SOFI": "XLF", "SNAP": "XLC", "U": "XLK", "CLF": "XLB", "X": "XLB", 
    "AA": "XLB", "FCX": "XLB", "SBUX": "XLY", "CSCO": "XLK", "ACN": "XLK", "TXN": "XLK", "IBM": "XLK", 
    "AMAT": "XLK", "GS": "XLF", "MS": "XLF", "WFC": "XLF", "C": "XLF", "BLK": "XLF", "AXP": "XLF", 
    "INTU": "XLK", "PGR": "XLF", "CB": "XLF", "BX": "XLF", "SCHW": "XLF", "MMC": "XLF", "AON": "XLF", 
    "COR": "XLV", "CI": "XLV", "AMGN": "XLV", "GILD": "XLV", "ABT": "XLV", "MDT": "XLV", "ISRG": "XLV", 
    "REGN": "XLV", "VRTX": "XLV", "GEV": "XLI", "WM": "XLI", "NOC": "XLI", "GD": "XLI", "ETN": "XLI", 
    "PH": "XLI", "CSX": "XLI", "NSC": "XLI", "NKE": "XLY", "MCD": "XLY", "TJX": "XLY", "ORLY": "XLY", 
    "AZO": "XLY", "LOW": "XLY", "MAR": "XLY", "HLT": "XLY", "BKNG": "XLY", "MDLZ": "XLP", "MO": "XLP", 
    "PM": "XLP", "TGT": "XLY", "EL": "XLP", "CL": "XLP", "KMB": "XLP", "TMUS": "XLC", "CHTR": "XLC", 
    "EA": "XLK", "TTWO": "XLK", "RBLX": "XLK", "OKTA": "XLK", "TEAM": "XLK", "LIN": "XLB", "PLD": "XLRE"
}
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: VECTOR SECTOR PROCESSOR (PART 4A)
# ==============================================================================

roi_cutoff_date = datetime.now() - timedelta(days=lookback_days_map[selected_timeframe])

# Vectorized global cross-sectional math for sector taxonomy pools
if not RAW_MARKET_BATCH.empty:
    sec_close_matrix = RAW_MARKET_BATCH.xs('Close', axis=1, level=1)
    sec_high_matrix = RAW_MARKET_BATCH.xs('High', axis=1, level=1)
    sec_low_matrix = RAW_MARKET_BATCH.xs('Low', axis=1, level=1)
    sec_vol_matrix = RAW_MARKET_BATCH.xs('Volume', axis=1, level=1)

    # Compute global indicators across all columns in memory instantly
    sec_fast_ma_matrix = sec_close_matrix.rolling(window=min(int(fast_ma_input), len(sec_close_matrix)), min_periods=1).mean()
    sec_slow_ma_matrix = sec_close_matrix.rolling(window=min(int(slow_ma_input), len(sec_close_matrix)), min_periods=1).mean()
    
        # High-speed native Pandas matrix comparison completely bypasses version bugs
    sec_tr_matrix = pd.concat([(sec_high_matrix - sec_low_matrix), (sec_high_matrix - sec_close_matrix.shift(1)).abs(), (sec_low_matrix - sec_close_matrix.shift(1)).abs()], axis=1)
    sec_tr_df = sec_tr_matrix.max(axis=1, level=1) if isinstance(sec_tr_matrix.columns, pd.MultiIndex) else sec_tr_matrix.groupby(level=0, axis=1).max()
    sec_tr_df = sec_tr_df.fillna(0.0)

    sec_atr_matrix = sec_tr_df.rolling(window=min(14, len(sec_tr_df)), min_periods=1).mean()
    sec_vol_avg_matrix = sec_vol_matrix.rolling(window=min(20, len(sec_vol_matrix)), min_periods=1).mean()

    sec_delta = sec_close_matrix.diff()
    sec_gain = sec_delta.clip(lower=0).rolling(window=min(14, len(sec_delta)), min_periods=1).mean()
    sec_loss = (-sec_delta.clip(upper=0)).rolling(window=min(14, len(sec_delta)), min_periods=1).mean()
    sec_rsi_matrix = 100 - (100 / (1 + (sec_gain / sec_loss.replace(0, np.nan)))).fillna(50)

    sec_macd_matrix = sec_close_matrix.ewm(span=min(12, len(sec_close_matrix)), adjust=False).mean() - sec_close_matrix.ewm(span=min(26, len(sec_close_matrix)), adjust=False).mean()
    sec_sig_matrix = sec_macd_matrix.ewm(span=min(9, len(sec_macd_matrix)), adjust=False).mean()
else:
    sec_close_matrix = pd.DataFrame()
if sec_close_matrix.empty or len(sec_close_matrix.columns) == 0:
    st.warning("⚠️ Network Connection Throttled by Provider. Please wait 1-2 minutes for the cache to clear.")
    st.stop()

# ==============================================================================
# ACTIVE POSITION MATRIX ASSEMBLY ENGINE (PART 4B)
# ==============================================================================

# Define the missing mapping dictionary to resolve the NameError safely
local_name_map = {
    "F": "Ford Motor Co.", "GM": "General Motors", "PFE": "Pfizer Inc.", "T": "AT&T Inc.",
    "MDT": "Medtronic plc", "VZ": "Verizon Communications", "AAL": "American Airlines", "DAL": "Delta Air Lines",
    "SOFI": "SoFi Technologies", "PLTR": "Palantir Technologies", "AIR.NZ": "Air New Zealand",
    "SPK.NZ": "Spark NZ", "FBU.NZ": "Fletcher Building", "TLS.AX": "Telstra Group"
}

for sector_symbol, descriptive_name in sector_mapping_dictionary.items():
    if not sec_close_matrix.empty and sector_symbol in sec_close_matrix.columns:
        s_close = float(sec_close_matrix[sector_symbol].iloc[-1])
        s_rsi = float(sec_rsi_matrix[sector_symbol].iloc[-1])
        rsi_label = f"{s_rsi:.1f} 🔴 OVERBOUGHT" if s_rsi >= 70.0 else (f"{s_rsi:.1f} 🟢 OVERSOLD" if s_rsi <= 30.0 else f"{s_rsi:.1f} Healthy")
        macro_sector_rows.append({"Sector Symbol": sector_symbol, "Sector Domain Name": descriptive_name, "Closing Price": s_close, "RSI Status Value": s_rsi, "RSI Speedometer": rsi_label})

for ticker in all_active_workspace_tickers:
    if sec_close_matrix.empty or ticker not in sec_close_matrix.columns: continue
    
    # Reconstruct localized slice mapping for chart renderers cleanly from global arrays
    df_ticker_rebuilt = pd.DataFrame(index=RAW_MARKET_BATCH.index)
    df_ticker_rebuilt['Close'] = sec_close_matrix[ticker]
    df_ticker_rebuilt['High'] = sec_high_matrix[ticker]
    df_ticker_rebuilt['Low'] = sec_low_matrix[ticker]
    df_ticker_rebuilt['Volume'] = sec_vol_matrix[ticker]
    df_ticker_rebuilt['Fast_MA'] = sec_fast_ma_matrix[ticker]
    df_ticker_rebuilt['Slow_MA'] = sec_slow_ma_matrix[ticker]
    df_ticker_rebuilt['RSI'] = sec_rsi_matrix[ticker]
    df_ticker_rebuilt['ATR'] = sec_atr_matrix[ticker]
    df_ticker_rebuilt['MACD'] = sec_macd_matrix[ticker]
    df_ticker_rebuilt['Signal_Line'] = sec_sig_matrix[ticker]
    operational_dfs[ticker] = df_ticker_rebuilt

    localized_cutoff = roi_cutoff_date.tz_localize(df_ticker_rebuilt.index.tz) if df_ticker_rebuilt.index.tz else roi_cutoff_date
    hist_df_sliced = df_ticker_rebuilt[df_ticker_rebuilt.index >= localized_cutoff]
    if hist_df_sliced.empty: hist_df_sliced = df_ticker_rebuilt

    resolved_name = disk_memory.get("local_name_map", {}).get(ticker, local_name_map.get(ticker, ticker))
    last_close = float(df_ticker_rebuilt['Close'].iloc[-1])
    fast_ma_val = float(df_ticker_rebuilt['Fast_MA'].iloc[-1])
    slow_ma_val = float(df_ticker_rebuilt['Slow_MA'].iloc[-1])
    rsi_val = float(df_ticker_rebuilt['RSI'].iloc[-1])
    atr_val = float(df_ticker_rebuilt['ATR'].iloc[-1]) if df_ticker_rebuilt['ATR'].iloc[-1] > 0 else (last_close * 0.02)
    
    safe_daily_limit_target = round(last_close - (0.75 * atr_val), 2)
    safe_take_profit_target = round((last_close + (2.0 * atr_val)) * 1.012, 2)
    
    window_start_price = float(hist_df_sliced['Close'].iloc[0]) if not hist_df_sliced.empty else last_close
    ticker_timeframe_roi = ((last_close - window_start_price) / window_start_price) * 100

    vol_twenty_avg = sec_vol_avg_matrix[ticker].iloc[-1] if ticker in sec_vol_avg_matrix.columns else 1.0
    live_snapshot_volume = float(df_ticker_rebuilt['Volume'].iloc[-1])
    v_surge = live_snapshot_volume / vol_twenty_avg if vol_twenty_avg > 0 else 1.0

    if last_close > fast_ma_val and last_close > slow_ma_val:
        strategy_status = "🌟 STRONG BUY" if v_surge >= 1.5 else "🟩 BULLISH BREAKOUT"
    elif last_close > fast_ma_val and last_close <= slow_ma_val:
        strategy_status = "🟢 Bullish Turning (High Volume)" if v_surge >= 1.5 else "🟨 MOMENTUM WARNING"
    else:
        strategy_status = "🔴 Structural Bear"
    
    assigned_sector = asset_sector_tags.get(ticker, "Other")
    
    master_unified_rows.append({
        "Ticker": ticker, "Sector": assigned_sector, "Company Name": resolved_name, "Closing": last_close, 
        "Limit Entry Target": safe_daily_limit_target, "Take Profit Target": safe_take_profit_target, 
        "Timeframe ROI %": ticker_timeframe_roi, "Alert status": strategy_status, "Fast MA": fast_ma_val, 
        "Slow MA": slow_ma_val, "RSI": rsi_val, "ATR": atr_val
    })

# ==============================================================================
# RESTORED: MULTI-CURRENCY DRIFT PROTECTION & INVESTMENT MATH ENGINE (PART 4C)
# ==============================================================================
    if ticker in clean_portfolio_list:
        stored_block = runtime_positions.get(ticker, {})
        custom_saved_shares = float(stored_block.get("shares", 0.0))
        entry_p = float(stored_block.get("entry", 0.0))
        upper_target = float(stored_block.get("upper", 0.0))
        fixed_stop_dist = float(stored_block.get("fixed_stop_distance", 15.0))
        
        if custom_saved_shares > 0.0:
            implied_investment_local = custom_saved_shares * entry_p
            is_us_asset = not (ticker.endswith(".NZ") or ticker.endswith(".AX"))
            native_currency_label = "USD" if is_us_asset else ("AUD" if ticker.endswith(".AX") else "NZD")
            currency_multiplier = usd_to_nzd_rate if native_currency_label == "USD" else (aud_to_nzd_rate if native_currency_label == "AUD" else 1.0)
            current_value_local = custom_saved_shares * last_close
            
            # FIXED: Variable updated to point directly to the rebuilt matrix
            hist_365 = df_ticker_rebuilt.tail(52)
            true_52w_high = float(hist_365['High'].max()) if not hist_365.empty else last_close
            true_52w_low = float(hist_365['Low'].min()) if not hist_365.empty else last_close
            
            # Restore compound algorithmic stop floor targets
            calculated_trailing_floor = true_52w_high - (2.0 * atr_val)
            if calculated_trailing_floor < (entry_p - (2.0 * atr_val)): 
                calculated_trailing_floor = entry_p - (2.0 * atr_val)
            if calculated_trailing_floor >= last_close: 
                calculated_trailing_floor = last_close - (2.0 * atr_val)
            if fixed_stop_dist > 0.0 and (last_close - fixed_stop_dist) > calculated_trailing_floor:
                calculated_trailing_floor = last_close - fixed_stop_dist

            # Restore target price projection buffers
            distance_to_target = upper_target - last_close if upper_target > 0.0 else 0.0
            pct_to_target = (distance_to_target / last_close) * 100 if last_close > 0.0 else 0.0

            active_live_positions.append({
                "Ticker": ticker, 
                "Company Name": resolved_name, 
                "Shares": custom_saved_shares, 
                "Currency": native_currency_label,
                "My Entry Price": entry_p, 
                "Live Market Price": last_close, 
                "Daily Pullback Limit": safe_daily_limit_target,   
                "Take-Profit Target": safe_take_profit_target, 
                "Upper Target": upper_target,
                "Pct to Target": pct_to_target,
                "Investment (Local)": implied_investment_local,
                "Investment (NZD)": implied_investment_local * currency_multiplier, 
                "Current Value (Local)": current_value_local,
                "Current Value (NZD)": current_value_local * currency_multiplier, 
                "Trailing Floor": calculated_trailing_floor,
                "52W High Peak": true_52w_high,
                "52W Low Floor": true_52w_low
            })

st.markdown("#### 💼 Layer A: My Portfolio Ledger")
if active_live_positions:
    p_df = pd.DataFrame(active_live_positions)
    p_df["Net Profit (NZD)"] = p_df["Current Value (NZD)"] - p_df["Investment (NZD)"]
    p_df["Live ROI"] = (p_df["Net Profit (NZD)"] / p_df["Investment (NZD)"]) * 100
    
    cols_layer_a = [
        "Ticker", "Company Name", "Shares", "Currency", "My Entry Price", 
        "Live Market Price", "Daily Pullback Limit", "Take-Profit Target",
        "Investment (Local)", "Investment (NZD)", "Current Value (Local)", 
        "Current Value (NZD)", "Trailing Floor", "Net Profit (NZD)", "Live ROI"
    ]
    p_df = p_df[[c for c in cols_layer_a if c in p_df.columns]]
    
    st.dataframe(
        p_df, use_container_width=True, hide_index=True, height=200,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Company Name": st.column_config.TextColumn("Asset Name", width="small"),
            "Shares": st.column_config.NumberColumn("Shares", format="%.2f", width="small"),
            "Currency": st.column_config.TextColumn("Currency", width="small"),
            "My Entry Price": st.column_config.NumberColumn("Bought at", format="$%.2f", width="small"),
            "Live Market Price": st.column_config.NumberColumn("Live price", format="$%.2f", width="small"),
            "Daily Pullback Limit": st.column_config.NumberColumn("New Limit Buy", format="$%.2f", width="small"),
            "Take-Profit Target": st.column_config.NumberColumn("Take Profit", format="$%.2f", width="small"),
            "Investment (Local)": st.column_config.NumberColumn("Cost (Loc)", format="$%.2f", width="small"),
            "Investment (NZD)": st.column_config.NumberColumn("Cost (NZD)", format="$%.2f", width="small"),
            "Current Value (Local)": st.column_config.NumberColumn("Value (Loc)", format="$%.2f", width="small"),
            "Current Value (NZD)": st.column_config.NumberColumn("Value (NZD)", format="$%.2f", width="small"),
            "Trailing Floor": st.column_config.NumberColumn("Stop Loss", format="$%.2f", width="small"),
            "Net Profit (NZD)": st.column_config.NumberColumn("P&L (NZD)", format="$%.2f", width="small"),
            "Live ROI": st.column_config.NumberColumn("ROI", format="%.2f%%", width="small")
        }
    )
# ==============================================================================
# TOTAL DASHBOARD METRICS SUMMARY & ACCOUNT BALANCE STATS GENERATOR (PART 4D)
# ==============================================================================
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
# LAYER A.2 PAPER PORTFOLIO SANBOX ACCOUNT MONITORS (PART 4E)
# ==============================================================================
st.markdown("---")
st.markdown("#### 🧪 Layer A.2: Paper Trading Forward-Testing Ledger")

runtime_paper_data = disk_memory.get("paper_positions", {})
active_paper_positions = []

for idx in range(6):
    p_ticker = st.session_state.get(f"paper_slot_{idx}", "").strip().upper()
    p_entry_price = float(st.session_state.get(f"paper_entry_{idx}", 0.0))
    p_date = st.session_state.get(f"paper_date_{idx}", None)
    p_shares = 1.0
    
    if not p_ticker or "EMPTY" in p_ticker:
        temp_keys = list(runtime_paper_data.keys())
        if idx < len(temp_keys):
            p_ticker = temp_keys[idx]
            p_stored_block = runtime_paper_data.get(p_ticker, {})
            p_entry_price = float(p_stored_block.get("entry", 0.0))
            stored_date_str = p_stored_block.get("entry_date", None)
            if stored_date_str:
                try: p_date = datetime.strptime(stored_date_str, "%Y-%m-%d").date()
                except: p_date = datetime.today().date()

    if p_ticker and "EMPTY" not in p_ticker and p_entry_price > 0.0:
        if p_ticker in operational_dfs and not operational_dfs[p_ticker].empty:
            p_calc = operational_dfs[p_ticker]
            p_latest = p_calc.iloc[-1]
            p_close = float(p_latest['Close'])
            p_atr = float(p_latest['ATR']) if 'ATR' in p_latest else (p_close * 0.02)
        else:
            p_close = p_entry_price
            p_atr = p_close * 0.02
            
        if p_date:
            try: days_active = (datetime.today().date() - p_date).days
            except: days_active = 0
        else:
            days_active = 0
            
        p_cost = p_shares * p_entry_price
        p_val = p_shares * p_close
        p_pnl = p_val - p_cost
        p_roi = (p_pnl / p_cost) * 100 if p_cost > 0 else 0.0
        
        active_paper_positions.append({
            "Paper Ticker": p_ticker, "Days Active": f"{days_active} Days" if days_active >= 0 else "0 Days",
            "Simulated Entry": p_entry_price, "Live Price": p_close, "Current Value": p_val,
            "$ ROI": p_pnl, "% ROI": p_roi, "ATR Noise Stop": p_close - (2.0 * p_atr)
        })

if active_paper_positions:
    paper_df = pd.DataFrame(active_paper_positions)
    st.dataframe(
        paper_df, use_container_width=True, hide_index=True, height=180,
        column_config={
            "Paper Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Days Active": st.column_config.TextColumn("Days Active", width="small"),
            "Simulated Entry": st.column_config.NumberColumn("Paper Entry", format="$%.2f", width="small"),
            "Live Price": st.column_config.NumberColumn("Live Close", format="$%.2f", width="small"),
            "Current Value": st.column_config.NumberColumn("Sim Value", format="$%.2f", width="small"),
            "$ ROI": st.column_config.NumberColumn("$ ROI", format="$%.2f", width="small"),
            "% ROI": st.column_config.NumberColumn("% ROI", format="%.2f%%", width="small"),
            "ATR Noise Stop": st.column_config.NumberColumn("Stop Floor", format="$%.2f", width="small")
        }
    )
else:
    st.info("💡 Paper Ledger Standby: Populate tickers in your Layer A.2 sidebar slots to monitor simulated positions safely.")
# ==============================================================================
# ALTAIR HOVER-TRACKER CHART ENGINE AND GENERAL ASSET COMPARISONS (PART 4F)
# ==============================================================================
st.markdown("---")
st.markdown("#### 🔍 Core System Chart Analytics")

unified_chart_list = [t for t in all_active_workspace_tickers if t in operational_dfs]
unified_chart_list = [t for t in unified_chart_list if t and "EMPTY" not in t]

if unified_chart_list:
    selected_portal_ticker = st.radio("🛰️ **Global Chart Engine Quick-Link Bar:**", options=unified_chart_list, horizontal=True)
    if operational_dfs and selected_portal_ticker in operational_dfs:
        full_df = operational_dfs[selected_portal_ticker]
        chart_tz = full_df.copy()
        
    if chart_tz.index.tz is not None:
        chart_tz.index = chart_tz.index.tz_localize(None)
    
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
    st.info("💡 No assets available to plot. Add symbols to your Portfolio slots via the workspace menu.")

st.markdown("---")
st.markdown("#### 📊 Layer B: Asset Comparison Grid")
if master_unified_rows:
    master_df = pd.DataFrame(master_unified_rows)
    columns_to_show = ["Ticker", "Sector", "Company Name", "Closing", "Timeframe ROI %", "Limit Entry Target", "Take Profit Target", "Alert status", "Fast MA", "Slow MA", "RSI", "ATR"]
    master_df = master_df[columns_to_show]
    
    st.dataframe(
        apply_market_signal_theme(master_df), use_container_width=True, hide_index=True, height=200, 
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Sector": st.column_config.TextColumn("Sector", width="small"),
            "Company Name": st.column_config.TextColumn("Asset Name", width="small"),
            "Closing": st.column_config.NumberColumn("Price", format="$%.2f", width="small"), 
            "Timeframe ROI %": st.column_config.NumberColumn("Return", format="%.2f%%", width="small"),
            "Limit Entry Target": st.column_config.NumberColumn("Limit Buy at", format="$%.2f", width="small"), 
            "Take Profit Target": st.column_config.NumberColumn("T/P Exit", format="$%.2f", width="small"), 
            "Alert status": st.column_config.TextColumn("Status", width="medium"),
            "Fast MA": st.column_config.NumberColumn("Fast MA", format="$%.2f", width="small"), 
            "Slow MA": st.column_config.NumberColumn("Slow MA", format="$%.2f", width="small"), 
            "RSI": st.column_config.NumberColumn("RSI", format="%.1f", width="small"),
            "ATR": st.column_config.NumberColumn("ATR", format="$%.2f", width="small")
        }
    )
# ==============================================================================
# POSITION SIZING RISK DEPLOYMENT ENGINE AND GRID FOOTERS (PART 4G)
# ==============================================================================
st.markdown("---")
st.markdown(
    """
    <style>
    div[data-testid="stMetricLabel"] p { font-size: 0.95rem !important; color: #475569 !important; font-weight: 600 !important; text-transform: uppercase; }
    div[data-testid="stMetricValue"] div { font-size: 1.85rem !important; font-weight: 700 !important; color: #0F172A !important; }
    .custom-funding-list { margin-top: 12px; margin-bottom: 16px; }
    .custom-funding-item { font-size: 1.05rem !important; color: #1E293B !important; margin-bottom: 8px; line-height: 1.6; }
    .custom-funding-highlight { color: #0F172A !important; font-weight: 700 !important; font-size: 1.1rem !important; }
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
        selected_calc_ticker = st.selectbox("Target Execution Asset:", options=calculator_tickers, key="layer_c_ticker_select")
        max_risk_nzd = st.number_input("Max Account Risk Allowed (NZD $):", min_value=5.00, max_value=1000.00, value=25.00, step=25.00, format="%.2f", key="layer_c_max_risk_input")
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
    
    is_nz, is_au = selected_calc_ticker.endswith(".NZ"), selected_calc_ticker.endswith(".AX")
    native_currency = "USD" if not (is_nz or is_au) else ("AUD" if is_au else "NZD")
    fx_multiplier = usd_to_nzd_rate if not (is_nz or is_au) else (aud_to_nzd_rate if is_au else 1.0)
    
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
        with m_col1: st.metric("Optimal Execution Size", f"{computed_shares:.4f} Shares")
        with m_col2: st.metric("Limit Entry Trigger", f"${limit_entry_target:.2f} {native_currency}")
        with m_col3: st.metric("2x ATR Protective Stop", f"${stop_floor_target:.2f} {native_currency}")
            
        st.markdown("### 🧮 Position Funding & Capital Breakdown")
        available_native_cash = cash_usd if not (is_nz or is_au) else (cash_aud if is_au else cash_nzd)
        cash_gap_native = total_capital_required_native - available_native_cash
        
        if cash_gap_native <= 0:
            funding_status = f"🟩 <span class='custom-funding-highlight'>Vault Verified:</span> Native {native_currency} wallet handles this size cleanly."
        else:
            funding_status = f"🟨 <span class='custom-funding-highlight'>FX Buffer Needed:</span> Convert ${cash_gap_native * fx_multiplier:,.2f} NZD inside Sharesies."

        st.markdown(
            f"""
            <div class="custom-funding-list">
                <div class="custom-funding-item">• <b>Total Position Capital:</b> <span class="custom-funding-highlight">${total_capital_required_native:,.2f} {native_currency}</span> (${total_capital_required_nzd:,.2f} NZD)</div>
                <div class="custom-funding-item">• <b>Cushion Distance Risk:</b> <span class="custom-funding-highlight">${stop_loss_distance_native:.2f} {native_currency}</span> per share.</div>
                <div class="custom-funding-item">• <b>Portfolio Funding Status:</b> {funding_status}</div>
            </div>
            """, unsafe_allow_html=True
        )
        if calc_close > calc_fast_ma and calc_close > calc_slow_ma:
            st.markdown("""<div style='padding: 8px; background-color: #1A2E3B; border-left: 5px solid #38BDF8; font-size: 0.95rem; font-weight: bold; color: #FFFFFF;'>🌟 ASSET MOMENTUM CONSTRUCTIVE: Calibrated to buy structural pullbacks.</div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div style='padding: 8px; background-color: #2E1A1A; border-left: 5px solid #EF4444; font-size: 0.95rem; font-weight: bold; color: #FFFFFF;'>⚠️ STRUCTURAL BEAR: Asset is trading below average baselines. Scaledown sizing recommended.</div>""", unsafe_allow_html=True)
else:
    st.info("💡 Layer C Standby: Add active stock tickers into your slots to run risk simulations.")

st.markdown("---")
st.markdown("#### 🔄 Layer D: Institutional Sector Money Flow")
if macro_sector_rows:
    st.dataframe(pd.DataFrame(macro_sector_rows).sort_values(by="RSI Status Value", ascending=False), use_container_width=True, hide_index=True, height=480)
