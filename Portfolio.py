import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import altair as alt
from datetime import datetime, timedelta
import pytz
from zoneinfo import ZoneInfo
import warnings

warnings.filterwarnings('ignore')

# 1. Enforce wide-screen single dashboard orientation layout
st.set_page_config(
    page_title="Mike's Share Market Dashboard", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# 2. COMPLETE LIGHT-THEME STYLING INJECTION (REVISED FOR VISIBLE HEADERS)
# =============================================================================
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
        .block-container { padding-top: 2.5rem !important; padding-bottom: 1.0rem !important; }
        div[data-testid="stVerticalBlock"] > div { margin-top: 0px !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 16px !important; margin-bottom: 15px !important; }
        .stTabs [data-baseweb="tab-panel"] { padding-top: 10px !important; }
        
        /* 👑 STYLES ALL TABLES AND LEDGERS IN CRISP BLACK FOR ALL TEXT ELEMENTS */
        div[data-testid="stDataFrame"] *, 
        div[data-testid="stDataFrame"] [role="columnheader"] span,
        div[data-testid="stDataFrame"] div,
        div[data-testid="stTable"] *,
        .custom-grid th, .custom-grid td {
            color: #111111 !important;
            font-weight: 600 !important;
        }
        
        /* Forces the text inside table headers to remain bold and sharp */
        div[data-testid="stDataFrame"] [role="columnheader"] * {
            font-weight: bold !important;
            color: #111111 !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

TARGETS_FILE = "portfolio_targets.json"

# =============================================================================
# 3. HIGH-SPEED COMPANY NAME DICTIONARY MAPPING ENGINE (AUTO-JSON GENERATION)
# =============================================================================
def load_company_names():
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
            
            t_col = 'Ticker' if 'Ticker' in m_df.columns else m_df.columns[0]
            n_col = 'True_Name' if 'True_Name' in m_df.columns else m_df.columns[1]
            
            csv_data = {}
            for _, row in m_df.iterrows():
                ticker_key = str(row[t_col]).strip()
                name_val = str(row[n_col]).strip()
                csv_data[ticker_key.upper()] = name_val
                csv_data[ticker_key.lower()] = name_val
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(csv_data, f, indent=4)
                
            return csv_data
        except Exception:
            pass
            
    return {}

company_name_map = load_company_names()
# 4. Load Workspace json state files from local disk memory
disk_memory = {}
if os.path.exists(TARGETS_FILE):
    try:
        with open(TARGETS_FILE, 'r') as f: disk_memory = json.load(f)
    except Exception: pass

runtime_positions = disk_memory.get("positions", {})
runtime_watchlist = disk_memory.get("watchlist_tickers", [])
runtime_cash = disk_memory.get("wallet_cash", {"NZD": 14.52, "AUD": 0.00, "USD": 78.24})
runtime_sliders = disk_memory.get("sliders", {"fast_ma": 10, "slow_ma": 50, "roi_window": "1 Year"})
runtime_paper = disk_memory.get("paper_positions", {})

# 5. High-Speed Cached Concurrent Market Downloader Block
@st.cache_data(ttl=300)
def fetch_market_matrix_concurrent(tickers, lookback_days):
    if not tickers:
        return pd.DataFrame()
    start_date = datetime.now() - timedelta(days=lookback_days + 250)
    try:
        df = yf.download(tickers, start=start_date, interval="1d", group_by="ticker", progress=False)
        return df
    except Exception:
        return pd.DataFrame()

# 6. Live FX Rate Fetcher Engine Block
@st.cache_data(ttl=300)
def get_live_fx_rates():
    nzd_rate, aud_rate = 1.7540, 1.1000
    try:
        nzd_data = yf.download("NZD=X", period="1d", interval="1d", progress=False)
        if not nzd_data.empty:
            nzd_rate = float(nzd_data[('Close', 'NZD=X')].dropna().iloc[-1]) if isinstance(nzd_data.columns, pd.MultiIndex) else float(nzd_data['Close'].dropna().iloc[-1])
            if nzd_rate < 1.0: nzd_rate = 1.0 / nzd_rate
        
        aud_data = yf.download("AUDNZD=X", period="1d", interval="1d", progress=False)
        if not aud_data.empty:
            aud_rate = float(aud_data[('Close', 'AUDNZD=X')].dropna().iloc[-1]) if isinstance(aud_data.columns, pd.MultiIndex) else float(aud_data['Close'].dropna().iloc[-1])
    except: pass
    return nzd_rate, aud_rate

usd_to_nzd_rate, aud_to_nzd_rate = get_live_fx_rates()

# 7. Clean structural clocks tracking banner matching original layout specs
def get_exchange_status_badge(tz_name, open_hour=9, open_min=30, close_hour=16, close_min=0, is_nz_au=False):
    if is_nz_au: open_hour, open_min = 10, 0
    try:
        target_tz = pytz.timezone(tz_name)
        tz_now = datetime.now(target_tz)
        if tz_now.weekday() >= 5: return "<span style='color: #ef4444;'>CLOSED</span>"
        start_time = tz_now.replace(hour=open_hour, minute=open_min, second=0, microsecond=0)
        end_time = tz_now.replace(hour=close_hour, minute=close_min, second=0, microsecond=0)
        if start_time <= tz_now <= end_time: return "<span style='color: #22c55e;'>OPEN</span>"
        return "<span style='color: #ef4444;'>CLOSED</span>"
    except: return "CLOSED"

us_status = get_exchange_status_badge('America/New_York')
au_status = get_exchange_status_badge('Australia/Sydney', is_nz_au=True)
nz_status = get_exchange_status_badge('Pacific/Auckland', is_nz_au=True)
nz_now_time = datetime.now(ZoneInfo("Pacific/Auckland")).strftime("%d %b %Y, %I:%M %p %Z")

st.markdown(f"""
    <div style='background-color: #161A22; padding: 12px; border-radius: 6px; text-align: center; font-size: 1.08rem; font-weight: bold; border: 1px solid #2d3139; color: #FFFFFF;'>
        <span style='margin-right: 30px;'>🇺🇸 NYSE US: {us_status}</span>
        <span style='margin-right: 30px;'>🇦🇺 ASX AUS: {au_status}</span>
        <span style='margin-right: 30px;'>🇳🇿 NZX NZ: {nz_status}</span>
        <span style='color: #8B949E; margin-left: 20px; font-weight: normal; font-size: 0.95rem;'>🕒 Local: {nz_now_time}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
head_col1, head_col2 = st.columns(2)
with head_col1:
    st.markdown("### 🛠️ Live Workspace Control Desk")
with head_col2:
    save_trigger = st.button("💾 SAVE & SYNC WORKSPACE", type="primary", use_container_width=True)

control_tab1, control_tab2, control_tab3 = st.tabs(["⚙️ Parameters", "📐 Portfolio Slots", "🧪 Paper Trading"])

with control_tab1:
    c_col1, c_col2, c_col3 = st.columns(3)
    with c_col1:
        st.markdown("#### 🕒 Horizons")
        st.selectbox("Timeframe", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], index=3, key="roi_window")
        if st.button("🔄 Clear Cache Memory", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with c_col2:
        st.markdown("#### 📈 Analysis")
        st.slider("Fast Moving Average (MA)", 5, 30, int(runtime_sliders.get("fast_ma", 10)), key="fast_ma")
        st.slider("Slow Moving Average (MA)", 20, 200, int(runtime_sliders.get("slow_ma", 50)), key="slow_ma")
    
    with c_col3:
        st.markdown("#### 💼 Sharesies Vault (Available vs Pending)")
        
        # --- NZD Row ---
        nzd_left, nzd_right = st.columns(2)
        with nzd_left:
            cash_nzd = st.number_input("NZD $ Available", min_value=0.0, value=float(runtime_cash.get("NZD", 14.52)), step=1.0, format="%.2f", key="cash_nzd_input")
        with nzd_right:
            pending_nzd = st.number_input("NZD $ Pending", min_value=0.0, value=float(runtime_cash.get("Pending_NZD", 0.00)), step=1.0, format="%.2f", key="pending_nzd_input")
            
        # --- AUD Row ---
        aud_left, aud_right = st.columns(2)
        with aud_left:
            cash_aud = st.number_input("AUD $ Available", min_value=0.0, value=float(runtime_cash.get("AUD", 0.00)), step=1.0, format="%.2f", key="cash_aud_input")
        with aud_right:
            pending_aud = st.number_input("AUD $ Pending", min_value=0.0, value=float(runtime_cash.get("Pending_AUD", 0.00)), step=1.0, format="%.2f", key="pending_aud_input")
            
        # --- USD Row ---
        usd_left, usd_right = st.columns(2)
        with usd_left:
            cash_usd = st.number_input("USD $ Available", min_value=0.0, value=float(runtime_cash.get("USD", 78.24)), step=1.0, format="%.2f", key="cash_usd_input")
        with usd_right:
            pending_usd = st.number_input("USD $ Pending", min_value=0.0, value=float(runtime_cash.get("Pending_USD", 0.00)), step=1.0, format="%.2f", key="pending_usd_input")

portfolio_slots = list(runtime_positions.keys())[:6]
while len(portfolio_slots) < 6: portfolio_slots.append(f"EMPTY_PORT_{len(portfolio_slots)+1}")

with control_tab2:
    slot_cols = st.columns(3)
    for i in range(6):
        ticker = portfolio_slots[i]
        stored = runtime_positions.get(ticker, {}) if "EMPTY" not in ticker else {}
        display_label = ticker if "EMPTY" not in ticker else "Empty Slot"
        with slot_cols[i % 3]:
            with st.expander(f"Slot {i+1}: {display_label}", expanded=False):
                st.text_input(f"Ticker Symbol", value="" if "EMPTY" in ticker else ticker, key=f"port_slot_{i}")
                st.number_input("Shares Owned", min_value=0.0, value=float(stored.get("shares", 0.0)), step=0.01, format="%.4f", key=f"shares_{i}")
                st.number_input("Entry Cost", min_value=0.0, value=float(stored.get("entry", 0.0)), step=0.01, format="%.2f", key=f"entry_{i}")
                st.number_input("Upper Target", min_value=0.0, value=float(stored.get("upper", 0.0)), step=0.01, format="%.2f", key=f"up_{i}")
                st.number_input("Stop Distance", min_value=0.0, value=float(stored.get("fixed_stop_distance", 15.0)), step=0.5, format="%.2f", key=f"fixed_stop_{i}")

with control_tab3:
    paper_slots = list(runtime_paper.keys())[:6]
    while len(paper_slots) < 6: 
        paper_slots.append(f"EMPTY_PAPER_{len(paper_slots)+1}")
        
    paper_cols = st.columns(3)
    for i in range(6):
        p_ticker = paper_slots[i]
        
        # 🟢 FIX: Ensure empty state variables do not draw ghosts from memory
        if "EMPTY" in p_ticker:
            default_tk = ""
            default_ep = 0.0
            stored_date_str = None
        else:
            default_tk = p_ticker
            p_stored = runtime_paper.get(p_ticker, {})
            default_ep = float(p_stored.get("entry", 0.0))
            stored_date_str = p_stored.get("entry_date", None)
            
        try: 
            d_date = datetime.strptime(stored_date_str, "%Y-%m-%d").date() if stored_date_str else datetime.today().date()
        except: 
            d_date = datetime.today().date()
            
        with paper_cols[i % 3]:
            # Clean layout window header display resolution
            slot_header = f"Paper Slot {i+1}: {default_tk}" if default_tk else f"Paper Slot {i+1}: Empty"
            with st.expander(slot_header, expanded=False):
                st.text_input(f"Paper Ticker Symbol", value=default_tk, key=f"paper_slot_{i}")
                st.number_input("Paper Entry Price", min_value=0.0, value=default_ep, step=0.01, format="%.2f", key=f"paper_entry_{i}")
                st.date_input("Calendar Entry Date", value=d_date, key=f"paper_date_{i}")

if save_trigger:
    live_bounds = {
        "wallet_cash": {
            "NZD": cash_nzd, 
            "AUD": cash_aud, 
            "USD": cash_usd,
            "Pending_NZD": pending_nzd,
            "Pending_AUD": pending_aud,
            "Pending_USD": pending_usd
        },
        "sliders": {"fast_ma": int(st.session_state["fast_ma"]), "slow_ma": int(st.session_state["slow_ma"]), "roi_window": st.session_state["roi_window"]},
        "positions": {}, 
        "watchlist_tickers": runtime_watchlist, 
        "paper_positions": {}
    }

    # Process portfolio slots
    for idx in range(6):
        t_input = st.session_state.get(f"port_slot_{idx}", "").upper().strip()
        if t_input and "EMPTY" not in t_input and t_input != "":
            live_bounds["positions"][t_input] = {
                "shares": float(st.session_state.get(f"shares_{idx}", 0.0)), 
                "entry": float(st.session_state.get(f"entry_{idx}", 0.0)),
                "upper": float(st.session_state.get(f"up_{idx}", 0.0)), 
                "fixed_stop_distance": float(st.session_state.get(f"fixed_stop_{idx}", 15.0))
            }
            
    # Process paper trading slots with clear validation checks
    for idx in range(6):
        p_input = st.session_state.get(f"paper_slot_{idx}", "").upper().strip()
        if p_input and "EMPTY" not in p_input and p_input != "":
            p_date = st.session_state.get(f"paper_date_{idx}", datetime.today().date())
            live_bounds["paper_positions"][p_input] = {
                "shares": 1.0, 
                "entry": float(st.session_state.get(f"paper_entry_{idx}", 0.0)), 
                "entry_date": p_date.strftime("%Y-%m-%d")
            }
            
    # Commit changes cleanly to JSON disk state memory
    with open(TARGETS_FILE, 'w') as f: 
        json.dump(live_bounds, f, indent=4)
        
    st.cache_data.clear()
    st.rerun()

# 8. Core Sector Taxonomy Benchmarks List
sector_mapping_dictionary = {
    "SPY": "🇺🇸 S&P 500 Index", "XLK": "Technology", "XLY": "Consumer Discretionary", 
    "XLC": "Communication", "XLF": "Financials", "XLV": "Healthcare", 
    "XLP": "Consumer Staples", "XLI": "Industrials", 
    "XLB": "Materials", "XLU": "Utilities", "XLRE": "Real Estate"
}
asset_sector_tags = {
    "XLE": "🛢️ Energy Sector", "MDT": "🩺 Healthcare", "HAS": "🎯 Consumer Goods",
    "HGH.NZ": "🏢 Infrastructure", "NAB.AX": "🏦 Financials", "POT.NZ": "⚡ Utilities"
}

clean_portfolio_list = [t for t in runtime_positions.keys() if t and "EMPTY" not in t]
clean_paper_list = [t for t in runtime_paper.keys() if t and "EMPTY" not in t]
all_active_workspace_tickers = list(dict.fromkeys(clean_portfolio_list + clean_paper_list))
extended_fetching_tickers = list(set(all_active_workspace_tickers + list(sector_mapping_dictionary.keys())))

lookback_days_map = {"1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365, "2 Years": 730}
chosen_horizon = st.session_state.get("roi_window", "1 Year")
horizon_days = lookback_days_map.get(chosen_horizon, 365)

master_unified_rows, active_live_positions, operational_dfs, macro_sector_rows = [], [], {}, []

if extended_fetching_tickers:
    RAW_MARKET_BATCH = fetch_market_matrix_concurrent(extended_fetching_tickers, horizon_days)
else:
    RAW_MARKET_BATCH = pd.DataFrame()

if not RAW_MARKET_BATCH.empty:
    for ticker in extended_fetching_tickers:
        try:
            clean_ticker_key = str(ticker).strip().upper()
            if isinstance(RAW_MARKET_BATCH.columns, pd.MultiIndex):
                if ticker in RAW_MARKET_BATCH.columns.get_level_values(0):
                    df_t = RAW_MARKET_BATCH[ticker].copy()
                elif clean_ticker_key in RAW_MARKET_BATCH.columns.get_level_values(0):
                    df_t = RAW_MARKET_BATCH[clean_ticker_key].copy()
                else:
                    continue
            else:
                df_t = RAW_MARKET_BATCH.copy()
                
            df_t = df_t.ffill().bfill().dropna(subset=['Close'])
            if df_t.empty: continue

            df_t['Fast_MA'] = df_t['Close'].rolling(window=int(st.session_state["fast_ma"]), min_periods=1).mean()
            df_t['Slow_MA'] = df_t['Close'].rolling(window=int(st.session_state["slow_ma"]), min_periods=1).mean()
            
            if 'High' in df_t.columns and 'Low' in df_t.columns:
                df_t['True_Range'] = pd.concat([
                    (df_t['High'] - df_t['Low']), 
                    (df_t['High'] - df_t['Close'].shift(1)).abs(), 
                    (df_t['Low'] - df_t['Close'].shift(1)).abs()
                ], axis=1).max(axis=1)
            else:
                df_t['True_Range'] = df_t['Close'] * 0.02
                
            df_t['ATR'] = df_t['True_Range'].rolling(window=14, min_periods=1).mean()
            
            delta = df_t['Close'].diff()
            gain = delta.clip(lower=0).rolling(window=14, min_periods=1).mean()
            loss = (-delta.clip(upper=0)).rolling(window=14, min_periods=1).mean()
            df_t['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)))).fillna(50)
            
            operational_dfs[ticker] = df_t
            operational_dfs[clean_ticker_key] = df_t
            
            last_close = float(df_t['Close'].iloc[-1])
            rsi_val = float(df_t['RSI'].iloc[-1])
            
            if ticker in sector_mapping_dictionary:
                rsi_lbl = f"{rsi_val:.1f} Healthy"
                macro_sector_rows.append({
                    "Sector Symbol": ticker, "Sector Domain Name": sector_mapping_dictionary[ticker], 
                    "Closing Price": last_close, "RSI Status Value": rsi_val, "RSI Speedometer": rsi_lbl
                })
                continue
            
            fast_ma_val = float(df_t['Fast_MA'].iloc[-1])
            slow_ma_val = float(df_t['Slow_MA'].iloc[-1])
            atr_val = float(df_t['ATR'].iloc[-1]) if df_t['ATR'].iloc[-1] > 0 else (last_close * 0.02)
            
            safe_daily_limit_target = round((last_close - (0.50 * atr_val)) * 0.981, 2)
            safe_take_profit_target = round((safe_daily_limit_target + (2.0 * atr_val)) * 1.019, 2)
            resolved_name = company_name_map.get(clean_ticker_key, f"{ticker}")
            
            if last_close > fast_ma_val and last_close > slow_ma_val:
                strategy_status = "🟩 DUAL-TREND BREAKOUT"
            else:
                strategy_status = "🔴 Structural Bear"
            
            roi_cutoff = datetime.now() - timedelta(days=horizon_days)
            localized_cutoff = roi_cutoff.tz_localize(df_t.index.tz) if df_t.index.tz else roi_cutoff
            hist_sliced = df_t[df_t.index >= localized_cutoff]
            window_start_p = float(hist_sliced['Close'].iloc[0]) if not hist_sliced.empty else last_close
            ticker_roi = ((last_close - window_start_p) / window_start_p) * 100
            
                        # Calculate personal entry-based returns for Layer B tracking
            if ticker in clean_portfolio_list or clean_ticker_key in clean_portfolio_list:
                stored_block = runtime_positions.get(ticker, runtime_positions.get(clean_ticker_key, {}))
                entry_p_calc = float(stored_block.get("entry", 0.0))
                if entry_p_calc > 0.0:
                    ticker_roi = ((last_close - entry_p_calc) / entry_p_calc) * 100
                else:
                    ticker_roi = 0.0
            else:
                ticker_roi = 0.0
            
            if ticker in all_active_workspace_tickers or clean_ticker_key in all_active_workspace_tickers:
                master_unified_rows.append({
                    "Ticker": ticker, "Sector": asset_sector_tags.get(ticker, "Other"), "Asset Name": resolved_name, 
                    "Price": last_close, "Return": ticker_roi, "Limit Buy at": safe_daily_limit_target, 
                    "T/P Exit": safe_take_profit_target, "Status": strategy_status, "Fast MA": fast_ma_val, 
                    "Slow MA": slow_ma_val, "RSI": rsi_val, "ATR": atr_val
                })
                
            if ticker in clean_portfolio_list or clean_ticker_key in clean_portfolio_list:
                stored_block = runtime_positions.get(ticker, runtime_positions.get(clean_ticker_key, {}))
                shares_num = float(stored_block.get("shares", 0.0))
                entry_p = float(stored_block.get("entry", 0.0))
                
                if shares_num > 0:
                    cost_loc = shares_num * entry_p
                    currency_lbl = "USD" if not (ticker.endswith(".NZ") or ticker.endswith(".AX")) else ("AUD" if ticker.endswith(".AX") else "NZD")
                    mult = usd_to_nzd_rate if currency_lbl == "USD" else (aud_to_nzd_rate if currency_lbl == "AUD" else 1.0)
                    val_loc = shares_num * last_close
                    
                    active_live_positions.append({
                        "Ticker": ticker, "Asset Name": resolved_name, "Shares": shares_num, "Currency": currency_lbl,
                        "Bought at": entry_p, "Live price": last_close, "New Limit Buy": safe_daily_limit_target,   
                        "Take Profit": safe_take_profit_target, "Cost (Loc)": cost_loc, "Cost (NZD)": cost_loc * mult, 
                        "Value (Loc)": val_loc, "Value (NZD)": val_loc * mult, "Stop Loss": last_close - (2.0 * atr_val)
                    })
        except Exception:
            pass
st.markdown("#### 💼 Layer A: My Portfolio Ledger")
if active_live_positions:
    p_df = pd.DataFrame(active_live_positions)
    p_df["P&L (NZD)"] = p_df["Value (NZD)"] - p_df["Cost (NZD)"]
    p_df["ROI"] = (p_df["P&L (NZD)"] / p_df["Cost (NZD)"]) * 100
    
    cols_a = ["Ticker", "Asset Name", "Shares", "Currency", "Bought at", "Live price", 
              "New Limit Buy", "Take Profit", "Cost (Loc)", "Cost (NZD)", 
              "Value (Loc)", "Value (NZD)", "Stop Loss", "P&L (NZD)", "ROI"]
    
    tot_invest_nzd = p_df["Cost (NZD)"].sum()
    tot_equity_nzd = p_df["Value (NZD)"].sum()
    tot_profit_nzd = tot_equity_nzd - tot_invest_nzd
    tot_roi_nzd = (tot_profit_nzd / tot_invest_nzd) * 100 if tot_invest_nzd > 0 else 0.0
        # Calculate available and pending balances converted to native NZD
    available_cash_nzd = cash_nzd + (cash_aud * aud_to_nzd_rate) + (cash_usd * usd_to_nzd_rate)
    pending_cash_nzd = pending_nzd + (pending_aud * aud_to_nzd_rate) + (pending_usd * usd_to_nzd_rate)
    integ_cash_nzd = available_cash_nzd + pending_cash_nzd
    
    tot_app_value = tot_equity_nzd + integ_cash_nzd

    p_color, p_sign = ("#28a745", "+") if tot_profit_nzd >= 0 else ("#dc3545", "")
    
    currency_cols_a = ["Bought at", "Live price", "New Limit Buy", "Take Profit", "Cost (Loc)", "Cost (NZD)", "Value (Loc)", "Value (NZD)", "Stop Loss", "P&L (NZD)"]
    for col in currency_cols_a: p_df[col] = p_df[col].map("${:,.2f}".format)
    p_df["ROI"] = p_df["ROI"].map("{:,.2f}%".format)
    
    html_table_a = p_df[cols_a].to_html(index=False, escape=False, table_id="ledger-portfolio")
    
    ledger_a_css = """
    <style>
        .ledger-a-scroll-window { max-height: 400px; overflow-y: auto !important; overflow-x: auto !important; border: 1px solid #D1D5DB; }
        #ledger-portfolio { width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #FFFFFF !important; }
        #ledger-portfolio th { position: -webkit-sticky !important; position: sticky !important; top: 0 !important; z-index: 10 !important; background-color: #E5E7EB !important; color: #111111 !important; font-size: 1.00rem !important; font-weight: bold !important; padding: 14px 12px !important; text-align: left; border-bottom: 3px solid #007bff !important; white-space: nowrap !important; user-select: none; }
        #ledger-portfolio td { color: #222222 !important; font-size: 0.95rem !important; padding: 12px 12px !important; border-bottom: 1px solid #E5E7EB !important; white-space: nowrap !important; }
        #ledger-portfolio tr:nth-child(even) { background-color: #F9FAFB !important; }
        #ledger-portfolio tr:hover { background-color: #F3F4F6 !important; }
    </style>
    """
    st.markdown(ledger_a_css, unsafe_allow_html=True)
    st.markdown(f"<div class='ledger-a-scroll-window'>{html_table_a}</div>", unsafe_allow_html=True)
    st.markdown(f"""<div style='background-color: #f1f5f9; padding: 10px 14px; border-radius: 4px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; font-size: 0.88rem; font-weight: bold; margin-bottom: 20px; border: 1px solid #cbd5e1;'><div>🌎 FX: US/NZD: <span style='color: #0284c7;'>{usd_to_nzd_rate:.4f}</span> | AU/NZD: <span style='color: #0284c7;'>{aud_to_nzd_rate:.4f}</span></div><div>📋 Invested: <span style='color: #334155;'>${tot_invest_nzd:,.2f} NZD</span></div><div>💰 Cash: <span style='color: #0284c7;'>${integ_cash_nzd:,.2f} NZD</span></div><div style='background-color: #e2e8f0;'>👑 TOTAL VALUE:<br><span style='color: #0f172a; font-size: 1.15rem;'>${tot_app_value:,.2f} NZD</span></div><div>📈 Return: <span style='color: {p_color};'>{p_sign}${tot_profit_nzd:,.2f} ({p_sign}{tot_roi_nzd:.2f}%)</span></div></div>""", unsafe_allow_html=True)
else:
    st.info("💡 Portfolio ledger values are currently processing. Verify slot input expressions.")

# =============================================================================
# 📊 Layer B: Asset Comparison Grid (ORDERED BELOW A2)
# =============================================================================
st.markdown("#### 📊 Layer B: Asset Comparison Grid")

# Build chart_list early here so both Layer B and Layer C can safely reference it
chart_list = [str(t).strip().upper() for t in all_active_workspace_tickers if str(t).strip().upper() in operational_dfs]

if master_unified_rows:
    b_df = pd.DataFrame(master_unified_rows)
    cols_b = ["Ticker", "Sector", "Asset Name", "Price", "Return", "Limit Buy at", "T/P Exit", "Status", "Fast MA", "Slow MA", "RSI", "ATR"]
    b_df = b_df[cols_b]
    
    # Use session state to find Layer C's selected token to dynamically sync tables
    current_calc_ticker = st.session_state.get("target_execution_asset_key", chart_list[0] if chart_list else "")
    if current_calc_ticker in b_df["Ticker"].values:
        hoist_row = b_df[b_df["Ticker"] == current_calc_ticker].copy()
        remaining_rows = b_df[b_df["Ticker"] != current_calc_ticker].copy()
        b_df = pd.concat([hoist_row, remaining_rows], ignore_index=True)
        
    df_portfolio_display = b_df.copy()
    for col in ["Price", "Limit Buy at", "T/P Exit", "Fast MA", "Slow MA", "ATR"]:
        df_portfolio_display[col] = df_portfolio_display[col].map("${:,.2f}".format)
    df_portfolio_display["Return"] = df_portfolio_display["Return"].apply(lambda x: f"🟢 {x:+.2f}%" if x >= 3.00 else f"{x:+.2f}%")
    df_portfolio_display["RSI"] = df_portfolio_display["RSI"].apply(lambda x: f"🟢 {x:,.1f}" if x >= 60.0 else f"{x:,.1f}")
    
    if current_calc_ticker:
        df_portfolio_display["Ticker"] = df_portfolio_display["Ticker"].apply(lambda x: f"🎯 {x}" if x == current_calc_ticker else x)
        
    html_portfolio_table = df_portfolio_display.to_html(index=False, escape=False, table_id="portfolio-screener")
    
    portfolio_combined_html = f"""
    <style>
        body {{ margin: 0; padding: 0; background-color: transparent; }}
        .portfolio-scroll-window {{ max-height: 320px; overflow-y: auto !important; overflow-x: auto !important; border: 1px solid #D1D5DB; }}
        #portfolio-screener {{ width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #FFFFFF !important; }}
        #portfolio-screener th {{ position: -webkit-sticky !important; position: sticky !important; top: 0 !important; z-index: 10 !important; background-color: #E5E7EB !important; color: #111111 !important; font-size: 1.00rem !important; font-weight: bold !important; padding: 16px 12px !important; text-align: left; border-bottom: 3px solid #007bff !important; white-space: nowrap !important; cursor: pointer !important; user-select: none; }}
        #portfolio-screener th::after {{ content: " ↕"; font-size: 0.8rem; color: #888; padding-left: 5px; }}
        #portfolio-screener td {{ color: #222222 !important; font-size: 0.95rem !important; padding: 12px 12px !important; border-bottom: 1px solid #E5E7EB !important; white-space: nowrap !important; }}
        #portfolio-screener tr:nth-child(even) {{ background-color: #F9FAFB !important; }}
        #portfolio-screener tr:hover {{ background-color: #F3F4F6 !important; }}
    </style>
    <div class='portfolio-scroll-window'>{html_portfolio_table}</div>
    <script>
        document.querySelectorAll("#portfolio-screener th").forEach((header, index) => {{
            header.addEventListener("click", () => {{
                const table = document.getElementById("portfolio-screener");
                const tbody = table.querySelector("tbody");
                const rows = Array.from(tbody.querySelectorAll("tr"));
                const isAscending = header.classList.contains("sort-asc");
                table.querySelectorAll("th").forEach(th => th.classList.remove("sort-asc", "sort-desc"));
                rows.sort((rowA, rowB) => {{
                    let cellA = rowA.children[index].textContent.replace(/[\\$,%x\\s]/g, "").trim().replace(/🟢/g, "").replace(/🎯/g, "").trim();
                    let cellB = rowB.children[index].textContent.replace(/[\\$,%x\\s]/g, "").trim().replace(/🟢/g, "").replace(/🎯/g, "").trim();
                    const numA = parseFloat(cellA); const numB = parseFloat(cellB);
                    if (!isNaN(numA) && !isNaN(numB)) return isAscending ? numB - numA : numA - numB;
                    return isAscending ? cellB.localeCompare(cellA) : cellA.localeCompare(cellB);
                }});
                header.classList.toggle("sort-asc", !isAscending); header.classList.toggle("sort-desc", isAscending);
                rows.forEach(row => tbody.appendChild(row));
            }});
        }});
    </script>
    """
    st.components.v1.html(portfolio_combined_html, height=340, scrolling=False)
else:
    st.info("💡 Portfolio overview data matrix processing.")

# =============================================================================
# 🔍 Core System Chart Analytics
# =============================================================================
st.markdown("#### 🔍 Core System Chart Analytics")
if chart_list:
    sel_chart_ticker = st.radio("🛰️ Global Chart Engine Quick-Link Bar:", options=chart_list, horizontal=True)
    chart_bars_map = {"1 Month": 22, "3 Months": 65, "6 Months": 130, "1 Year": 252, "2 Years": 504}
    zoom_bars = chart_bars_map.get(st.session_state.get("roi_window", "1 Year"), 252)
    cleaned_key = str(sel_chart_ticker).strip().upper()
    c_df = operational_dfs[cleaned_key].copy().tail(zoom_bars).reset_index().rename(columns={'index': 'Date'})
    
    if not c_df.empty:
        c_df['Date'] = pd.to_datetime(c_df['Date']).dt.strftime('%Y-%m-%d')
        last_r = c_df.iloc[-1]
        atr_f = float(last_r['Close']) - (2.0 * float(last_r['ATR']))
        st.markdown(f"""<div style='padding: 6px 12px; background-color: #f8fafc; border-radius: 4px; border-left: 5px solid #FF9900; margin-bottom: 15px; font-size: 1.0rem; font-weight: bold; border: 1px solid #e2e8f0;'>⚠️ <span style='color: #FF9900;'>{sel_chart_ticker} Safety Stops:</span> Current 2x ATR Noise Buffer is <span style='color: #0f172a;'>${2.0*float(last_r['ATR']):.2f}</span>. Dynamic Risk Floor sits at <span style='color: #16a34a;'>${atr_f:.2f}</span>.</div>""", unsafe_allow_html=True)
        y_scale = alt.Scale(domain=[c_df['Close'].min() * 0.95, c_df['Close'].max() * 1.05], clamp=True)
        base = alt.Chart(c_df).encode(x='Date:T').properties(width='container', height=260)
        st.altair_chart(alt.layer(base.mark_line(color='#4A90E2', strokeWidth=3).encode(y=alt.Y('Close:Q', scale=y_scale)), base.mark_line(color='#00FF66', strokeWidth=2).encode(y='Fast_MA:Q'), base.mark_line(color='#FF3333', strokeWidth=2).encode(y='Slow_MA:Q')), use_container_width=True)
# =============================================================================
# 📐 Layer C: Volatility-Adjusted Position Sizing Calculator
# =============================================================================
st.markdown("#### 📐 Layer C: Volatility-Adjusted Position Sizing Calculator")
if chart_list:
    calc_col1, calc_col2 = st.columns(2)
    with calc_col1:
        st.markdown("<p style='font-size: 1.1rem; font-weight: bold; color: #0284c7; margin-bottom: 2px;'>⚙️ Risk Parameters</p>", unsafe_allow_html=True)
        sel_calc_tk = st.selectbox("Target Execution Asset:", options=chart_list, index=0, key="target_execution_asset_key")
        m_risk = st.number_input("Max Account Risk Allowed (NZD $):", value=25.00, step=5.0)
        st.markdown("---")
        st.markdown(f"📋 **Your Available Funding Vaults:**\n• **NZD Wallet:** ${cash_nzd:,.2f}\n• **AUD Wallet:** ${cash_aud:,.2f}\n• **USD Wallet:** ${cash_usd:,.2f}")
    
    l_bar = operational_dfs[sel_calc_tk].iloc[-1]
    c_px, c_at = float(l_bar['Close']), float(l_bar['ATR'])
    is_us = not (sel_calc_tk.endswith(".NZ") or sel_calc_tk.endswith(".AX"))
    curr_lbl, mult = ("USD", usd_to_nzd_rate) if is_us else ("NZD", 1.0)
    stop_dist = 2.0 * c_at
    shares_fit = m_risk / (stop_dist * mult)
    tot_cap_native, tot_cap_nzd = shares_fit * c_px, shares_fit * c_px * mult
    
    with calc_col2:
        st.markdown(f"<p style='font-size: 1.1rem; font-weight: bold; color: #16a34a; margin-bottom: 2px;'>⚡ Mathematical Sizing Blueprint ({sel_calc_tk})</p>", unsafe_allow_html=True)
        m_c1, m_c2, m_c3 = st.columns(3)
        with m_c1: st.metric("Optimal Execution Size", f"{shares_fit:.4f} Shares")
        with m_c2: st.metric("Limit Entry Trigger", f"${c_px - (0.5*c_at):.2f} {curr_lbl}")
        with m_c3: st.metric("2x ATR Protective Stop", f"${c_px - stop_dist:.2f} {curr_lbl}")
        avail_cash = cash_usd if is_us else cash_nzd
        gap = tot_cap_native - avail_cash
        f_status = f"🟩 <span class='custom-funding-highlight'>Vault Verified:</span> Native {curr_lbl} wallet handles this cleanly." if gap <= 0 else f"🟨 <span class='custom-funding-highlight'>FX Buffer Needed:</span> Convert ${gap * mult:,.2f} NZD inside Sharesies."
        st.markdown(f'<div class="custom-funding-list"><div class="custom-funding-item">• <b>Total Position Capital:</b> <span class="custom-funding-highlight">${tot_cap_native:,.2f} {curr_lbl}</span> (${tot_cap_nzd:,.2f} NZD)</div><div class="custom-funding-item">• <b>Cushion Distance Risk:</b> <span class="custom-funding-highlight">${stop_dist:.2f} {curr_lbl}</span> per share.</div><div class="custom-funding-item">• <b>Portfolio Funding Status:</b> {f_status}</div></div>', unsafe_allow_html=True)

st.markdown("#### 🔄 Layer D: Institutional Sector Money Flow")
if macro_sector_rows:
    st.dataframe(pd.DataFrame(macro_sector_rows).sort_values(by="RSI Status Value", ascending=False), use_container_width=True, hide_index=True)
