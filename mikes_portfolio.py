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
    
    # High-Visibility Sync Status Banner
    if "last_cloud_save_time" not in st.session_state:
        st.session_state["last_cloud_save_time"] = None

    if st.session_state["last_cloud_save_time"]:
        if "⚠️" in st.session_state["last_cloud_save_time"]:
            st.markdown(f"""
                <div style='background-color: #dc3545; color: #FFFFFF; padding: 10px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 1.1rem; margin-bottom: 15px; border: 2px solid #bd2130;'>
                    {st.session_state["last_cloud_save_time"]}
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style='background-color: #28a745; color: #FFFFFF; padding: 10px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 1.1rem; margin-bottom: 15px; border: 2px solid #1e7e34; box-shadow: 0px 4px 10px rgba(0,0,0,0.3);'>
                    ✅ SYNCED TO GITHUB LIVE<br>
                    <span style='font-size: 0.9rem; font-weight: normal; opacity: 0.9;'>Timestamp: {st.session_state["last_cloud_save_time"]}</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style='background-color: #1C212A; color: #8B949E; padding: 10px; border-radius: 4px; text-align: center; font-weight: bold; font-size: 1.0rem; margin-bottom: 15px; border: 1px solid #30363D;'>
                📁 Database Standby: Connection Ready
            </div>
        """, unsafe_allow_html=True)

    if st.button("🔄 Clear App Cache Memory", use_container_width="stretch"):
        if os.path.exists(CACHE_FILE):
            try: os.remove(CACHE_FILE)
            except: pass
        st.cache_data.clear()
        st.rerun()

    @st.fragment
    def render_isolated_sidebar_controls():
        if st.button("💾 Save Matrix Boundary Changes", use_container_width="stretch"):
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
                    "graph_horizon": st.session_state.get("graph_horizon", "1 Year")
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
            
            # Fire cloud synchronization layout
            synced_ok = push_targets_to_github(live_sidebar_bounds)
            
            if synced_ok:
                st.session_state["last_cloud_save_time"] = datetime.now().strftime("%I:%M:%S %p")
            else:
                st.session_state["last_cloud_save_time"] = "⚠️ Connection Refused by GitHub"
            
            st.cache_data.clear()
            st.rerun()

        st.selectbox("ROI Window", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], key="roi_window")
        st.selectbox("Technical Graph Horizon", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], key="graph_horizon")
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
chart_timeframe_choice = st.session_state["graph_horizon"]
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

us_status = get_exchange_status_badge('America/New_York')
au_status = get_exchange_status_badge('Australia/Sydney', is_nz_au=True)
nz_status = get_exchange_status_badge('Pacific/Auckland', is_nz_au=True)

st.markdown(f"""
    <div style='background-color: #161A22; padding: 6px 12px; border-radius: 4px; display: flex; justify-content: center; gap: 40px; font-size: 1.1rem; font-weight: bold; margin-bottom: 15px; border: 1px solid #2d3139;'>
        <span style='color: #FFFFFF;'>🇺🇸 NYSE US: {us_status}</span>
        <span style='color: #FFFFFF;'>🇦🇺 ASX AUS: {au_status}</span>
        <span style='color: #FFFFFF;'>🇳🇿 NZX NZ: {nz_status}</span>
    </div>
""", unsafe_allow_html=True)

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
lookback_start_date = datetime.now() - timedelta(days=lookback_days_map[selected_timeframe] + 250)

macro_sector_rows = []
sector_mapping_dictionary = {"SPY": "🇺🇸 S&P 500 Index", "XLK": "💻 Technology", "XLY": "📦 Consumer Discretionary", "XLC": "🗣️ Communication", "XLF": "🏦 Financials", "XLV": "🩺 Healthcare", "XLP": "🛒 Consumer Staples", "XLI": "🏗️ Industrials", "XLE": "🛢️ Energy", "XLB": "🧱 Materials", "XLU": "⚡ Utilities", "XLRE": "🏢 Real Estate"}

clean_portfolio_list = [t for t in portfolio_slots if t and "EMPTY" not in t]
clean_watchlist_list = [t for t in watchlist_slots if t and "EMPTY" not in t]
all_active_workspace_tickers = list(set(clean_portfolio_list + clean_watchlist_list))

extended_fetching_tickers = list(set(all_active_workspace_tickers + list(sector_mapping_dictionary.keys())))
RAW_MARKET_BATCH = fetch_all_market_data_batch(extended_fetching_tickers, lookback_start_date)

asset_sector_tags = {
    "AAPL": "XLK", "NVDA": "XLK", "TEAM": "XLK", "ARM": "XLK", "INTC": "XLK", "AMD": "XLK", "SMCI": "XLK",
    "JPM": "XLF", "BAC": "XLF", "GS": "XLF", "COIN": "XLF", "MSTR": "XLF", "CRWD": "XLK",
    "XLE": "XLE", "SPY": "SPY", "QQQ": "QQQ", "DUK": "XLU", "NEM": "XLB", "PLD": "XLRE", "LIN": "XLB"
}

for sector_symbol, descriptive_name in sector_mapping_dictionary.items():
    s_hist = extract_ticker_dataframe(RAW_MARKET_BATCH, sector_symbol)
    if not s_hist.empty and len(s_hist) >= 5:
        s_calc = calculate_indicators_only(s_hist, fast_ma_input, slow_ma_input)
        s_close = float(s_calc['Close'].iloc[-1])
        s_rsi = float(s_calc['RSI'].iloc[-1]) if 'RSI' in s_calc.columns else 50.0
        rsi_label = f"{s_rsi:.1f} 🔴 OVERBOUGHT" if s_rsi >= 70.0 else (f"{s_rsi:.1f} 🟢 OVERSOLD" if s_rsi <= 30.0 else f"{s_rsi:.1f} ⚪ Healthy")
        macro_sector_rows.append({"Sector Symbol": sector_symbol, "Sector Domain Name": descriptive_name, "Closing Price": s_close, "RSI Status Value": s_rsi, "RSI Speedometer": rsi_label})

local_name_map = {
    "AAPL": "Apple Inc.", "AMD": "Advanced Micro Devices", "CRWD": "CrowdStrike Holdings", "NVDA": "NVIDIA Corp",
    "BAC": "Bank of America", "GS": "Goldman Sachs", "JPM": "JPMorgan Chase", "LIN": "Linde plc", "NEM": "Newmont Corp",
    "DUK": "Duke Energy", "PLD": "Prologis Inc", "QQQ": "Nasdaq 100 ETF", "SPY": "S&P 500 ETF", "XLE": "Energy Select ETF"
}

for ticker in all_active_workspace_tickers:
    hist_df = extract_ticker_dataframe(RAW_MARKET_BATCH, ticker)
    if hist_df.empty or len(hist_df) < 5: continue
    df_calc = calculate_indicators_only(hist_df, fast_ma_input, slow_ma_input)
    operational_dfs[ticker] = df_calc
    resolved_name = disk_memory.get("local_name_map", {}).get(ticker, local_name_map.get(ticker, f"{ticker} Asset"))
    last_close = float(df_calc['Close'].iloc[-1])
    fast_ma_val = float(df_calc['Fast_MA'].iloc[-1]) if 'Fast_MA' in df_calc.columns else last_close
    slow_ma_val = float(df_calc['Slow_MA'].iloc[-1]) if 'Slow_MA' in df_calc.columns else last_close
    rsi_val = float(df_calc['RSI'].iloc[-1]) if 'RSI' in df_calc.columns else 50.0
    macd_val = float(df_calc['MACD'].iloc[-1]) if 'MACD' in df_calc.columns else 0.0
    sig_val = float(df_calc['Signal_Line'].iloc[-1]) if 'Signal_Line' in df_calc.columns else 0.0
    atr_val = float(df_calc['ATR'].iloc[-1]) if 'ATR' in df_calc.columns else 1.0
    
        # --- ADDED: CALCULATE TIGHT DAILY PULLBACK LIMIT TARGET (Price - 1x ATR) ---
    safe_daily_limit_target = round(last_close - (1.0 * atr_val), 2)

    if last_close > fast_ma_val and fast_ma_val > slow_ma_val and macd_val > sig_val and rsi_val < 68.0: strategy_status = "🌟 STRONG BUY"
    elif last_close > fast_ma_val and last_close > slow_ma_val: strategy_status = "🟩 BULLISH LONG"
    elif last_close < fast_ma_val and last_close > slow_ma_val: strategy_status = "🟨 MOMENTUM WARNING"
    else: strategy_status = "⬜ CASH FLAT"
    
    assigned_sector = asset_sector_tags.get(ticker, "Other")
    master_unified_rows.append({
        "Ticker": ticker, "Sector": assigned_sector, "Company Name": resolved_name, 
        "Closing": last_close, "Limit Entry Target": safe_daily_limit_target, # <-- INJECTED HERE
        "Alert status": strategy_status, "Fast MA": fast_ma_val, 
        "Slow MA": slow_ma_val, "RSI": rsi_val, "ATR": atr_val
    })
    
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
                "Ticker": ticker, "Shares": custom_saved_shares, "Currency": native_currency_label, 
                "My Entry Price": entry_p, "Live Market Price": last_close, "Investment (Local)": implied_investment_local, 
                "Investment (NZD)": implied_investment_local * currency_multiplier, "Current Value (Local)": current_value_local, 
                "Current Value (NZD)": current_value_local * currency_multiplier, "Trailing Floor": calculated_trailing_floor
            })
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: LEDGER METRICS (PART 4A)
# ==============================================================================
st.markdown("#### 💼 Layer A: My Portfolio Ledger")
if active_live_positions:
    p_df = pd.DataFrame(active_live_positions)
    p_df["Net Profit (NZD)"] = p_df["Current Value (NZD)"] - p_df["Investment (NZD)"]
    p_df["Live ROI"] = (p_df["Net Profit (NZD)"] / p_df["Investment (NZD)"]) * 100
    
    database_names = disk_memory.get("local_name_map", {})
    p_df["Company Name"] = p_df["Ticker"].map(lambda t: database_names.get(t, local_name_map.get(t, f"{t} Asset")))

    cols_layer_a = [
        "Ticker", "Company Name", "Shares", "Currency", "My Entry Price", 
        "Live Market Price", "Investment (Local)", "Investment (NZD)", 
        "Current Value (Local)", "Current Value (NZD)", "Trailing Floor", 
        "Net Profit (NZD)", "Live ROI"
    ]
    p_df = p_df[[c for c in cols_layer_a if c in p_df.columns]]
    
    st.dataframe(
        p_df, use_container_width="stretch", hide_index=True, height=280, 
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Company Name": st.column_config.TextColumn("Company Name", width="medium"),
            "Shares": st.column_config.NumberColumn("Shares", format="%.4f"),
            "Currency": st.column_config.TextColumn("Currency", width="small"),
            "My Entry Price": st.column_config.NumberColumn(format="$%.2f"), 
            "Live Market Price": st.column_config.NumberColumn(format="$%.2f"), 
            "Investment (Local)": st.column_config.NumberColumn("Investment (Local)", format="$%.2f"),
            "Investment (NZD)": st.column_config.NumberColumn(format="$%.2f"),
            "Current Value (Local)": st.column_config.NumberColumn("Current Value (Local)", format="$%.2f"), 
            "Current Value (NZD)": st.column_config.NumberColumn(format="$%.2f"), 
            "Trailing Floor": st.column_config.NumberColumn("2x ATR Stop Floor", format="$%.2f"), 
            "Net Profit (NZD)": st.column_config.NumberColumn(format="$%.2f"), 
            "Live ROI": st.column_config.NumberColumn(format="%.2f%%")
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
unified_chart_list = sorted(list(set(owned_tickers + grid_tickers)))
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
    st.info("💡 No assets available to plot. Add symbols to your Portfolio or Watchlist slots via the sidebar menu.")
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: COMPARISON GRIDS (PART 4C - BLOCK 1)
# ==============================================================================
st.markdown("---")
st.markdown("#### 📊 Layer B: Asset Comparison Grid")
if master_unified_rows:
    master_df = pd.DataFrame(master_unified_rows)
    
    # --- ADDED 'Limit Entry Target' TO COLS LIST ---
    columns_to_show = ["Ticker", "Sector", "Company Name", "Closing", "Limit Entry Target", "Alert status", "Fast MA", "Slow MA", "RSI", "ATR"]
    master_df = master_df[columns_to_show]
    
    st.dataframe(
        apply_market_signal_theme(master_df), use_container_width="stretch", hide_index=True, height=350, 
        column_config={
            "Sector": st.column_config.TextColumn("Sector ETF", width="small"),
            "Closing": st.column_config.NumberColumn("Price", format="$%.2f"), 
            "Limit Entry Target": st.column_config.NumberColumn("Daily Pullback Limit", format="$%.2f"), # <-- NEW CONFIG BLOCK
            "Fast MA": st.column_config.NumberColumn(format="$%.2f"), 
            "Slow MA": st.column_config.NumberColumn(format="$%.2f"), 
            "RSI": st.column_config.NumberColumn(format="%.1f"),
            "ATR": st.column_config.NumberColumn("Daily ATR", format="$%.2f")
        }
    )

st.markdown("---")
st.markdown("#### 🔄 Layer C: Institutional Sector Money Flow")
if macro_sector_rows:
    sector_df = pd.DataFrame(macro_sector_rows).sort_values(by="RSI Status Value", ascending=False)
    st.dataframe(
        sector_df, use_container_width="stretch", hide_index=True, height=250,
        column_config={
            "Closing Price": st.column_config.NumberColumn(format="$%.2f"),
            "RSI Status Value": st.column_config.NumberColumn("RSI Value", format="%.1f"),
            "RSI Speedometer": st.column_config.TextColumn("Velocity Status")
        }
    )
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: TRADING JOURNAL LOOPS (PART 4C - BLOCK 2)
# ==============================================================================
st.markdown("---")
st.markdown("#### 📝 Layer D: Advanced Performance Journal Log")
JOURNAL_FILE = "trading_journal.json"

def load_trading_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            with open(JOURNAL_FILE, 'r') as f: return json.load(f)
        except: return []
    return []

def save_trading_journal(journal_data):
    with open(JOURNAL_FILE, 'w') as f: json.dump(journal_data, f, indent=4)

current_journal = load_trading_journal()
management_col1, management_col2 = st.columns(2)

with management_col1:
    with st.expander("🗑️ Database Administrative Controls (Delete Rows)"):
        if current_journal:
            deletion_options = [
                f"[{i}] {row['Date']} | {row['Ticker']} | {row['Action']} | {row['Shares']} Shares @ ${row['Price']:.2f}"
                for i, row in enumerate(current_journal)
            ]
            selected_row_to_kill = st.selectbox("Select Record Row to Permanently Remove:", options=deletion_options)
            if st.button("❌ Delete Selected Record Match", use_container_width="stretch"):
                target_idx = int(selected_row_to_kill.split(']')[0].replace('[', ''))
                removed_item = current_journal.pop(target_idx)
                save_trading_journal(current_journal)
                st.toast(f"Removed record entry for {removed_item['Ticker']} successfully.")
                st.rerun()
        else:
            st.info("No active records available to modify or delete.")

with management_col2:
    if current_journal:
        export_rows = []
        inventory_pool = {}
        for row in sorted(current_journal, key=lambda x: x['Date']):
            row_copy = row.copy()
            tk = row_copy['Ticker']
            row_copy['Realized PnL'] = "-"
            row_copy['PnL ROI (%)'] = "-"
            if "BUY" in row_copy['Action']:
                if tk not in inventory_pool: inventory_pool[tk] = []
                inventory_pool[tk].append({'price': row_copy['Price'], 'shares': row_copy['Shares']})
                export_rows.append(row_copy)
            elif "SELL" in row_copy['Action']:
                if tk in inventory_pool and inventory_pool[tk]:
                    matched_buy = inventory_pool[tk][0]
                    cost_basis = matched_buy['price']
                    abs_pnl = (row_copy['Price'] - cost_basis) * row_copy['Shares']
                    pct_roi = ((row_copy['Price'] - cost_basis) / cost_basis) * 100
                    row_copy['Realized PnL'] = f"${abs_pnl:.2f}"
                    row_copy['PnL ROI (%)'] = f"{pct_roi:.2f}%"
                    if row_copy['Shares'] >= matched_buy['shares']: inventory_pool[tk].pop(0)
                export_rows.append(row_copy)
        raw_export_df = pd.DataFrame(export_rows).iloc[::-1]
        if 'Action' in raw_export_df.columns:
            raw_export_df['Action'] = raw_export_df['Action'].astype(str).str.replace("🔵 ", "", regex=False).str.replace("🔴 ", "", regex=False)
        if 'Setup Catalyst' in raw_export_df.columns:
            raw_export_df['Setup Catalyst'] = raw_export_df['Setup Catalyst'].astype(str).str.replace("🌟 ", "", regex=False).str.replace("🟩 ", "", regex=False).str.replace("📐 ", "", regex=False).str.replace("📈 ", "", regex=False).str.replace("🟢 ", "", regex=False).str.replace("⏱️ ", "", regex=False)
        if 'Price' in raw_export_df.columns: raw_export_df['Price'] = raw_export_df['Price'].apply(lambda x: f"${float(x):.2f}")
        if 'Total (Local)' in raw_export_df.columns: raw_export_df['Total (Local)'] = raw_export_df['Total (Local)'].apply(lambda x: f"${float(x):.2f}")
        csv_buffer = raw_export_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 Export Ledger to Excel (.CSV)", data=csv_buffer, file_name=f"mikes_trading_journal_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width="stretch")
    else: st.button("📥 Export Ledger to Excel (.CSV)", disabled=True, use_container_width="stretch")
# ==============================================================================
# MIKE'S SHARE MARKET DASHBOARD: TRADING LEDGER FORMS (PART 4C - BLOCK 3)
# ==============================================================================
with st.expander("➕ Log a New Trade Execution Entry", expanded=False):
    form_col1, form_col2, form_col3 = st.columns(3)
    with form_col1:
        log_ticker = st.text_input("Ticker Symbol", value="AAPL", placeholder="E.g., AAPL, TSLA", key="journal_ticker_input").upper().strip()
        log_type = st.selectbox("Action Type", options=["🔵 BUY / ENTRY", "🔴 SELL / EXIT"], key="journal_type")
        log_date = st.date_input("Execution Date", datetime.now(), key="journal_date_input")
    with form_col2:
        log_shares = st.number_input("Shares Transacted", min_value=0.0000, value=0.0000, step=0.0001, format="%.4f", key="journal_shares_input")
        log_price = st.number_input("Execution Price ($)", min_value=0.00, value=0.00, step=0.01, format="%.2f", key="journal_price_input")
    with form_col3:
        log_catalyst = st.selectbox("Indicator Setup Catalyst", options=["🌟 STRONG BUY Ruleset Match", "🟩 Bullish Long MA Crossover", "📐 Chandelier Trailing Floor Invalidation", "📈 RSI Overbought Profit Scale-Out", "🟢 RSI Oversold Bounce Entry", "⏱️ Manual Discretionary Trade"], key="journal_cat_input")
        log_notes = st.text_area("Session Observations / Compliance Notes", placeholder="E.g., Followed 2x ATR rule cushion perfectly.", key="journal_notes_input")
    if st.button("🚀 Commit Execution to Local Database", use_container_width="stretch"):
        if log_shares <= 0 or log_price <= 0: st.error("❌ Submission Denied: Shares and Price must be greater than zero.")
        else:
            new_log_entry = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Ticker": log_ticker, "Action": log_type, "Date": log_date.strftime("%Y-%m-%d"), "Shares": float(log_shares), "Price": float(log_price), "Total (Local)": float(log_shares * log_price), "Setup Catalyst": log_catalyst, "Notes": log_notes}
            current_journal.append(new_log_entry)
            save_trading_journal(current_journal)
            st.success(f"✅ Successfully logged execution for {log_ticker}!")
            st.rerun()

processed_display_rows, running_career_pnl, inventory_buy_pool = [], 0.0, {}
for row in sorted(current_journal, key=lambda x: x['Date']):
    row_copy = row.copy()
    ticker = row_copy['Ticker']
    row_copy['Realized PnL ($)'] = "-"
    row_copy['PnL ROI (%)'] = "-"
    if "BUY" in row_copy['Action']:
        if ticker not in inventory_buy_pool: inventory_buy_pool[ticker] = []
        inventory_buy_pool[ticker].append({'price': row_copy['Price'], 'shares': row_copy['Shares']})
        processed_display_rows.append(row_copy)
    elif "SELL" in row_copy['Action']:
        if ticker in inventory_buy_pool and inventory_buy_pool[ticker]:
            matched_buy_event = inventory_buy_pool[ticker]
            cost_basis_per_share = matched_buy_event['price']
            absolute_pnl = (row_copy['Price'] - cost_basis_per_share) * row_copy['Shares']
            pnl_percentage_efficiency = ((row_copy['Price'] - cost_basis_per_share) / cost_basis_per_share) * 100
            row_copy['Realized PnL ($)'] = f"${absolute_pnl:,.2f}"
            row_copy['PnL ROI (%)'] = f"{pnl_percentage_efficiency:.2f}%"
            running_career_pnl += absolute_pnl
            if row_copy['Shares'] >= matched_buy_event['shares']: inventory_buy_pool[ticker].pop(0)
        processed_display_rows.append(row_copy)

st.markdown("<p class='small-header'>📋 Live Execution Ledger & Profit Reconciliations</p>", unsafe_allow_html=True)
if processed_display_rows:
    display_df = pd.DataFrame(processed_display_rows).iloc[::-1]
    st.dataframe(display_df, use_container_width="stretch", hide_index=True, column_config={"Shares": st.column_config.NumberColumn(format="%.4f"), "Price": st.column_config.NumberColumn(format="$%.2f"), "Total (Local)": st.column_config.NumberColumn(format="$%.2f"), "Realized PnL ($)": st.column_config.TextColumn("Realized PnL ($)"), "PnL ROI (%)": st.column_config.TextColumn("PnL ROI (%)")})
    pnl_banner_color = "#28a745" if running_career_pnl >= 0 else "#dc3545"
    pnl_sign_symbol = "+" if running_career_pnl >= 0 else ""
    st.markdown(f"""<div style='background-color: #1A1E24; padding: 10px; border-radius: 4px; border-right: 5px solid {pnl_banner_color}; font-size: 1.05rem; font-weight: bold; color: #FFFFFF;'>📈 Cumulative Career Ledger Trading Performance: <span style='color: {pnl_banner_color};'>{pnl_sign_symbol}${running_career_pnl:,.2f} USD Total Realized Cash Velocity</span></div>""", unsafe_allow_html=True)
else: st.info("💡 Your trading journal database is empty. Add entries above to construct historical accounting lines.")
