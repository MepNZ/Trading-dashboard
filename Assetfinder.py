import streamlit as st
import pandas as pd
import numpy as np
import math
import yfinance as yf
import altair as alt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import json
import warnings
import requests
import base64

def load_from_github(filename):
    # Local-first fallback for local testing to bypass network delays
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    try:
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://github.com{st.secrets['GITHUB_REPO']}/contents/{filename}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]).decode())
    except:
        pass
    return {}

def save_to_github(filename, data):
    # Local-first fallback to write instantly to disk without hitting Github API
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except:
        pass
        
    try:
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://github.com{st.secrets['GITHUB_REPO']}/contents/{filename}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None
        payload = {
            "message": f"Update {filename} from Streamlit Cloud",
            "content": base64.b64encode(json.dumps(data, indent=4).encode()).decode()
        }
        if sha: payload["sha"] = sha
        requests.put(url, headers=headers, json=payload)
    except:
        pass

warnings.filterwarnings('ignore')

# =============================================================================
# 1. WINDOW SETUP & LIGHT-THEME STYLING
# =============================================================================
st.set_page_config(
    page_title="Asset Finder",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .block-container { padding-top: 2.5rem !important; padding-bottom: 0.5rem !important; max-width: 100% !important; }
        div[data-testid="stTitle"] { margin-top: -20px !important; margin-bottom: -10px !important; }
        h1 { font-size: 2.0rem !important; font-weight: 800 !important; color: #111111 !important; }
        .small-header { font-size: 1.25rem !important; font-weight: bold !important; color: #007bff !important; margin-bottom: 4px !important; }
        
        div[data-testid="stDataFrame"] *, 
        div[data-testid="stDataFrame"] [role="columnheader"] span,
        div[data-testid="stDataFrame"] div {
            color: #111111 !important;
            font-weight: 600 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("💼 Financial Asset Discovery Dashboard")

# --- CLEAN HEADER CONTROLS AND TIMESTAMP ---
col_btn, col_time = st.columns([1, 4])

with col_btn:
    if st.button("🔄 Force Refresh Data", use_container_width=False):
        st.cache_data.clear()
        st.rerun()

with col_time:
    st.markdown(
        f"<p style='color: #666; margin-top: 6px; font-size: 14px; text-align: left;'> "
        f"📅 <b>Last Market Scan:</b> {pd.Timestamp.now().strftime('%d-%m-%Y %I:%M:%S %p')}"
        f"</p>", 
        unsafe_allow_html=True
    )
st.markdown("---")

TARGETS_FILE = "discovery_targets.json"

if "disk_memory" not in st.session_state:
    st.session_state.disk_memory = load_from_github(TARGETS_FILE)

if "watchlist_positions" not in st.session_state.disk_memory:
    st.session_state.disk_memory["watchlist_positions"] = {}
# =============================================================================
# 2. DICTIONARY MAPPING FOR COMPLETE TICKER DATASET
# =============================================================================
def load_company_names_matrix():
    json_path = "master_tickers.json"
    csv_path = "ticker_names.csv"
    
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    if os.path.exists(csv_path):
        try:
            m_df = pd.read_csv(csv_path, encoding='latin-1')
            m_df.columns = m_df.columns.astype(str).str.strip()
            
            t_col = 'Ticker' if 'Ticker' in m_df.columns else m_df.columns
            n_col = 'True_Name' if 'True_Name' in m_df.columns else m_df.columns
            
            csv_data = {}
            for _, row in m_df.iterrows():
                ticker_key = str(row[t_col]).strip().upper()
                name_val = str(row[n_col]).strip()
                csv_data[ticker_key] = name_val
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(csv_data, f, indent=4)
                
            return csv_data
        except Exception:
            pass
            
    return {}
# =============================================================================
# 3. HIGH-SPEED CHUNKED LIVE DATA DOWNLOAD LAYER
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_single_chunk_cached(chunk_list, lookback_date):
    try:
        chunk_data = yf.download(chunk_list, start=lookback_date, progress=False, group_by='ticker')
        if not chunk_data.empty:
            if isinstance(chunk_list, str):
                t_name = chunk_list.strip().upper()
            elif isinstance(chunk_list, list) and len(chunk_list) > 0:
                t_name = str(chunk_list).strip().upper()
            else:
                t_name = "ASSET"

            if isinstance(chunk_list, str) or len(chunk_list) == 1:
                chunk_data.columns = [f"{col}_{t_name}" for col in chunk_data.columns]
                return chunk_data
            
            if isinstance(chunk_data.columns, pd.MultiIndex):
                new_cols = [f"{item}_{ticker}" if item in ['Open', 'High', 'Low', 'Close', 'Volume'] else f"{ticker}_{item}" for item, ticker in chunk_data.columns.values]
                chunk_data.columns = new_cols
            else:
                chunk_data.columns = [f"{c}_{t_name}" for c in chunk_data.columns]
            return chunk_data
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_fundamentals(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            "pe": info.get('trailingPE', None),
            "income": info.get('netIncomeToCommon', None)
        }
    except:
        return {"pe": None, "income": None}

def fetch_live_market_data(tickers, days_lookback):
    if not tickers:
        return pd.DataFrame()
        
    lookback_start = datetime.today() - timedelta(days=days_lookback)
    chunk_size = 50
    ticker_chunks = [tickers[i:i + chunk_size] for i in range(0, len(tickers), chunk_size)]
    
    master_frames = []
    progress_bar = st.progress(0, text="📥 Ingesting live market data arrays...")
    
    for idx, chunk in enumerate(ticker_chunks):
        chunk_df = fetch_single_chunk_cached(chunk, lookback_start)
        if not chunk_df.empty:
            master_frames.append(chunk_df)
            
        progress_pct = int(((idx + 1) / len(ticker_chunks)) * 100)
        progress_bar.progress(progress_pct, text=f"📥 Loaded {min((idx+1)*chunk_size, len(tickers))} of {len(tickers)} assets...")
    
    progress_bar.empty()
    if not master_frames:
        return pd.DataFrame()
        
    return pd.concat(master_frames, axis=1).ffill().bfill()
# =============================================================================
# 4. UPGRADED BREAKOUT ALGORITHMS & DYNAMIC TIME-AWARE SCORE ENGINE
# =============================================================================
def calculate_momentum_matrix(raw_batch, tickers, fast_ma, slow_ma, min_stars, min_vol_multiple, show_bears, require_positive_income, max_pe_hurdle):
    if raw_batch.empty: 
        return []
    disk_names = load_company_names_matrix()
    b_rows = []
    f_ma_int, s_ma_int = int(fast_ma), int(slow_ma)
    
    for ticker in tickers:
        try:
            open_col = f"Open_{ticker}" if f"Open_{ticker}" in raw_batch.columns else 'Open'
            high_col = f"High_{ticker}" if f"High_{ticker}" in raw_batch.columns else 'High'
            low_col = f"Low_{ticker}" if f"Low_{ticker}" in raw_batch.columns else 'Low'
            close_col = f"Close_{ticker}" if f"Close_{ticker}" in raw_batch.columns else 'Close'
            vol_col = f"Volume_{ticker}" if f"Volume_{ticker}" in raw_batch.columns else 'Volume'
            
            if close_col not in raw_batch.columns:
                continue
                
            df = pd.DataFrame({
                'Open': raw_batch[open_col], 'High': raw_batch[high_col],
                'Low': raw_batch[low_col], 'Close': raw_batch[close_col], 'Volume': raw_batch[vol_col]
            }).ffill().bfill().dropna(subset=['Close'])
            
            if len(df) < max(s_ma_int, 25): 
                continue
                
            df['Fast_MA'] = df['Close'].rolling(window=f_ma_int, min_periods=1).mean()
            df['Slow_MA'] = df['Close'].rolling(window=s_ma_int, min_periods=1).mean()
            
            tr1 = df['High'] - df['Low']
            tr2 = (df['High'] - df['Close'].shift(1)).abs()
            tr3 = (df['Low'] - df['Close'].shift(1)).abs()
            df['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            df['Avg_Vol_20D'] = df['Volume'].shift(1).rolling(window=20, min_periods=1).mean()
            df['ATR'] = df['TR'].rolling(window=14, min_periods=1).mean()
            
            delta = df['Close'].diff()
            gain = delta.clip(lower=0).rolling(window=14, min_periods=1).mean()
            loss = (-delta.clip(upper=0)).rolling(window=14, min_periods=1).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)))).fillna(50)
            
            c_today, f_today, s_today = float(df['Close'].iloc[-1]), float(df['Fast_MA'].iloc[-1]), float(df['Slow_MA'].iloc[-1])
            c_yest = float(df['Close'].iloc[-2])
            
            pct_change = ((c_today - c_yest) / c_yest) * 100
            current_volume = int(df['Volume'].iloc[-1])
            rsi_val = float(df['RSI'].iloc[-1])
            atr_val = float(df['ATR'].iloc[-1]) if not np.isnan(df['ATR'].iloc[-1]) else (c_today * 0.02)
            
            market_label = "NZ" if ticker.endswith(".NZ") else ("AUS" if ticker.endswith(".AX") else "US")
            resolved_name = disk_names.get(ticker, f"{ticker}")
            
            safe_daily_limit_target = round((c_today - (0.50 * atr_val)) * 0.981, 2)
            safe_take_profit_target = round((safe_daily_limit_target + (2.0 * atr_val)) * 1.019, 2)

            avg_volume_20d = float(df['Avg_Vol_20D'].iloc[-1]) if df['Avg_Vol_20D'].iloc[-1] > 0 else 1.0
            volume_multiple = current_volume / avg_volume_20d

            if market_label == "US":
                ny_now = datetime.now(ZoneInfo("America/New_York"))
                is_us_open = (ny_now.weekday() < 5) and (ny_now.hour > 9 or (ny_now.hour == 9 and ny_now.minute >= 30)) and (ny_now.hour < 16)
                if is_us_open:
                    historical_avg = float(df['Avg_Vol_20D'].iloc[-2]) if df['Avg_Vol_20D'].iloc[-2] > 0 else 1.0
                    volume_multiple = float(df['Volume'].iloc[-2]) / historical_avg

            is_near_fast_ma = abs(c_today - f_today) / f_today <= 0.015

            if c_today > f_today and c_today > s_today:
                if is_near_fast_ma and c_today >= f_today:
                    breakout_signal = "🔵 FAST MA PULLBACK (Retest Entry)"
                else:
                    breakout_signal = "🟩 DUAL-TREND BREAKOUT"
            elif c_today > f_today and c_today <= s_today:
                if volume_multiple >= 1.1:
                    breakout_signal = "🟡 PRE-BREAKOUT: Turning Bullish (High Vol)"
                else:
                    breakout_signal = "⚡ PRE-BREAKOUT: Turning Bullish (Low Vol)"
            else:
                breakout_signal = "🔴 Structural Bear"

            stars = 0
            if c_today > f_today: stars += 1
            if c_today > s_today: stars += 1
            if volume_multiple >= 1.5: stars += 1
            if 45 <= rsi_val <= 68: stars += 1
            if pct_change > 0: stars += 1
            star_rating = "⭐" * stars if stars > 0 else "❌"

            if not show_bears and breakout_signal == "🔴 Structural Bear": continue
            if volume_multiple < min_vol_multiple: continue
            if stars < min_stars: continue

            fundamentals = get_cached_fundamentals(ticker)
            trailing_pe = fundamentals["pe"]
            net_income = fundamentals["income"]

            if require_positive_income and net_income is not None and net_income <= 0: continue
            if trailing_pe is not None and trailing_pe > max_pe_hurdle: continue

            b_rows.append({
                "Market": market_label, "Ticker": ticker, "Company Name": resolved_name, 
                "Alert Status": breakout_signal, "Score": star_rating, "Live Price": c_today, 
                "Limit Entry Target": safe_daily_limit_target, "Take Profit Target": safe_take_profit_target, 
                "Vol Multiple": volume_multiple, "ATR Risk": atr_val, "Daily Change %": pct_change, "RSI Momentum": rsi_val,
                "Trailing PE": trailing_pe if trailing_pe is not None else np.nan,  
                "Net Income": net_income if net_income is not None else np.nan     
            })
        except: 
            continue
    return b_rows
# =============================================================================
# 5. USER PREFERENCE SIDEBAR CONTROLS
# =============================================================================
with st.sidebar:
    st.markdown("### 🌐 Market Universe Horizon")
    market_choice = st.multiselect("Select Active Trading Horizons:", options=["US", "NZ", "AUS"], default=["US", "NZ", "AUS"])
    include_all_us = st.checkbox("Load Extended S&P 500 (Remaining 403 Stocks)", value=False)

    st.markdown("---")
    st.markdown("### 📅 Financial History Timescale")
    time_frame_map = {"1 Week": 7, "1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365, "2 Years": 730}
    selected_timeframe = st.select_slider("Select Analysis Lookback Range:", options=list(time_frame_map.keys()), value="1 Year")
    days_lookback_value = time_frame_map[selected_timeframe]

    st.markdown("---")
    st.markdown("### 🛠 Technical Settings Layer")
    fast_ma_slider = st.slider("Fast MA Filter Window:", min_value=5, max_value=30, value=10, step=1)
    slow_ma_slider = st.slider("Slow MA Filter Window:", min_value=20, max_value=150, value=50, step=5)
    
    st.markdown("---")
    st.markdown("### 🎯 Display Filters")
    show_bears = st.checkbox("Include Structural Bears in Matrix", value=False)
    min_vol_multiple = st.slider("Minimum Vol Multiple Filter:", min_value=0.0, max_value=5.0, value=1.3, step=0.1, format="%.1fx")
    min_stars = st.slider("Minimum Confluence Rating (Stars):", min_value=0, max_value=5, value=3, step=1, format="%d ⭐")
    
    signal_filter = st.multiselect(
        "Filter Matrix by Specific Signals:",
        options=[
            "🟩 DUAL-TREND BREAKOUT", 
            "🔵 FAST MA PULLBACK (Retest Entry)", 
            "🟡 PRE-BREAKOUT: Turning Bullish (High Vol)",
            "⚡ PRE-BREAKOUT: Turning Bullish (Low Vol)"
        ],
        default=[
            "🟩 DUAL-TREND BREAKOUT", 
            "🔵 FAST MA PULLBACK (Retest Entry)", 
            "🟡 PRE-BREAKOUT: Turning Bullish (High Vol)"
        ]
    )
    st.markdown("---")
    st.markdown("### 💸 Price Restrictions")
    max_price_filter = st.slider("Maximum Live Price to Display:", min_value=5, max_value=2000, value=2000, step=5, format="$%d")
    
    st.markdown("---")
    st.markdown("### 📊 Fundamental Health Layer")
    require_positive_income = st.checkbox("Enforce Positive Net Income (12M)", value=True, key="sb_income")
    max_pe_hurdle = st.slider("Maximum Allowed Trailing P/E:", min_value=5, max_value=100, value=40, step=5, format="%d×", key="sb_pe")
# STATE CONTROLLER ENGINE
csv_path = "ticker_names.csv"
ticker_universe = []
disk_names = load_company_names_matrix()

if os.path.exists(csv_path):
    try:
        m_df = pd.read_csv(csv_path, encoding='latin-1')
        m_df.columns = m_df.columns.astype(str).str.strip()
        m_df['Market'] = m_df['Market'].astype(str).str.strip().str.upper()
        
        us_assets = m_df[m_df['Market'] == 'US']
        nz_assets = m_df[m_df['Market'] == 'NZ']
        aus_assets = m_df[m_df['Market'] == 'AUS']
        
        if "US" in market_choice:
            if include_all_us: ticker_universe.extend(us_assets['Ticker'].astype(str).str.strip().str.upper().tolist())
            else: ticker_universe.extend(us_assets.head(100)['Ticker'].astype(str).str.strip().str.upper().tolist())
        if "NZ" in market_choice: ticker_universe.extend(nz_assets['Ticker'].astype(str).str.strip().str.upper().tolist())
        if "AUS" in market_choice: ticker_universe.extend(aus_assets['Ticker'].astype(str).str.strip().str.upper().tolist())
    except Exception as parse_error:
        st.sidebar.error(f"Source file routing error: {str(parse_error)}")

if not ticker_universe: ticker_universe = ["AAPL", "NVDA"]
ticker_universe = list(dict.fromkeys(ticker_universe))

@st.cache_data(ttl=300, show_spinner=False)
def get_immutable_market_snapshot(universe, lookback_days):
    return fetch_live_market_data(universe, lookback_days)

if "ticker_universe" in locals() or "ticker_universe" in globals():
    raw_market_snapshot = get_immutable_market_snapshot(ticker_universe, days_lookback_value)
    
    raw_breakouts = calculate_momentum_matrix(
        raw_market_snapshot, 
        ticker_universe, 
        fast_ma_slider, 
        slow_ma_slider, 
        min_stars, 
        min_vol_multiple, 
        show_bears, 
        require_positive_income, 
        max_pe_hurdle
    )

absolute_max_price = max(math.ceil(max([row["Live Price"] for row in raw_breakouts])) if raw_breakouts else 1000, 500)

# =============================================================================
# 6. INSTANT DATA SCREENER GRID VIEW
# =============================================================================
# HIGH-SPEED PATCH: Cache calculations so selecting items does NOT trigger a 30-second delay
@st.cache_data(ttl=300, show_spinner=False)
def get_cached_breakouts_matrix(snapshot_df, universe, f_ma, s_ma, stars, vol_mult, bears, inc_chk, pe_chk):
    return calculate_momentum_matrix(snapshot_df, universe, f_ma, s_ma, stars, vol_mult, bears, inc_chk, pe_chk)

if "ticker_universe" in locals() or "ticker_universe" in globals():
    raw_market_snapshot = get_immutable_market_snapshot(ticker_universe, days_lookback_value)
    
    raw_breakouts = get_cached_breakouts_matrix(
        raw_market_snapshot, 
        ticker_universe, 
        fast_ma_slider, 
        slow_ma_slider, 
        min_stars, 
        min_vol_multiple, 
        show_bears, 
        require_positive_income, 
        max_pe_hurdle
    )

absolute_max_price = max(math.ceil(max([row["Live Price"] for row in raw_breakouts])) if raw_breakouts else 1000, 500)

df_grid = pd.DataFrame()
if raw_breakouts:
    df_grid = pd.DataFrame(raw_breakouts)
    df_grid = df_grid[df_grid["Market"].isin(market_choice)]
    
    if signal_filter:
        df_grid = df_grid[df_grid["Alert Status"].isin(signal_filter)]
    
    if not show_bears: df_grid = df_grid[df_grid["Alert Status"] != "🔴 Structural Bear"]
    df_grid = df_grid[(df_grid["Live Price"] <= max_price_filter) & (df_grid["Vol Multiple"] >= min_vol_multiple)]
    
    df_grid["Star_Count"] = df_grid["Score"].apply(lambda x: len(x) if x != "❌" else 0)
    df_grid = df_grid[df_grid["Star_Count"] >= min_stars].drop(columns=["Star_Count"])
    
    if not df_grid.empty:
        df_grid = df_grid.sort_values(by=["Vol Multiple"], ascending=False)
        cols_order = ["Market", "Ticker", "Company Name", "Alert Status", "Score", "Live Price", "Limit Entry Target", "Take Profit Target", "Vol Multiple", "ATR Risk", "Daily Change %", "RSI Momentum", "Trailing PE", "Net Income"]
        df_grid = df_grid[[c for c in cols_order if c in df_grid.columns]]
        df_grid.columns = ["Market", "Ticker", "Asset Name", "System Status", "Confluence", "Price", "Limit Entry", "Take Profit", "RVOL", "ATR Risk", "Daily %", "RSI", "P/E", "Net Income"]

        df_display = df_grid.copy()
        df_display["Price"] = df_display["Price"].map("${:,.2f}".format)
        df_display["Limit Entry"] = df_display["Limit Entry"].map("${:,.2f}".format)
        df_display["Take Profit"] = df_display["Take Profit"].map("${:,.2f}".format)
        df_display["RVOL"] = df_display["RVOL"].apply(lambda x: f"🟢 {x:.2f}x" if x >= 1.50 else f"⚪ {x:.2f}x")
        df_display["ATR Risk"] = df_display["ATR Risk"].map("${:,.2f}".format)
        df_display["Daily %"] = df_display["Daily %"].apply(lambda x: f"🟢 {x:+.2f}%" if x >= 3.00 else f"⚪ {x:+.2f}%")
        df_display["RSI"] = df_display["RSI"].apply(lambda x: f"🔴 {x:.1f}" if x >= 68.0 else f"⚪ {x:.1f}")

        html_table = df_display.to_html(index=False, escape=False, table_id="interactive-screener")
        screener_combined_html = f"""<style>body {{ margin: 0; padding: 0; background-color: transparent; }} .scroll-window {{ max-height: 450px; overflow-y: auto !important; overflow-x: auto !important; border: 1px solid #D1D5DB; }} #interactive-screener {{ width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #FFFFFF !important; }} #interactive-screener th {{ position: -webkit-sticky !important; position: sticky !important; top: 0 !important; z-index: 10 !important; background-color: #E5E7EB !important; color: #111111 !important; font-size: 1.00rem !important; font-weight: bold !important; padding: 0px 12px !important; height: 90px !important; display: table-cell !important; vertical-align: middle !important; line-height: 90px !important; text-align: left; border-bottom: 3px solid #007bff !important; white-space: nowrap !important; cursor: pointer; user-select: none; }} #interactive-screener th::after {{ content: " ↕"; font-size: 0.8rem; color: #888; padding-left: 5px; display: inline-block !important; vertical-align: middle !important; line-height: normal !important; }} #interactive-screener td {{ color: #222222 !important; font-size: 0.95rem !important; padding: 12px 12px !important; border-bottom: 1px solid #E5E7EB !important; white-space: nowrap !important; }} #interactive-screener tr:nth-child(even) {{ background-color: #F9FAFB !important; }} #interactive-screener tr:hover {{ background-color: #F3F4F6 !important; }}</style><div class='scroll-window'>{html_table}</div><script>document.querySelectorAll("#interactive-screener th").forEach((header, index) => {{ header.addEventListener("click", () => {{ const table = document.getElementById("interactive-screener"); const tbody = table.querySelector("tbody"); const rows = Array.from(tbody.querySelectorAll("tr")); const isAscending = header.classList.contains("sort-asc"); table.querySelectorAll("th").forEach(th => th.classList.remove("sort-asc", "sort-desc")); rows.sort((rowA, rowB) => {{ let cellA = rowA.children[index].textContent.replace(/[\\$,%x\\s]/g, "").trim().replace(/🟢/g, "").trim(); let cellB = rowB.children[index].textContent.replace(/[\\$,%x\\s]/g, "").trim().replace(/🟢/g, "").trim(); const numA = parseFloat(cellA); const numB = parseFloat(cellB); if (!isNaN(numA) && !isNaN(numB)) return isAscending ? numB - numA : numA - numB; return isAscending ? cellB.localeCompare(cellA) : cellA.localeCompare(cellB); }}); header.classList.toggle("sort-asc", !isAscending); header.classList.toggle("sort-desc", isAscending); rows.forEach(row => tbody.appendChild(row)); }}); }});</script>"""
        st.components.v1.html(screener_combined_html, height=500, scrolling=False)

# =============================================================================
# 7. PERSISTENT LIVE WATCHLIST LAYOUT WITH ROW SELECTION DELETION
# =============================================================================
st.markdown("---")
st.markdown("<div class='small-header'>📋 Layer E: Persistent Live Watchlist Deck</div>", unsafe_allow_html=True)

all_discoverable_tickers = [row["Ticker"] for row in raw_breakouts] if 'raw_breakouts' in locals() else []
watch_col1, watch_col2 = st.columns([1, 2])

with watch_col1:
    st.markdown("##### Batch-Add Assets")
    selected_batch_tickers = st.multiselect(
        "Select Assets from Active Screener Output Matrix:", 
        options=all_discoverable_tickers, 
        key="wl_batch_select_key"
    )
    
    if st.button("➕ LOCK QUEUED ASSETS TO WATCHLIST", use_container_width=True):
        if selected_batch_tickers:
            write_occurred = False
            
            # OPTIMIZATION A: Create a lightning-fast O(1) dictionary look-up array out of your initial calculation matrix
            screener_lookup = {row["Ticker"]: row for row in raw_breakouts} if 'raw_breakouts' in locals() else {}
            
            for target_code in selected_batch_tickers:
                target_code = target_code.strip().upper()
                if target_code in st.session_state.disk_memory["watchlist_positions"]:
                    continue
                
                # Check the cached list instantly
                if target_code in screener_lookup:
                    matched_item = screener_lookup[target_code]
                    st.session_state.disk_memory["watchlist_positions"][target_code] = {
                        "entry": float(matched_item["Live Price"]),
                        "asset_name": str(matched_item["Company Name"]),
                        "entry_date": pd.Timestamp.now().strftime('%d-%m-%Y')
                    }
                    write_occurred = True
                else:
                    st.error(f"❌ '{target_code}' properties could not be mapped out of initial memory cache arrays.")

            if write_occurred:
                # OPTIMIZATION B: Save instantly to local disk memory block, then run the slow GitHub write in the background
                import threading
                try:
                    with open(TARGETS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(st.session_state.disk_memory, f, indent=4)
                except:
                    pass
                
                # Spin up an asynchronous thread for GitHub so your Streamlit screen updates instantly
                threading.Thread(target=save_to_github, args=(TARGETS_FILE, st.session_state.disk_memory), daemon=True).start()
                
                st.toast(f"🚀 Locked batch assets successfully to Watchlist Deck!", icon="✅")
                st.rerun()
        else:
            st.warning("⚠️ Choose one or more valid stocks inside the selection queue box first.")
with watch_col2:
    st.markdown("##### Active Watchlist Matrix Rows")
    watchlist_grid_rows = []
            
    for wl_ticker, wl_meta in list(st.session_state.disk_memory["watchlist_positions"].items()):
        try:
            live_px, live_vol_str = None, "N/A"
            
            if 'raw_breakouts' in locals():
                matched_item = next((row for row in raw_breakouts if row["Ticker"] == wl_ticker), None)
                if matched_item:
                    live_px = float(matched_item["Live Price"])
                    live_vol_str = f"{matched_item['Vol Multiple']:.2f}x"

            if (live_px is None or live_vol_str == "N/A") and not raw_market_snapshot.empty:
                try:
                    clean_wl = wl_ticker.strip().upper()
                    close_col = f"Close_{clean_wl}" if f"Close_{clean_wl}" in raw_market_snapshot.columns else None
                    vol_col = f"Volume_{clean_wl}" if f"Volume_{clean_wl}" in raw_market_snapshot.columns else None
                    
                    if close_col and live_px is None:
                        live_px = float(raw_market_snapshot[close_col].dropna().iloc[-1])
                    if vol_col and live_vol_str == "N/A":
                        vol_val = float(raw_market_snapshot[vol_col].dropna().iloc[-1])
                        live_vol_str = f"{vol_val:,.0f}"
                except:
                    pass

            if live_px is None:
                live_px = float(wl_meta.get("entry", 1.00))
                
            fixed_entry_px = float(wl_meta.get("entry", live_px))
            currency_lbl = "USD" if not (wl_ticker.endswith(".NZ") or wl_ticker.endswith(".AX")) else ("AUD" if wl_ticker.endswith(".AX") else "NZD")
            roi_dollar = live_px - fixed_entry_px
            roi_percent = (roi_dollar / fixed_entry_px) * 100 if fixed_entry_px > 0 else 0.0
            
            watchlist_grid_rows.append({
                "Delete": False, 
                "Ticker": wl_ticker, 
                "Asset Name": wl_meta.get("asset_name", wl_ticker), 
                "Date Added": wl_meta.get("entry_date", "N/A"), 
                "Fixed Entry": f"${fixed_entry_px:,.2f} {currency_lbl}", 
                "Current Live": f"${live_px:,.2f} {currency_lbl}", 
                "Live Volume": live_vol_str, 
                "ROI ($)": f"+${roi_dollar:,.2f}" if roi_dollar >= 0 else f"-${abs(roi_dollar):,.2f}", 
                "ROI (%)": f"+{roi_percent:,.2f}%" if roi_dollar >= 0 else f"{roi_percent:,.2f}%"
            })
        except: 
            pass
            
    if watchlist_grid_rows:
        edited_wl_df = st.data_editor(pd.DataFrame(watchlist_grid_rows), use_container_width=True, hide_index=True, column_config={"Delete": st.column_config.CheckboxColumn(help="Select lines to drop")})
        dropped_tickers = edited_wl_df[edited_wl_df["Delete"] == True]["Ticker"].tolist()
        if dropped_tickers and st.button("🗑️ PURGE SELECTED WATCHLIST ROWS", use_container_width=True, type="secondary"):
            for t_drop in dropped_tickers:
                if t_drop in st.session_state.disk_memory["watchlist_positions"]: 
                    del st.session_state.disk_memory["watchlist_positions"][t_drop]
            save_to_github(TARGETS_FILE, st.session_state.disk_memory)
            st.toast("Dropped selected tracked entries.")
            st.rerun()
    else: 
        st.caption("Watchlist backend is currently empty.")

# =============================================================================
# 8. HIGH-SPEED LIGHTWEIGHT OVERLAY CHART
# =============================================================================
st.markdown("---")
st.markdown("<div class='small-header'>📈 Global Chart Engine Analytics Overlay</div>", unsafe_allow_html=True)
available_charts = list(dict.fromkeys([t for t in list(st.session_state.disk_memory["watchlist_positions"].keys()) if t]))

if available_charts:
    selected_ticker = st.radio("Select an Asset to View Moving Average Overlays:", options=available_charts, horizontal=True)
    if selected_ticker:
        try:
            chart_df = pd.DataFrame()
            target_sel = str(selected_ticker).strip().upper()
            
            # 1. Try to extract from the pre-loaded live market snapshot
            if not raw_market_snapshot.empty:
                target_col = f"Close_{target_sel}"
                if target_col in raw_market_snapshot.columns:
                    chart_df = pd.DataFrame({'Close': raw_market_snapshot[target_col].dropna()})

            # 2. Fall back to standalone download if snapshot didn't resolve it
            if chart_df.empty:
                downloaded_raw = yf.download(selected_ticker, start=datetime.now() - timedelta(days=days_lookback_value), progress=False)
                if not downloaded_raw.empty:
                    # Cleanly unnest potential MultiIndex headers from standalone yfinance
                    if isinstance(downloaded_raw.columns, pd.MultiIndex):
                        if 'Close' in downloaded_raw.columns.get_level_values(0):
                            extracted_series = downloaded_raw['Close']
                        elif 'Close' in downloaded_raw.columns.get_level_values(1):
                            extracted_series = downloaded_raw.xs('Close', axis=1, level=1)
                        else:
                            extracted_series = downloaded_raw.iloc[:, 0]
                    else:
                        extracted_series = downloaded_raw['Close'] if 'Close' in downloaded_raw.columns else downloaded_raw.iloc[:, 0]
                    
                    # FORCE TO A FLATTENED SERIES AND CLEAN ANY HIGHER LEVEL MULTIINDEX SCALARS
                    if isinstance(extracted_series, pd.DataFrame):
                        extracted_series = extracted_series.iloc[:, 0]
                        
                    chart_df = pd.DataFrame(extracted_series).rename(columns={extracted_series.name: 'Close'}).dropna()
    
            if not chart_df.empty:
                # Strictly force column names to standard flat strings to protect Altair rendering
                chart_df = chart_df.ffill().bfill()
                chart_df['Fast_MA_Line'] = chart_df['Close'].rolling(window=int(fast_ma_slider), min_periods=1).mean()
                chart_df['Slow_MA_Line'] = chart_df['Close'].rolling(window=int(slow_ma_slider), min_periods=1).mean()
                
                # Standarize Index to a plain text 'Date' column safely
                chart_df = chart_df.reset_index()
                if 'index' in chart_df.columns:
                    chart_df = chart_df.rename(columns={'index': 'Date'})
                elif 'Date' not in chart_df.columns:
                    chart_df.columns.values[0] = 'Date'
                    
                chart_df['Date'] = pd.to_datetime(chart_df['Date']).dt.strftime('%Y-%m-%d')
                chart_df.columns = [str(c) for c in chart_df.columns]
                
                # Plot the clean, flattened structures
                y_scale = alt.Scale(domain=[float(chart_df['Close'].min()) * 0.95, float(chart_df['Close'].max()) * 1.05], clamp=True)
                base = alt.Chart(chart_df).encode(x='Date:T').properties(height=300)
                st.altair_chart(alt.layer(
                    base.mark_line(color='#4A90E2', strokeWidth=3).encode(y=alt.Y('Close:Q', scale=y_scale, title="Price ($)")), 
                    base.mark_line(color='#00FF66', strokeWidth=2).encode(y='Fast_MA_Line:Q'), 
                    base.mark_line(color='#FF3333', strokeWidth=2).encode(y='Slow_MA_Line:Q')
                ), use_container_width=True)
                st.caption(f"🔵 Blue = Price | 🟢 Green = {fast_ma_slider}-Day Fast MA | 🔴 Red = {slow_ma_slider}-Day Slow MA")
            else:
                st.info("No historical pricing values available to display for this instrument.")
        except Exception as chart_err: 
            st.error(f"Error formatting chart analytics: {str(chart_err)}")
else: 
    st.info("Pin items into your tracking watchlist above to populate chart profiles.")
