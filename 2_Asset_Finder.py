# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: CONFIG & THEME SETUP (PART 1 OF 3)
# ==============================================================================
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import altair as alt
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
        div[data-testid="stTitle"] { margin-top: -20px !important; margin-bottom: -10px !important; }
        div[data-testid="stCaptionContainer"] { margin-bottom: 5px !important; }
        div[data-testid="stTab"] { padding: 4px 16px !important; }
        html, body, [data-testid="stAppViewContainer"] { font-size: 1.15rem !important; }
        div[data-testid="stDataFrame"] * { font-size: 1.20rem !important; }
        div[data-testid="stDataFrame"] [role="row"] { margin-top: 2px !important; margin-bottom: 2px !important; }
        h1 { font-size: 2.0rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
        .small-header { font-size: 1.25rem !important; font-weight: bold !important; color: #4A90E2 !important; margin-bottom: 4px !important; }
    </style>
""", unsafe_allow_html=True)

def apply_alpha_signal_theme(df):
    def style_breakout_rows(row):
        styles = [''] * len(row)
        vol_multiple = float(row['Vol Multiple']) if 'Vol Multiple' in row.index else 0.0
        alert_status = str(row['Alert Status']) if 'Alert Status' in row.index else ""
        elite_statuses = ["🌟 STRONG BUY", "🟢 Bullish Turning (High Volume)"]
        if alert_status in elite_statuses and vol_multiple >= 2.0:
            return ['background-color: #0A1128; color: #00E5FF; font-weight: 700; border: 1px solid #00E5FF;'] * len(row)
        if 'Alert Status' in row.index:
            idx = row.index.get_loc('Alert Status')
            if alert_status == "🌟 STRONG BUY": styles[idx] = 'background-color: #0A1128; color: #00E5FF; font-weight: bold;'
            elif alert_status == "🟢 Bullish Turning (High Volume)": styles[idx] = 'background-color: #1e3a1e; color: #38ef7d; font-weight: bold;'
            elif alert_status == "🟡 Bullish Turning (Low Volume)": styles[idx] = 'background-color: #3a351e; color: #f1c40f; font-weight: bold;'
            elif alert_status == "🔴 Structural Bear": styles[idx] = 'background-color: #3a1e1e; color: #e74c3c; font-weight: bold;'
        return styles
    return df.style.apply(style_breakout_rows, axis=1)

TARGETS_FILE = "portfolio_targets.json"
CACHE_FILE = "alpha_hunter_cache.json"
NAMES_CACHE_FILE = "alpha_names_cache.json"
CACHE_TTL_MINUTES = 120

disk_memory = {}
if os.path.exists(TARGETS_FILE):
    try:
        with open(TARGETS_FILE, 'r') as f: disk_memory = json.load(f)
    except Exception: pass

if "local_name_map" not in disk_memory: disk_memory["local_name_map"] = {}

runtime_sliders = disk_memory.get("sliders", {})
default_fast_ma = int(runtime_sliders.get("fast_ma", 10))
default_slow_ma = int(runtime_sliders.get("slow_ma", 50))
default_roi = runtime_sliders.get("roi_window", "1 Year")
default_horizon = runtime_sliders.get("graph_horizon", "1 Year")

if "asset_fast_ma" not in st.session_state: st.session_state["asset_fast_ma"] = default_fast_ma
if "asset_slow_ma" not in st.session_state: st.session_state["asset_slow_ma"] = default_slow_ma
if "asset_roi" not in st.session_state: st.session_state["asset_roi"] = default_roi
if "asset_horizon" not in st.session_state: st.session_state["asset_horizon"] = default_horizon

if "view_mode_choice" not in st.session_state: st.session_state["view_mode_choice"] = "Entire Universe"
if "max_share_price_cap" not in st.session_state: st.session_state["max_share_price_cap"] = 50.0

with st.sidebar:
    st.markdown("### 🛠️ Research Settings")
    st.selectbox("Screening Window", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], key="asset_roi", on_change=lambda: st.rerun())
    st.selectbox("Scanner Chart Horizon", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], key="asset_horizon", on_change=lambda: st.rerun())
    st.selectbox("Fast MA (weeks)", [5, 10, 20, 50], index=[5, 10, 20, 50].index(st.session_state["asset_fast_ma"]) if st.session_state["asset_fast_ma"] in [5, 10, 20, 50] else 1, key="asset_fast_ma", on_change=lambda: st.rerun())
    st.selectbox("Slow MA (weeks)", [25, 50, 100], index=[25, 50, 100].index(st.session_state["asset_slow_ma"]) if st.session_state["asset_slow_ma"] in [25, 50, 100] else 1, key="asset_slow_ma", on_change=lambda: st.rerun())

    st.markdown("---")
    st.markdown("### 🎯 Sizing Filters")
    st.radio("Viewing Mode:", ["Entire Universe", "Budget-Friendly Assets"], key="view_mode_choice", on_change=lambda: st.rerun())
    
    if st.session_state["view_mode_choice"] == "Budget-Friendly Assets":
        st.slider("Max Entry Share Price Limit ($):", min_value=2.00, max_value=150.00, value=float(st.session_state["max_share_price_cap"]), step=1.00, format="$%.2f", key="max_share_price_cap", on_change=lambda: st.rerun())

fast_ma_input = st.session_state["asset_fast_ma"]
slow_ma_input = st.session_state["asset_slow_ma"]
selected_timeframe = st.session_state["asset_roi"]
chart_timeframe_choice = st.session_state["asset_horizon"]

st.title("🔍 Asset Finder")
st.caption("Standalone Laboratory Analysis & Market Screeners")
# ==============================================================================
# MASTER STRUCTURAL POOL: ALL NZX50, ASX200, & S&P 500 STOCKS (PART A)
# ==============================================================================
institutional_scan_pool = [
    # --- FULL NEW ZEALAND S&P/NZX 50 COMPONENTS ---
    "AIA.NZ", "EBO.NZ", "FPH.NZ", "IFT.NZ", "MCY.NZ", "MEL.NZ", "MFT.NZ", "SPK.NZ", 
    "CNU.NZ", "CEN.NZ", "FBU.NZ", "RYM.NZ", "ATM.NZ", "AIR.NZ", "ARG.NZ", "GNE.NZ",
    "KPG.NZ", "OCA.NZ", "PCT.NZ", "PFI.NZ", "SUM.NZ", "THL.NZ", "WHS.NZ", "HGH.NZ", 
    "KMD.NZ", "PEB.NZ", "SAN.NZ", "SKC.NZ", "SKT.NZ", "ANZ.NZ", "ERD.NZ", "FRW.NZ", 
    "IPL.NZ", "NZX.NZ", "POT.NZ", "SCL.NZ", "SKL.NZ", "SKO.NZ", "SML.NZ", "VCT.NZ", 
    "VGL.NZ", "VHP.NZ", "WBC.NZ", "FSF.NZ", "GNZ.NZ", "GTK.NZ", "PFI.NZ", "FRE.NZ",

    # --- S&P/ASX 200 COHORT 1 ---
    "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WDS.AX", "TLS.AX",
    "WOW.AX", "WES.AX", "RIO.AX", "FMG.AX", "MQG.AX", "REA.AX", "XRO.AX", "QAN.AX",
    "APA.AX", "AGL.AX", "AMC.AX", "AMP.AX", "ASX.AX", "BEN.AX", "BOQ.AX", "BSL.AX",
    "BXB.AX", "COL.AX", "CPU.AX", "EVN.AX", "FLT.AX", "IAG.AX", "IPL.AX", "JBH.AX",
    "JHX.AX", "LLC.AX", "LYC.AX", "MIN.AX", "MGR.AX", "MPL.AX", "NST.AX", "ORG.AX",
    "ORI.AX", "PLS.AX", "QBE.AX", "RHC.AX", "RMD.AX", "SCG.AX", "SHL.AX", "STO.AX",
    "SUN.AX", "TAH.AX", "TCL.AX", "TNE.AX", "TPG.AX", "TWE.AX", "VCX.AX", "WOR.AX",

    # --- S&P 500 BULK INITIAL COHORT ---
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "BRK-B", "JNJ", "V", "PG", "WMT",
    "LLY", "UNH", "HD", "XOM", "CVX", "MA", "MRK", "PEP", "KO", "COST",
    "NVDA", "AMD", "AVGO", "QCOM", "ASML", "INTC", "MU", "ARM", "SMCI", "PLTR",
    "CRM", "NOW", "WDAY", "SNOW", "NET", "DDOG", "CRWD", "PANW", "FTNT", "ZS",
    "TSLA", "MSTR", "COIN", "HOOD", "DKNG", "SHOP", "NFLX", "DIS", "JPM", "BAC",
    "F", "GM", "AAL", "DAL", "UAL", "KRE", "XBI", "PFE", "KVUE", "T", "VZ", "CMCSA",
    "HPQ", "HPE", "BMY", "NEM", "GOLD", "HBAN", "KEY", "RF", "FITB", "NYCB", "SOFI",
    "SNAP", "U", "CLF", "X", "AA", "FCX", "SBUX", "CSCO", "ACN", "TXN", "IBM", "AMAT"
    # --- S&P 500 COHORT 2: FINANCIALS, HEALTHCARE & INDUSTRY ---
    "GS", "MS", "WFC", "C", "BLK", "AXP", "INTU", "PGR", "CB", "BX", "SCHW", "MMC",
    "AON", "COR", "CI", "BMY", "AMGN", "GILD", "ABT", "MDT", "ISRG", "REGN", "VRTX",
    "GEV", "WM", "NOC", "GD", "ETN", "PH", "CSX", "NSC", "NKE", "MCD", "TJX", "ORLY",
    "AZO", "LOW", "MAR", "HLT", "BKNG", "MDLZ", "MO", "PM", "TGT", "EL", "CL", "KMB",
    "TMUS", "CHTR", "EA", "TTWO", "RBLX", "OKTA", "SPLK", "APTV", "BWA", "ALV", "MGM",
    "WYNN", "LVS", "RCL", "CCL", "NCLH", "DRI", "YUM", "DPZ", "WEN", "QSR", "LEN",
    "DHI", "PHM", "TOL", "NVR", "GRMN", "HAS", "MAT", "POOL", "TSCO", "BBY", "LCID",
    "RIVN", "STLA", "HMC", "TM", "BLNK", "CHPT", "TSM", "ON", "NXPI", "MCHP", "MPWR"
    # --- S&P 500 COHORT 3: ENERGY, UTILITIES & INDUSTRIAL CYCLICALS ---
    "MRVL", "SWKS", "QRVO", "WOLF", "INFY", "WIT", "CTSH", "EPAM", "FICO", "GEN",
    "ANSS", "PTC", "ADSK", "CDNS", "SNPS", "VRSN", "AKAM", "DD", "DOW", "ECL",
    "CTVA", "APD", "SHW", "PPG", "GOLD", "AEM", "HMY", "AU", "BTG", "LNG",
    "EOG", "COP", "SLB", "HAL", "BKR", "OXY", "DVN", "FANG", "MRO", "HES",
    "APA", "CTRA", "EQT", "SO", "D", "AEE", "AEP", "CNP", "CMS", "ED",
    "EIX", "ES", "ETR", "FE", "LNT", "NEE", "NI", "PEG", "PNW", "PPL",
    "SRE", "WEC", "XEL", "AMT", "CCI", "WY", "SBAC", "DLR", "EQIX", "PSA",
    "EXR", "CUBE", "IRM", "O", "NNN", "ADC", "WPC", "SPG", "KIM", "REG",
    "FRT", "MAA", "CPT", "COF", "DFS", "IBKR", "LPLA", "RJF", "STT", "NTRS",
    "BK", "AMP", "TROW", "BEN", "IVZ", "AMG", "SEIC", "FDS", "MCO", "SPGI",
    "CBOE", "NDAQ", "CME", "ICE", "MKTX", "GE", "HON", "UNP", "LMT", "RTX"
]

# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: OPTIMIZED DICTIONARY & CACHE ENGINE (PART 2)
# ==============================================================================
local_name_map = {
    "F": "Ford Motor Co.", "GM": "General Motors", "PFE": "Pfizer Inc.", "T": "AT&T Inc.",
    "VZ": "Verizon Communications", "AAL": "American Airlines", "DAL": "Delta Air Lines",
    "SOFI": "SoFi Technologies", "PLTR": "Palantir Technologies", "AIR.NZ": "Air New Zealand",
    "SPK.NZ": "Spark NZ", "FBU.NZ": "Fletcher Building", "TLS.AX": "Telstra Group"
}

def calculate_indicators_only(df, fast_ma, slow_ma):
    df = df.copy()
    if df.empty or len(df) < max(fast_ma, slow_ma, 30): return df
    close_series, high_series, low_series = df['Close'].astype(float), df['High'].astype(float), df['Low'].astype(float)
    
    df['Fast_MA'] = close_series.rolling(window=int(fast_ma)).mean()
    df['Slow_MA'] = close_series.rolling(window=int(slow_ma)).mean()
    
    rolling_mean_20 = close_series.rolling(window=20).mean()
    rolling_std_20 = close_series.rolling(window=20).std()
    df['Lower_Bollinger_Band'] = rolling_mean_20 - (2 * rolling_std_20)
    
    tr1 = high_series - low_series
    tr2, tr3 = (high_series - close_series.shift(1)).abs(), (low_series - close_series.shift(1)).abs()
    df['True_Range'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = df['True_Range'].rolling(window=14).mean()
    df['Avg_Volume_20D'] = df['Volume'].rolling(window=20).mean() if 'Volume' in df.columns else 1.0
        
    delta = close_series.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs)).fillna(50)
    df['MACD'] = close_series.ewm(span=12, adjust=False).mean() - close_series.ewm(span=26, adjust=False).mean()
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def fetch_all_market_data_batch(ticker_list, start_date):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    resolved_cache_path = os.path.join(project_root, CACHE_FILE)

    # 1. ATTEMPT BULLETPROOF DISK LOAD
    if os.path.exists(resolved_cache_path):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(resolved_cache_path))
        if datetime.now() - file_mod_time < timedelta(minutes=CACHE_TTL_MINUTES):
            try:
                # Load flat structure from disk
                df_flat = pd.read_json(resolved_cache_path)
                df_flat.index = pd.to_datetime(df_flat.index)
                
                # Reconstruct MultiIndex dynamically via explicit split mapping
                new_tuples = []
                for col in df_flat.columns:
                    parts = col.split("---")
                    if len(parts) == 2:
                        new_tuples.append((parts[0], parts[1]))
                    else:
                        new_tuples.append((col, "Close"))
                        
                df_flat.columns = pd.MultiIndex.from_tuples(new_tuples)
                return df_flat
            except Exception as e:
                pass  # Fall back to web download safely if structural definitions vary
            
    # 2. CHUNKED PARALLEL DOWNLOAD ENGINE
    try:
        unique_tickers = list(dict.fromkeys(ticker_list))
        chunk_size = 100
        chunked_dfs = []
        
        loading_slot = st.empty()
        loading_slot.info(f"🔄 Cache refresh required. Initializing structural multi-market chunked downloads...")
        
        for i in range(0, len(unique_tickers), chunk_size):
            sub_list = unique_tickers[i:i+chunk_size]
            df_chunk = yf.download(sub_list, start=start_date, interval="1wk", group_by='ticker', actions=False, threads=True, progress=False)
            if not df_chunk.empty:
                chunked_dfs.append(df_chunk)
                
        loading_slot.empty()
        
        if chunked_dfs:
            df_live = pd.concat(chunked_dfs, axis=1)
            
            # Create a flat copy explicitly built for reliable JSON serialization
            df_serializable = df_live.copy()
            flat_cols = []
            for col in df_serializable.columns:
                if isinstance(col, tuple):
                    flat_cols.append(f"{col[0]}---{col[1]}")
                else:
                    flat_cols.append(str(col))
                    
            df_serializable.columns = flat_cols
            df_serializable.to_json(resolved_cache_path)
            return df_live
            
    except Exception as e: 
        st.sidebar.error(f"Batch Connection Interrupted: {str(e)}")
        return pd.DataFrame()

def extract_ticker_dataframe(df_all, ticker):
    try:
        if df_all.empty or ticker not in df_all.columns.get_level_values(0):
            return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        df = df_all[ticker].copy()
        df.columns = [str(c).title() for c in df.columns]
        return df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    except: return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

lookback_days_map = {"1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365, "2 Years": 730}
chosen_lookback_days = lookback_days_map.get(chart_timeframe_choice, 365)
lookback_start_date = datetime.now() - timedelta(days=lookback_days_map["2 Years"] + 250)

RAW_MARKET_BATCH = fetch_all_market_data_batch(institutional_scan_pool, lookback_start_date)
breakout_rows, discount_rows, operational_dfs = [], [], {}
unique_scan_pool = list(dict.fromkeys(institutional_scan_pool))

# --- MEMORY TRAP OPTIMIZATION: LOAD NAMES FILE EXACTLY ONCE OUTSIDE THE LOOP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
resolved_names_path = os.path.join(project_root, NAMES_CACHE_FILE)

if os.path.exists(resolved_names_path):
    try:
        with open(resolved_names_path, 'r') as f: disk_names = json.load(f)
    except: disk_names = {}
else:
    disk_names = {}

cache_was_updated = False

# --- THE MAIN PERFORMANCE-CLEANED LOOP ---
for ticker in unique_scan_pool:
    hist_df = extract_ticker_dataframe(RAW_MARKET_BATCH, ticker)
    if hist_df.empty or len(hist_df) < max(fast_ma_input, slow_ma_input, 30): continue
    
    df_calc = calculate_indicators_only(hist_df, fast_ma_input, slow_ma_input)
    operational_dfs[ticker] = df_calc
    
    last_close = float(df_calc['Close'].iloc[-1])
    if st.session_state.get("view_mode_choice") == "Budget-Friendly Assets":
        if last_close > float(st.session_state.get("max_share_price_cap", 50.0)):
            continue

    prev_close = float(df_calc['Close'].iloc[-2]) if len(df_calc) > 1 else last_close
    pct_change = ((last_close - prev_close) / prev_close) * 100
    
    fast_ma_val = float(df_calc['Fast_MA'].iloc[-1]) if 'Fast_MA' in df_calc.columns else last_close
    slow_ma_val = float(df_calc['Slow_MA'].iloc[-1]) if 'Slow_MA' in df_calc.columns else last_close
    rsi_val = float(df_calc['RSI'].iloc[-1]) if 'RSI' in df_calc.columns else 50.0
    macd_val = float(df_calc['MACD'].iloc[-1]) if 'MACD' in df_calc.columns else 0.0
    sig_val = float(df_calc['Signal_Line'].iloc[-1]) if 'Signal_Line' in df_calc.columns else 0.0
    atr_val = float(df_calc['ATR'].iloc[-1]) if 'ATR' in df_calc.columns else 0.0
    bb_lower_val = float(df_calc['Lower_Bollinger_Band'].iloc[-1]) if 'Lower_Bollinger_Band' in df_calc.columns else last_close

    current_volume = int(df_calc['Volume'].iloc[-1]) if 'Volume' in df_calc.columns else 0
    avg_volume_20d = float(df_calc['Avg_Volume_20D'].iloc[-1]) if 'Avg_Volume_20D' in df_calc.columns else 1.0
    volume_multiple = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0.0
    
    hist_365 = df_calc[df_calc.index >= pd.to_datetime(datetime.now() - timedelta(days=730)).tz_localize(df_calc.index.tz)] if not df_calc.empty else df_calc
    true_52w_high, true_52w_low = float(hist_365['High'].max()), float(hist_365['Low'].min())
    proximity_to_low_pct = ((last_close - true_52w_low) / true_52w_low) * 100
    
    market_label = "NZ" if ticker.endswith(".NZ") else ("AUS" if ticker.endswith(".AX") else "US")
    
    if last_close > fast_ma_val and last_close > slow_ma_val and volume_multiple >= 1.5:
        breakout_signal = "🌟 STRONG BUY"
    elif last_close > fast_ma_val and last_close <= slow_ma_val and volume_multiple >= 1.5:
        breakout_signal = "🟢 Bullish Turning (High Volume)"
    elif (last_close > fast_ma_val or last_close > slow_ma_val) and volume_multiple < 1.5:
        breakout_signal = "🟡 Bullish Turning (Low Volume)"
    else:
        breakout_signal = "🔴 Structural Bear"

    # 🚀 INSTANT MEMORY LOOKUP (No file system or web calls inside the loop!)
    if ticker in disk_names:
        resolved_name = disk_names[ticker]
    else:
        try:
            resolved_name = yf.Ticker(ticker).info.get('longName', local_name_map.get(ticker, f"{ticker}"))
            disk_names[ticker] = resolved_name
            cache_was_updated = True
        except:
            resolved_name = local_name_map.get(ticker, f"{ticker}")

    if breakout_signal != "🔴 Structural Bear":
        safe_breakout_limit = round(fast_ma_val, 2)
        breakout_rows.append({
            "Market": market_label, "Ticker": ticker, "Company Name": resolved_name,
            "Live Price": last_close, "Alert Status": breakout_signal, "Limit Entry Target": safe_breakout_limit,
            "Vol Multiple": volume_multiple, "Daily Change %": pct_change, "RSI Momentum": rsi_val, "ATR Volatility": atr_val
        })

    if last_close <= (true_52w_low * 1.10):
        signal_label = "🟢 Bullish Turning" if macd_val > sig_val else "🔴 Bearish Floor"
        safe_limit_price = round(true_52w_low * 1.01, 2)
        
        discount_rows.append({
            "Market": market_label, "Ticker": ticker, "Company Name": resolved_name,
            "Live Price": last_close, "52W Low Floor": true_52w_low, "Limit Entry Target": safe_limit_price,
            "Lower Bollinger Band": bb_lower_val, "52W High Ceiling": true_52w_high,
            "Proximity to Low": proximity_to_low_pct, "RSI Status": rsi_val, "MACD Signal": signal_label
        })

# --- FLUSH ENTIRE CACHE TO DRIVE EXACTLY ONCE IF UPDATED ---
if cache_was_updated:
    try:
        with open(resolved_names_path, 'w') as f:
            json.dump(disk_names, f, indent=4)
    except: pass
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: DASHBOARD INTERFACE LAYOUT (PART 3 OF 3)
# ==============================================================================
tab_momentum, tab_discount = st.tabs(["🔥 Breakouts", "📉 Possible Value Discounts"])

with tab_momentum:
    st.markdown("<p class='small-header'>Potential Targets</p>", unsafe_allow_html=True)
    if breakout_rows:
        raw_m_df = pd.DataFrame(breakout_rows)
        status_rank_map = {"🌟 STRONG BUY": 0, "🟢 Bullish Turning (High Volume)": 1, "🟡 Bullish Turning (Low Volume)": 2}
        raw_m_df["Rank_Weight"] = raw_m_df["Alert Status"].map(status_rank_map).fillna(3)
        master_breakout_df = raw_m_df.sort_values(by=["Rank_Weight", "Daily Change %"], ascending=[True, False]).head(20)
        
        page_m = st.radio("Pagination Window Control:", ["Show Tickers 1–10", "Show Tickers 11–20"], horizontal=True, key="m_page_toggle")
        sliced_breakout_df = master_breakout_df.iloc[0:10] if page_m == "Show Tickers 1–10" else master_breakout_df.iloc[10:20]
            
        momentum_tickers_ordered = sliced_breakout_df["Ticker"].tolist() if not sliced_breakout_df.empty else []
        cols_order = ["Market", "Ticker", "Company Name", "Alert Status", "Live Price", "Limit Entry Target", "ATR Volatility", "Vol Multiple", "Daily Change %", "RSI Momentum"]
        
        if not sliced_breakout_df.empty:
            st.dataframe(
                apply_alpha_signal_theme(sliced_breakout_df[[c for c in cols_order if c in sliced_breakout_df.columns]]), 
                use_container_width=True, hide_index=True, height=440, 
                column_config={
                    "Live Price": st.column_config.NumberColumn(format="$%.2f"), 
                    "Limit Entry Target": st.column_config.NumberColumn("Pullback Limit Buy", format="$%.2f"),
                    "ATR Volatility": st.column_config.NumberColumn("Daily ATR ($)", format="$%.2f"), 
                    "Vol Multiple": st.column_config.NumberColumn("Volume Surge", format="%.2fx"), 
                    "Daily Change %": st.column_config.NumberColumn(format="%+.2f%%"), 
                    "RSI Momentum": st.column_config.NumberColumn(format="%.1f")
                }
            )
        else:
            st.info("No active setups match your budget filters inside this window tier.")
        
        st.markdown("---")
        if momentum_tickers_ordered:
            selected_m_ticker = st.radio("🛰 **Global Chart Engine Quick-Link Bar:**", options=momentum_tickers_ordered, horizontal=True, key="m_link_key")
            if selected_m_ticker in operational_dfs:
                chart_sliced = operational_dfs[selected_m_ticker].tail(chosen_lookback_days).copy().reset_index()
                if 'index' in chart_sliced.columns: chart_sliced = chart_sliced.rename(columns={'index': 'Date'})
                if not chart_sliced.empty and 'Fast_MA' in chart_sliced.columns:
                    chart_sliced['Date'] = pd.to_datetime(chart_sliced['Date']).dt.strftime('%Y-%m-%d')
                    y_scale = alt.Scale(domain=[float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].min().min()) * 0.98, float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].max().max()) * 1.02], zero=False)
                    base = alt.Chart(chart_sliced).encode(x=alt.X('Date:T', title=None)).properties(width=900, height=320)
                    final_m_chart = (
                        base.mark_line(color='#4A90E2', strokeWidth=3.5).encode(y=alt.Y('Close:Q', scale=y_scale, title='Price ($)')) + 
                        base.mark_line(color='#00FF66', strokeWidth=3.0).encode(y=alt.Y('Fast_MA:Q')) + 
                        base.mark_line(color='#FF3333', strokeWidth=3.0).encode(y=alt.Y('Slow_MA:Q'))
                    )
                    st.altair_chart(final_m_chart, use_container_width=True)
    else:
        st.info("No tickers matching crossover momentum velocity rules right now.")

with tab_discount:
    st.markdown("<p class='small-header'>Mean-Reversion Floor Screening Grid</p>", unsafe_allow_html=True)
    if discount_rows:
        raw_d_df = pd.DataFrame(discount_rows)
        discount_rank_map = {"🟢 Bullish Turning": 0, "🔴 Bearish Floor": 1}
        raw_d_df["Rank_Weight"] = raw_d_df["MACD Signal"].map(discount_rank_map).fillna(2)
        master_discount_df = raw_d_df.sort_values(by=["Rank_Weight", "Proximity to Low"], ascending=[True, True]).head(20)
        
        page_d = st.radio("Pagination Window Control:", ["Show Tickers 1–10", "Show Tickers 11–20"], horizontal=True, key="d_page_toggle")
        sliced_discount_df = master_discount_df.iloc[0:10] if page_d == "Show Tickers 1–10" else master_discount_df.iloc[10:20]
            
        discount_tickers_ordered = sliced_discount_df["Ticker"].tolist() if not sliced_discount_df.empty else []
        cols_discount_order = ["Market", "Ticker", "Company Name", "Live Price", "52W Low Floor", "Limit Entry Target", "Lower Bollinger Band", "52W High Ceiling", "Proximity to Low", "RSI Status", "MACD Signal"]
        
        if not sliced_discount_df.empty:
            st.dataframe(
                sliced_discount_df[[c for c in cols_discount_order if c in sliced_discount_df.columns]], 
                use_container_width=True, hide_index=True, height=440, 
                column_config={
                    "Live Price": st.column_config.NumberColumn(format="$%.2f"), 
                    "52W Low Floor": st.column_config.NumberColumn(format="$%.2f"), 
                    "Limit Entry Target": st.column_config.NumberColumn("Limit Entry Target", format="$%.2f", width="medium"),
                    "Lower Bollinger Band": st.column_config.NumberColumn("Lower BB", format="$%.2f", width="small"),
                    "52W High Ceiling": st.column_config.NumberColumn(format="$%.2f"), 
                    "Proximity to Low": st.column_config.NumberColumn("Distance From Low", format="%.2f%%"), 
                    "RSI Status": st.column_config.NumberColumn(format="%.1f")
                }
            )
        else:
            st.info("No deep discount setups match your budget filters inside this window tier.")

        st.markdown("---")
        if discount_tickers_ordered:
            selected_d_ticker = st.radio("🛰 **Global Chart Engine Quick-Link Bar:**", options=discount_tickers_ordered, horizontal=True, key="d_link_key")
            if selected_d_ticker in operational_dfs:
                chart_sliced = operational_dfs[selected_d_ticker].tail(chosen_lookback_days).copy().reset_index()
                if 'index' in chart_sliced.columns: chart_sliced = chart_sliced.rename(columns={'index': 'Date'})
                if not chart_sliced.empty and 'Fast_MA' in chart_sliced.columns:
                    chart_sliced['Date'] = pd.to_datetime(chart_sliced['Date']).dt.strftime('%Y-%m-%d')
                    y_scale = alt.Scale(domain=[float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].min().min()) * 0.98, float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].max().max()) * 1.02], zero=False)
                    base = alt.Chart(chart_sliced).encode(x=alt.X('Date:T', title=None)).properties(width=900, height=320)
                    final_d_chart = (
                        base.mark_line(color='#4A90E2', strokeWidth=3.5).encode(y=alt.Y('Close:Q', scale=y_scale, title='Price ($)')) + 
                        base.mark_line(color='#00FF66', strokeWidth=3.0).encode(y=alt.Y('Fast_MA:Q')) + 
                        base.mark_line(color='#FF3333', strokeWidth=3.0).encode(y=alt.Y('Slow_MA:Q'))
                    )
                    st.altair_chart(final_d_chart, use_container_width=True)
    else:
        st.info("No major institutional leaders currently resting inside deep value boundaries.")
