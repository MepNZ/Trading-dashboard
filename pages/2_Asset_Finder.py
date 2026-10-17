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

# --- FORCE THE ENTIRE SUB-PAGE GRID AND CHARTS TO STRETCH FULL-SCREEN ---
st.set_page_config(layout="wide")

# Force wide layout and matching high-visibility font scales with aggressive whitespace reduction
st.markdown("""
    <style>
        /* 1. Crush the dead whitespace padding at the very top of the app page */
        .block-container { 
            padding-top: 0.5rem !important; 
            padding-bottom: 0.5rem !important; 
        }
        
        /* 2. Tighten padding and margins around headers, captions, and tab selections */
        div[data-testid="stTitle"] { margin-top: -20px !important; margin-bottom: -10px !important; }
        div[data-testid="stCaptionContainer"] { margin-bottom: 5px !important; }
        div[data-testid="stTab"] { padding: 4px 16px !important; }
        
        /* 3. Keep text clear and crisp */
        html, body, [data-testid="stAppViewContainer"] {
            font-size: 1.15rem !important;
        }
        div[data-testid="stDataFrame"] * {
            font-size: 1.20rem !important;
        }
        
        /* 4. Optimize row tracking density */
        div[data-testid="stDataFrame"] [role="row"] {
            margin-top: 2px !important;
            margin-bottom: 2px !important;
        }
        h1 { font-size: 2.0rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
        .small-header { font-size: 1.25rem !important; font-weight: bold !important; color: #4A90E2 !important; margin-bottom: 4px !important; }
    </style>
""", unsafe_allow_html=True)

def apply_alpha_signal_theme(df):
    def style_breakout_rows(row):
        # 1. Establish standard blank slate styling for the row
        styles = [''] * len(row)
        
        # 2. Extract values cleanly from the row mapping indexes
        vol_multiple = float(row['Vol Multiple']) if 'Vol Multiple' in row.index else 0.0
        alert_status = str(row['Alert Status']) if 'Alert Status' in row.index else ""
        
        # 3. PRIORITY 1: Check for institutional 2.0x volume spike (Flashes the WHOLE row neon-blue)
        elite_statuses = ["🌟 STRONG BUY", "🟢 Bullish Turning (High Volume)"]
        if alert_status in elite_statuses and vol_multiple >= 2.0:
            # High-visibility deep midnight navy background with electric neon text
            return ['background-color: #0A1128; color: #00E5FF; font-weight: 700; border: 1px solid #00E5FF;'] * len(row)
            
        # 4. PRIORITY 2: Fallback styling rules for target cell modifications
        if 'Alert Status' in row.index:
            idx = row.index.get_loc('Alert Status')
            if alert_status == "🌟 STRONG BUY": 
                styles[idx] = 'background-color: #0A1128; color: #00E5FF; font-weight: bold;'
            elif alert_status == "🟢 Bullish Turning (High Volume)": 
                styles[idx] = 'background-color: #1e3a1e; color: #38ef7d; font-weight: bold;'
            elif alert_status == "🟡 Bullish Turning (Low Volume)": 
                styles[idx] = 'background-color: #3a351e; color: #f1c40f; font-weight: bold;'
            elif alert_status == "🔴 Structural Bear":
                styles[idx] = 'background-color: #3a1e1e; color: #e74c3c; font-weight: bold;'
        return styles
        
    return df.style.apply(style_breakout_rows, axis=1)
TARGETS_FILE = "portfolio_targets.json"
CACHE_FILE = "alpha_hunter_cache.json"
CACHE_TTL_MINUTES = 15

# Read configuration files from the hard drive safely
disk_memory = {}
if os.path.exists(TARGETS_FILE):
    try:
        with open(TARGETS_FILE, 'r') as f:
            disk_memory = json.load(f)
    except Exception: pass

if "local_name_map" not in disk_memory:
    disk_memory["local_name_map"] = {}

# Initialize local sidebar settings or default back to standard values
runtime_sliders = disk_memory.get("sliders", {})
default_fast_ma = int(runtime_sliders.get("fast_ma", 10))
default_slow_ma = int(runtime_sliders.get("slow_ma", 50))
default_roi = runtime_sliders.get("roi_window", "1 Year")
default_horizon = runtime_sliders.get("graph_horizon", "1 Year")

if "asset_fast_ma" not in st.session_state: st.session_state["asset_fast_ma"] = default_fast_ma
if "asset_slow_ma" not in st.session_state: st.session_state["asset_slow_ma"] = default_slow_ma
if "asset_roi" not in st.session_state: st.session_state["asset_roi"] = default_roi
if "asset_horizon" not in st.session_state: st.session_state["asset_horizon"] = default_horizon

# --- INDEPENDENT INTERACTIVE RESEARCH CONTROLS WITH GLOBAL RERUNS ---
with st.sidebar:
    st.markdown("### 🛰️ Research Settings")
    st.selectbox("Screening Window", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], key="asset_roi", on_change=lambda: st.rerun())
    st.selectbox("Scanner Chart Horizon", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], key="asset_horizon", on_change=lambda: st.rerun())
    st.selectbox("Fast MA (weeks)", [5, 10, 20, 50], index=[5, 10, 20, 50].index(st.session_state["asset_fast_ma"]) if st.session_state["asset_fast_ma"] in [5, 10, 20, 50] else 1, key="asset_fast_ma", on_change=lambda: st.rerun())
    st.selectbox("Slow MA (weeks)", [25, 50, 100], index=[25, 50, 100].index(st.session_state["asset_slow_ma"]) if st.session_state["asset_slow_ma"] in [25, 50, 100] else 1, key="asset_slow_ma", on_change=lambda: st.rerun())

fast_ma_input = st.session_state["asset_fast_ma"]
slow_ma_input = st.session_state["asset_slow_ma"]
selected_timeframe = st.session_state["asset_roi"]
chart_timeframe_choice = st.session_state["asset_horizon"]

st.title("🔍 Asset Finder")
st.caption("Standalone Laboratory Analysis & Market Screeners")
institutional_scan_pool = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "BRK-B", "JNJ", "V", "PG", "WMT",
    "LLY", "UNH", "HD", "XOM", "CVX", "MA", "MRK", "PEP", "KO", "COST",
    "NVDA", "AMD", "AVGO", "QCOM", "ASML", "INTC", "MU", "ARM", "SMCI", "PLTR",
    "CRM", "NOW", "WDAY", "SNOW", "NET", "DDOG", "CRWD", "PANW", "FTNT", "ZS",
    "TEAM", "ADBE", "ORAC", "TSLA", "MSTR", "COIN", "HOOD", "DKNG", "SHOP", "NFLX",
    "APP", "SNAP", "U", "DIS", "JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "AXP", 
    "PYPL", "SQ", "SOFI", "CAT", "GE", "HON", "UNP", "UPS", "FDX", "LMT", "RTX", 
    "FCX", "NUE", "BE", "LIN", "NEM", "SPY", "QQQ", "IWM", "XLK", "XLE", "XLF", 
    "XLV", "XLI", "XLY", "XLP", "XLC", "XLB", "XLU", "XLRE", "SMH", "XBI", "GDX", 
    "OIH", "KRE", "TAN", "PLD", "DUK", "AIA.NZ", "EBO.NZ", "FPH.NZ", "IFT.NZ", 
    "MCY.NZ", "MEL.NZ", "MFT.NZ", "SPK.NZ", "CNU.NZ", "CEN.NZ", "FBU.NZ", "RYM.NZ",
    "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WDS.AX", "TLS.AX", 
    "WOW.AX", "WES.AX", "RIO.AX", "FMG.AX", "MQG.AX", "REA.AX", "XRO.AX"
]
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: DICTIONARY & CACHE ENGINE (PART 2 - HALF 1)
# ==============================================================================
local_name_map = {
    "AAPL": "Apple Inc.", "ADBE": "Adobe Inc.", "AMZN": "Amazon.com Inc.", "APP": "AppLovin Corp",
    "ARM": "ARM Holdings", "ASML": "ASML Holding", "AVGO": "Broadcom Inc.", "BRK-B": "Berkshire Hathaway",
    "CRM": "Salesforce Inc.", "DIS": "Walt Disney Co.", "GOOGL": "Alphabet Inc.", "HD": "Home Depot Inc.",
    "KO": "The Coca-Cola Co.", "LLY": "Eli Lilly & Co.", "META": "Meta Platforms", "MSFT": "Microsoft Corp",
    "NFLX": "Netflix Inc.", "NOW": "ServiceNow Inc.", "ORAC": "Oracle Corp", "PEP": "PepsiCo Inc.",
    "PG": "Procter & Gamble", "QCOM": "Qualcomm Inc.", "SNAP": "Snap Inc.", "TSLA": "Tesla Inc.",
    "U": "Unity Software", "UNH": "UnitedHealth Group", "WMT": "Walmart Inc.", "AMD": "Advanced Micro Devices", 
    "CRWD": "CrowdStrike Holdings", "DDOG": "Datadog Inc.", "DKNG": "DraftKings Inc.", "FTNT": "Fortinet Inc.",
    "HOOD": "Robinhood Markets", "INTC": "Intel Corp", "NET": "Cloudflare Inc.", "NVDA": "NVIDIA Corp", 
    "PANW": "Palo Alto Networks", "PLTR": "Palantir Technologies", "SHOP": "Shopify Inc.", "SMCI": "Super Micro Computer", 
    "SNOW": "Snowflake Inc.", "TEAM": "Atlassian Corp", "WDAY": "Workday Inc.", "ZS": "Zscaler Inc.",
    "AXP": "American Express", "BAC": "Bank of America", "BLK": "BlackRock Inc.", "C": "Citigroup Inc.",
    "COIN": "Coinbase Global", "GS": "Goldman Sachs", "JPM": "JPMorgan Chase", "MS": "Morgan Stanley",
    "PYPL": "PayPal Holdings", "SOFI": "SoFi Technologies", "SQ": "Block Inc.", "V": "Visa Inc.",
    "WFC": "Wells Fargo & Co.", "JNJ": "Johnson & Johnson", "MRK": "Merck & Co.", "BE": "Bloom Energy",
    "CAT": "Caterpillar Inc.", "CVX": "Chevron Corp", "FCX": "Freeport-McMoRan", "FDX": "FedEx Corp",
    "GE": "General Electric", "HON": "Honeywell International", "LIN": "Linde plc", "LMT": "Lockheed Martin",
    "NEM": "Newmont Corp", "NUE": "Nucor Corp", "RTX": "RTX Corporation", "UNP": "Union Pacific Corp",
    "UPS": "United Parcel Service", "XOM": "Exxon Mobil Corp", "DUK": "Duke Energy", "GDX": "Gold Miners ETF",
    "IWM": "Russell 2000 ETF", "KRE": "Regional Banking ETF", "OIH": "Oil Services ETF", "PLD": "Prologis Inc", 
    "QQQ": "Nasdaq 100 ETF", "SMH": "Semiconductor ETF", "SPY": "S&P 500 ETF", "TAN": "Solar Energy ETF",
    "XBI": "Biotech ETF", "XLB": "Materials Sector ETF", "XLC": "Communication Services ETF", "XLE": "Energy Select ETF", 
    "XLF": "Financial Sector ETF", "XLI": "Industrials Sector ETF", "XLP": "Consumer Staples ETF",
    "XLRE": "Real Estate Sector ETF", "XLU": "Utilities Sector ETF", "XLV": "Healthcare Sector ETF",
    "XLY": "Consumer Discretionary ETF", "AIA.NZ": "Auckland International Airport", "CEN.NZ": "Contact Energy", 
    "CNU.NZ": "Chorus Ltd", "EBO.NZ": "Ebos Group", "FBU.NZ": "Fletcher Building", "FPH.NZ": "Fisher & Paykel Healthcare",
    "IFT.NZ": "Infratil Ltd", "MCY.NZ": "Mercury NZ", "MEL.NZ": "Meridian Energy", "MFT.NZ": "Mainfreight Ltd",
    "RYM.NZ": "Ryman Healthcare", "SPK.NZ": "Spark New Zealand", "ANZ.AX": "ANZ Group Holdings", 
    "BHP.AX": "BHP Group", "CBA.AX": "Commonwealth Bank of Australia", "CSL.AX": "CSL Limited", 
    "FMG.AX": "Fortescue Ltd", "MQG.AX": "Macquarie Group", "NAB.AX": "National Australia Bank",
    "REA.AX": "REA Group", "RIO.AX": "Rio Tinto", "TLS.AX": "Telstra Group", "WBC.AX": "Westpac Banking Corp",
    "WES.AX": "Wesfarmers Ltd", "WDS.AX": "Woodside Energy Group", "WOW.AX": "Woolworths Group", "XRO.AX": "Xero Ltd"
}

def calculate_indicators_only(df, fast_ma, slow_ma):
    df = df.copy()
    if df.empty or len(df) < max(fast_ma, slow_ma, 30): return df
    close_series, high_series, low_series = df['Close'].astype(float), df['High'].astype(float), df['Low'].astype(float)
    
    df['Fast_MA'] = close_series.rolling(window=int(fast_ma)).mean()
    df['Slow_MA'] = close_series.rolling(window=int(slow_ma)).mean()
    
    # --- CALCULATE LOWER BOLLINGER BAND ---
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
    """
    Performance Optimized: Reads directly from local JSON disk cache if TTL is valid.
    Moving average preference changes are calculated strictly in memory to bypass 
    unnecessary web API bottlenecks.
    """
    if os.path.exists(CACHE_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
        if datetime.now() - file_mod_time < timedelta(minutes=CACHE_TTL_MINUTES):
            try:
                df_cached = pd.read_json(CACHE_FILE)
                df_cached.index = pd.to_datetime(df_cached.index)
                df_cached.columns = pd.MultiIndex.from_tuples([eval(col) for col in df_cached.columns])
                return df_cached
            except Exception: pass
            
    try:
        df_live = yf.download(list(set(ticker_list)), start=start_date, interval="1wk", group_by='ticker', actions=False, threads=True, progress=False)
        if not df_live.empty:
            df_serializable = df_live.copy()
            df_serializable.columns = [str(col) for col in df_serializable.columns]
            df_serializable.to_json(CACHE_FILE)
        return df_live
    except Exception: return pd.DataFrame()
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: SCREENING LOOPS (PART 2 - HALF 2)
# ==============================================================================
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
lookback_start_date = datetime.now() - timedelta(days=lookback_days_map["2 Years"] + 250) # Keep 2y buffer available

RAW_MARKET_BATCH = fetch_all_market_data_batch(institutional_scan_pool, lookback_start_date)
breakout_rows, discount_rows, operational_dfs = [], [], {}
unique_scan_pool = list(dict.fromkeys(institutional_scan_pool))

for ticker in unique_scan_pool:
    hist_df = extract_ticker_dataframe(RAW_MARKET_BATCH, ticker)
    if hist_df.empty or len(hist_df) < max(fast_ma_input, slow_ma_input, 30): continue
    
    df_calc = calculate_indicators_only(hist_df, fast_ma_input, slow_ma_input)
    operational_dfs[ticker] = df_calc
    
    last_close = float(df_calc['Close'].iloc[-1])
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
    
    # --------------------------------------------------------------------------
    # ACTIVE 4-TIER TRAFFIC LIGHT STATUS HIERARCHY RULESET (SYNCHRONIZED)
    # --------------------------------------------------------------------------
    if last_close > fast_ma_val and last_close > slow_ma_val and volume_multiple >= 1.5:
        breakout_signal = "🌟 STRONG BUY"
    elif last_close > fast_ma_val and last_close <= slow_ma_val and volume_multiple >= 1.5:
        breakout_signal = "🟢 Bullish Turning (High Volume)"
    elif (last_close > fast_ma_val or last_close > slow_ma_val) and volume_multiple < 1.5:
        breakout_signal = "🟡 Bullish Turning (Low Volume)"
    else:
        breakout_signal = "🔴 Structural Bear"

    # Only include assets inside breakout_rows if they are showing constructive momentum
    if breakout_signal != "🔴 Structural Bear":
        safe_breakout_limit = round(fast_ma_val, 2)
        breakout_rows.append({
            "Market": market_label, "Ticker": ticker, "Company Name": local_name_map.get(ticker, f"{ticker} Leader"),
            "Live Price": last_close, "Alert Status": breakout_signal, "Limit Entry Target": safe_breakout_limit,
            "Vol Multiple": volume_multiple, "Daily Change %": pct_change, "RSI Momentum": rsi_val, "ATR Volatility": atr_val
        })

    if last_close <= (true_52w_low * 1.10):
        signal_label = "🟢 Bullish Turning" if macd_val > sig_val else "🔴 Bearish Floor"
        safe_limit_price = round(true_52w_low * 1.01, 2)
        
        discount_rows.append({
            "Market": market_label, "Ticker": ticker, "Company Name": local_name_map.get(ticker, f"{ticker} Leader"),
            "Live Price": last_close, "52W Low Floor": true_52w_low, "Limit Entry Target": safe_limit_price,
            "Lower Bollinger Band": bb_lower_val, "52W High Ceiling": true_52w_high,
            "Proximity to Low": proximity_to_low_pct, "RSI Status": rsi_val, "MACD Signal": signal_label
        })
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: DASHBOARD INTERFACE LAYOUT (PART 3 OF 3)
# ==============================================================================
tab_momentum, tab_discount = st.tabs(["🔥 Breakouts", "📉 Possible Value Discounts"])

with tab_momentum:
    st.markdown("<p class='small-header'>Potential Targets</p>", unsafe_allow_html=True)
    if breakout_rows:
        raw_m_df = pd.DataFrame(breakout_rows)
        # Strict mapping rank weights to ensure top setups hit top of dataframe view
        status_rank_map = {
            "🌟 STRONG BUY": 0, 
            "🟢 Bullish Turning (High Volume)": 1, 
            "🟡 Bullish Turning (Low Volume)": 2
        }
        raw_m_df["Rank_Weight"] = raw_m_df["Alert Status"].map(status_rank_map).fillna(3)
        
        # Sort primarily by Alert tier, and then sub-sort by biggest daily movers
        master_breakout_df = raw_m_df.sort_values(by=["Rank_Weight", "Daily Change %"], ascending=[True, False]).head(20)
        
        # --- PAGINATION LOGIC ---
        page_m = st.radio("Pagination Window Control:", ["Show Tickers 1–10", "Show Tickers 11–20"], horizontal=True, key="m_page_toggle")
        
        if page_m == "Show Tickers 1–10":
            sliced_breakout_df = master_breakout_df.iloc[0:10]
        else:
            sliced_breakout_df = master_breakout_df.iloc[10:20]
            
        momentum_tickers_ordered = sliced_breakout_df["Ticker"].tolist()
        cols_order = ["Market", "Ticker", "Company Name", "Alert Status", "Live Price", "Limit Entry Target", "ATR Volatility", "Vol Multiple", "Daily Change %", "RSI Momentum"]
        
        st.dataframe(
            apply_alpha_signal_theme(sliced_breakout_df[[c for c in cols_order if c in sliced_breakout_df.columns]]), 
            use_container_width=True, 
            hide_index=True, 
            height=440, 
            column_config={
                "Live Price": st.column_config.NumberColumn(format="$%.2f"), 
                "Limit Entry Target": st.column_config.NumberColumn("Pullback Limit Buy", format="$%.2f"),
                "ATR Volatility": st.column_config.NumberColumn("Daily ATR ($)", format="$%.2f"), 
                "Vol Multiple": st.column_config.NumberColumn("Volume Surge", format="%.2fx"), 
                "Daily Change %": st.column_config.NumberColumn(format="%+.2f%%"), 
                "RSI Momentum": st.column_config.NumberColumn(format="%.1f")
            }
        )
        
        st.markdown("---")
        if momentum_tickers_ordered:
            selected_m_ticker = st.radio("🛰 **Global Chart Engine Quick-Link Bar:**", options=momentum_tickers_ordered, horizontal=True, key="m_link_key")
            
            if selected_m_ticker in operational_dfs:
                chart_sliced = operational_dfs[selected_m_ticker].tail(chosen_lookback_days).copy().reset_index()
                if 'index' in chart_sliced.columns: 
                    chart_sliced = chart_sliced.rename(columns={'index': 'Date'})
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
        
        # --- PAGINATION LOGIC ---
        page_d = st.radio("Pagination Window Control:", ["Show Tickers 1–10", "Show Tickers 11–20"], horizontal=True, key="d_page_toggle")
        
        if page_d == "Show Tickers 1–10":
            sliced_discount_df = master_discount_df.iloc[0:10]
        else:
            sliced_discount_df = master_discount_df.iloc[10:20]
            
        discount_tickers_ordered = sliced_discount_df["Ticker"].tolist()
        cols_discount_order = ["Market", "Ticker", "Company Name", "Live Price", "52W Low Floor", "Limit Entry Target", "Lower Bollinger Band", "52W High Ceiling", "Proximity to Low", "RSI Status", "MACD Signal"]
        
        st.dataframe(
            sliced_discount_df[[c for c in cols_discount_order if c in sliced_discount_df.columns]], 
            use_container_width=True, 
            hide_index=True, 
            height=440, 
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

        st.markdown("---")
        if discount_tickers_ordered:
            selected_d_ticker = st.radio("🛰 **Global Chart Engine Quick-Link Bar:**", options=discount_tickers_ordered, horizontal=True, key="d_link_key")
            
            if selected_d_ticker in operational_dfs:
                chart_sliced = operational_dfs[selected_d_ticker].tail(chosen_lookback_days).copy().reset_index()
                if 'index' in chart_sliced.columns: 
                    chart_sliced = chart_sliced.rename(columns={'index': 'Date'})
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
