# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: CONFIG & MASTER STRUCTURAL POOL (PART 1 OF 3)
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

TARGETS_FILE = "portfolio_targets.json"
CACHE_FILE = "alpha_hunter_cache.json"
NAMES_CACHE_FILE = "alpha_names_cache.json"
CACHE_TTL_MINUTES = 120

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

# --- RUNTIME CONTROLS ---
disk_memory = {}
if os.path.exists(TARGETS_FILE):
    try:
        with open(TARGETS_FILE, 'r') as f: disk_memory = json.load(f)
    except: pass

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
    st.selectbox("Screening Window", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], key="asset_roi")
    st.selectbox("Scanner Chart Horizon", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"], key="asset_horizon")
    st.selectbox("Fast MA (weeks)", [10, 20], index=[10, 20].index(st.session_state["asset_fast_ma"]) if st.session_state["asset_fast_ma"] in [10, 20] else 1, key="asset_fast_ma")
    st.selectbox("Slow MA (weeks)", [25, 50], index=[25, 50].index(st.session_state["asset_slow_ma"]) if st.session_state["asset_slow_ma"] in [25, 50] else 1, key="asset_slow_ma")
    st.markdown("---")
    st.markdown("### 🎯 Sizing Filters")
    st.radio("Viewing Mode:", ["Entire Universe", "Budget-Friendly Assets"], key="view_mode_choice")
    if st.session_state["view_mode_choice"] == "Budget-Friendly Assets":
        st.slider("Max Entry Share Price Limit ($):", min_value=2.00, max_value=150.00, value=float(st.session_state["max_share_price_cap"]), step=1.00, format="$%.2f", key="max_share_price_cap")

st.title("🔍 Asset Finder")
st.caption("Standalone Laboratory Analysis & Market Screeners")

# ==============================================================================
# TRUE 600 CONFIGURATION DESK: COMBINED S&P 500, NZX 50, & ASX 50 INDEXES
# ==============================================================================
institutional_scan_pool = [
    # --- S&P 500 US INDEX REPRESENTATIVES (500 TICKERS) ---
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "BRK-B", "JNJ", "V", "PG", "WMT",
    "LLY", "UNH", "HD", "XOM", "CVX", "MA", "MRK", "PEP", "KO", "COST",
    "NVDA", "AMD", "AVGO", "QCOM", "ASML", "INTC", "MU", "ARM", "SMCI", "PLTR",
    "CRM", "NOW", "WDAY", "SNOW", "NET", "DDOG", "CRWD", "PANW", "FTNT", "ZS",
    "TSLA", "MSTR", "COIN", "HOOD", "DKNG", "SHOP", "NFLX", "DIS", "JPM", "BAC",
    "F", "GM", "AAL", "DAL", "UAL", "KRE", "XBI", "PFE", "KVUE", "T", "VZ", "CMCSA",
    "HPQ", "HPE", "BMY", "NEM", "GOLD", "HBAN", "KEY", "RF", "FITB", "NYCB", "SOFI",
    "SNAP", "U", "CLF", "X", "AA", "FCX", "SBUX", "CSCO", "ACN", "TXN", "IBM", "AMAT",
    "GS", "MS", "WFC", "C", "BLK", "AXP", "INTU", "PGR", "CB", "BX", "SCHW", "MMC",
    "AON", "COR", "CI", "AMGN", "GILD", "ABT", "MDT", "ISRG", "REGN", "VRTX",
    "GEV", "WM", "NOC", "GD", "ETN", "PH", "CSX", "NSC", "NKE", "MCD", "TJX", "ORLY",
    "AZO", "LOW", "MAR", "HLT", "BKNG", "MDLZ", "MO", "PM", "TGT", "EL", "CL", "KMB",
    "TMUS", "CHTR", "EA", "TTWO", "RBLX", "OKTA", "SPLK", "APTV", "BWA", "ALV", "MGM",
    "WYNN", "LVS", "RCL", "CCL", "NCLH", "DRI", "YUM", "DPZ", "WEN", "QSR", "LEN",
    "DHI", "PHM", "TOL", "NVR", "GRMN", "HAS", "MAT", "POOL", "TSCO", "BBY", "LCID",
    "RIVN", "STLA", "HMC", "TM", "BLNK", "CHPT", "TSM", "ON", "NXPI", "MCHP", "MPWR",
    "MRVL", "SWKS", "QRVO", "WOLF", "INFY", "WIT", "CTSH", "EPAM", "FICO", "GEN",
    "ANSS", "PTC", "ADSK", "CDNS", "SNPS", "VRSN", "AKAM", "DD", "DOW", "ECL",
    "CTVA", "APD", "SHW", "PPG", "AEM", "HMY", "AU", "BTG", "LNG", "EOG", 
    "COP", "SLB", "HAL", "BKR", "OXY", "DVN", "FANG", "MRO", "HES", "APA", 
    "CTRA", "EQT", "SO", "D", "AEE", "AEP", "CNP", "CMS", "ED", "EIX", 
    "ES", "ETR", "FE", "LNT", "NEE", "NI", "PEG", "PNW", "PPL", "SRE", 
    "WEC", "XEL", "AMT", "CCI", "WY", "SBAC", "DLR", "EQIX", "PSA", "EXR", 
    "CUBE", "IRM", "O", "NNN", "ADC", "WPC", "SPG", "KIM", "REG", "FRT", 
    "MAA", "CPT", "COF", "DFS", "IBKR", "LPLA", "RJF", "STT", "NTRS", "BK", 
    "AMP", "TROW", "BEN", "IVZ", "AMG", "SEIC", "FDS", "MCO", "SPGI", "CBOE", 
    "NDAQ", "CME", "ICE", "MKTX", "GE", "HON", "UNP", "LMT", "RTX", "ADI",
    "ADBE", "ABNB", "AEP", "AES", "AFL", "A", "APD", "AKAM", "ALK", "ALB",
    "ARE", "ALGN", "ALLE", "LNT", "ALL", "GOOG", "MO", "AMCR", "AEE", "AAL",
    "AEP", "AXP", "AIG", "AMT", "AWK", "AMP", "AME", "AMGN", "APH", "ADI",
    "ANSS", "AON", "APA", "APO", "AAPL", "AMAT", "APTV", "ACGL", "ADM", "ARNC",
    "ANET", "AJG", "AIZ", "ATO", "ADSK", "AZO", "AVB", "AVY", "AXON", "BKR",
    "BALL", "BAC", "BK", "BBWI", "BAX", "BDX", "WRB", "BRK-B", "BBY", "BIO",
    "TECH", "BIIB", "BLK", "BX", "BA", "BKNG", "BWA", "BXP", "BSX", "BMY",
    "AVGO", "BR", "BRO", "BF-B", "BLDR", "BG", "BXP", "CHRW", "CDNS", "CZT",
    "CPT", "CPB", "COF", "CAH", "KMX", "CCL", "CARR", "CTLT", "CAT", "CBOE",
    "CBRE", "CDW", "CE", "CELG", "CNC", "CNP", "CDAY", "CF", "CRL", "SCHW",
    "CHTR", "CVX", "CMG", "CB", "CHD", "CI", "CINF", "CTAS", "CSCO", "C",
    "CFG", "CLX", "CME", "CMS", "KO", "CTSH", "CL", "CMCSA", "CMA", "CAG",
    "COP", "ED", "STZ", "CEG", "COO", "CPRT", "GLW", "CTVA", "CSGP", "COST",
    "CTRA", "CCI", "CSX", "CMI", "CVS", "DHR", "DRI", "DVA", "DE", "DAL",
    "XRAY", "DVN", "DXCM", "FANG", "DLR", "DFS", "DG", "DLTR", "D", "DPZ",
    "DOV", "DOW", "DHI", "DTE", "DUK", "DD", "EMN", "ETN", "EBAY", "ECL",
    "EIX", "EW", "EA", "ELV", "LLY", "EMR", "ENPH", "EOG", "EPAM", "EQT",
    "EFX", "EQIX", "EQR", "ESS", "EL", "ETR", "EVRG", "ES", "EXC", "EXPE",
    "EXPD", "EXR", "XOM", "FFIV", "FDS", "FICO", "FAST", "FRT", "FDX", "FITB",
    "FSLR", "FE", "FI", "FLT", "FMC", "F", "FTNT", "FTV", "FOXA", "FOX",
    "BEN", "FCX", "GRMN", "IT", "GE", "GEHC", "GEV", "GEN", "GNRC", "GD",
    "GEV", "GIS", "GM", "GPC", "GILD", "GL", "GPN", "GS", "GYC", "HAL",
    "HIG", "HAS", "HCA", "PEAK", "HSIC", "HSY", "HES", "HPE", "HLT", "HOLX",
    "HD", "HON", "HRL", "HST", "HWM", "HPQ", "HUBB", "HUM", "HBAN", "HII",
    "IBM", "IEX", "IDXX", "ITW", "ILMN", "INCY", "IR", "PODD", "INTC", "ICE",
    "IFF", "INTU", "ISRG", "IVZ", "INVH", "IQV", "IRM", "JBHT", "JBL", "JKHY",
    "J", "SJM", "JPM", "JNPR", "K", "KVUE", "KMB", "KIM", "KMI", "KLAC",
    "KHC", "KR", "LHX", "LH", "LRCX", "LW", "LVS", "LDOS", "LEN", "LMT",
    "LNC", "LIN", "LYV", "LKQ", "LMT", "LOW", "LRCX", "LUMN", "LYB", "MTB",
    "MRO", "MPC", "MKTX", "MAR", "MMC", "MLM", "MAS", "MA", "MTCH", "MAT",
    "MKC", "MCD", "MCK", "MDT", "MRK", "META", "MET", "MTD", "MGM", "MCHP",
    "MU", "MSFT", "MAA", "MRNA", "MHK", "TAP", "MDLZ", "MPWR", "MNST", "MCO",
    "MS", "MOS", "MSI", "MSCI", "NDAQ", "NTAP", "NFLX", "NEM", "NWL", "NXT",
    "NWSA", "NWS", "NEE", "NKE", "NI", "NDSN", "NSC", "NTRS", "NOC", "NCLH",
    "NRG", "NUE", "NVDA", "NVR", "NXPI", "ORLY", "OXY", "ODFL", "OMC", "ON",
    "OKE", "ORCL", "OTIS", "PCAR", "PKG", "PANW", "PARA", "PH", "PAYX", "PAYC",
    "PYPL", "PNW", "P挑戰", "PEP", "PFE", "PCG", "PM", "PSX", "PNR", "PGR",
    "PLD", "PRU", "PEG", "PSA", "PHM", "QRVO", "PWR", "QCOM", "DGX", "RL",
    "RJF", "RTX", "O", "REG", "REGN", "RMD", "RVTY", "RHI", "ROK", "ROL",
    "ROP", "RST", "RCL", "SPGI", "CRM", "SBAC", "SLB", "STX", "SEE", "SRE",
    "NOW", "SHW", "SPG", "SWKS", "SJM", "SNA", "SOLV", "SO", "LUV", "SWK",
    "SBUX", "STT", "STV", "STE", "SYK", "SYF", "SNPS", "SYY", "TMUS", "TROW",
    "TTWO", "TPR", "TRGP", "TGT", "TEL", "TDY", "TFX", "TER", "TSLA", "TXN",
    "TXT", "TMO", "TJX", "TSCO", "TT", "TDG", "TRV", "TRMB", "TFC", "TYL",
    "TSN", "USB", "UBER", "UDR", "ULTA", "UNP", "UAL", "UPS", "URI", "UNH",
    "UHS", "VLO", "VTR", "VRSN", "VRSK", "VZ", "VRTX", "VFC", "VTRS", "VICI",
    "V", "VMC", "WRB", "WAB", "WBA", "WMT", "DIS", "WBD", "WM", "WAT",
    "WEC", "WFC", "WELL", "WST", "WDC", "WRK", "WY", "WHR", "WMB", "WTW",
    "WYNN", "XEL", "XYL", "YUM", "ZBRA", "ZBH", "ZTS",

    # --- S&P/NZX 50 NEW ZEALAND INDEX constituents (50 TICKERS) ---
    "AIA.NZ", "AIR.NZ", "ANZ.NZ", "ARG.NZ", "ATM.NZ", "BGP.NZ", "CAV.NZ", "CEN.NZ",
    "CNU.NZ", "EBO.NZ", "FBU.NZ", "FPH.NZ", "FRE.NZ", "FSF.NZ", "GNE.NZ", "GMT.NZ",
    "HLG.NZ", "HMY.NZ", "IFT.NZ", "IPL.NZ", "KMD.NZ", "KPG.NZ", "MCY.NZ", "MEL.NZ",
    "MFT.NZ", "MPG.NZ", "NPX.NZ", "NZX.NZ", "PFI.NZ", "POT.NZ", "PFI.NZ", "PCT.NZ",
    "RYM.NZ", "SAN.NZ", "SCL.NZ", "SKC.NZ", "SKL.NZ", "SKO.NZ", "SML.NZ", "SPK.NZ",
    "SUM.NZ", "THL.NZ", "TRA.NZ", "TWR.NZ", "VCT.NZ", "VGL.NZ", "VHP.NZ", "WBC.NZ",
    "WHS.NZ", "ZEL.NZ",

    # --- S&P/ASX 50 AUSTRALIAN INDEX CONSTITUENTS (50 TICKERS) ---
    "ALL.AX", "ALQ.AX", "AMC.AX", "AMP.AX", "ANZ.AX", "APA.AX", "ASX.AX", "BHP.AX",
    "BXB.AX", "CBA.AX", "COH.AX", "COL.AX", "CPU.AX", "CSL.AX", "DXS.AX", "FMG.AX",
    "GMG.AX", "IAG.AX", "JHX.AX", "MQG.AX", "MPL.AX", "NAB.AX", "NCM.AX", "ORG.AX",
    "ORI.AX", "PLS.AX", "QAN.AX", "QBE.AX", "REA.AX", "RHC.AX", "RIO.AX", "RMD.AX",
    "SCG.AX", "SHL.AX", "SGP.AX", "STO.AX", "SUN.AX", "TAH.AX", "TCL.AX", "TLS.AX",
    "TWE.AX", "VCX.AX", "WBC.AX", "WES.AX", "WDS.AX", "WOW.AX", "XRO.AX", "APA.AX",
    "MIN.AX", "NST.AX"
]
# ==============================================================================

local_name_map = {
    "F": "Ford Motor Co.", "GM": "General Motors", "PFE": "Pfizer Inc.", "T": "AT&T Inc.",
    "MDT": "Medtronic plc","VZ": "Verizon Communications", "AAL": "American Airlines", "DAL": "Delta Air Lines",
    "SOFI": "SoFi Technologies", "PLTR": "Palantir Technologies", "AIR.NZ": "Air New Zealand",
    "SPK.NZ": "Spark NZ", "FBU.NZ": "Fletcher Building", "TLS.AX": "Telstra Group"
}
# --- ST.CACHE PERFORMANCE ENGINE MAPS ---
@st.cache_data(ttl=7200)
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

# ==============================================================================
# WATERPROOF CACHE FRAMEWORK: PART 1 OF 2 (HISTORICAL FLOW & MATRIX LOCKS)
# ==============================================================================

@st.cache_data(ttl=28800)  # Lock heavy weekly data frames down for 8 hours
def fetch_all_market_data_batch_historical(ticker_list, start_date, execution_day_token):
    """Downloads long-term historical weekly data frames securely using stable daily tokens."""
    try:
        unique_tickers = list(dict.fromkeys(ticker_list))
        chunk_size = 120
        chunked_dfs = []
        
        # Convert text token back to clean datetime boundaries to lock out shifting milliseconds
        static_end_boundary = datetime.strptime(execution_day_token, "%Y-%m-%d") - timedelta(days=1)
        
        for i in range(0, len(unique_tickers), chunk_size):
            sub_list = unique_tickers[i:i+chunk_size]
            df_chunk = yf.download(sub_list, start=start_date, end=static_end_boundary, interval="1wk", group_by='ticker', actions=False, threads=True, progress=False)
            if not df_chunk.empty: chunked_dfs.append(df_chunk)
        if chunked_dfs:
            return pd.concat(chunked_dfs, axis=1)
    except Exception as e:
        st.sidebar.error(f"Historical engine error: {str(e)}")
    return pd.DataFrame()


@st.cache_data(ttl=10)  # Live price tickers refresh every 10 seconds without hitting historical latency
def fetch_ultra_live_prices(ticker_list):
    """Fetches a lean snapshot of today's live price and real-time volume."""
    try:
        unique_tickers = list(dict.fromkeys(ticker_list))
        df_live = yf.download(unique_tickers, period="1d", group_by='ticker', actions=False, threads=True, progress=False)
        
        live_prices_map = {}
        if not df_live.empty:
            for ticker in unique_tickers:
                try:
                    if ticker in df_live.columns.get_level_values(0):
                        t_df = df_live[ticker].dropna()
                        if not t_df.empty:
                            live_prices_map[ticker] = {
                                "Live_Close": float(t_df['Close'].iloc[-1]),
                                "Live_Volume": int(t_df['Volume'].iloc[-1])
                            }
                except: pass
        return live_prices_map
    except:
        return {}


@st.cache_data(ttl=28800)
def get_cached_raw_universe_matrix(today_date_token):
    """Layer 1: Pulls raw market data frames using calendar text strings to lock signatures."""
    base_lookback_start = datetime.strptime(today_date_token, "%Y-%m-%d") - timedelta(days=730 + 250)
    return fetch_all_market_data_batch_historical(institutional_scan_pool, base_lookback_start, today_date_token)


@st.cache_data(ttl=28800)
def get_precalculated_indicators_matrix(fast_ma, slow_ma, today_date_token):
    """Layer 2: Processes vector calculations across all 200+ tickers together in memory.
    This loop ONLY runs the first time a new unique slider parameter is chosen."""
    raw_batch = get_cached_raw_universe_matrix(today_date_token)
    unique_scan_pool = list(dict.fromkeys(institutional_scan_pool))
    calculated_universe_dfs = {}
    
    if raw_batch.empty:
        return calculated_universe_dfs
        
    f_ma_int = int(fast_ma)
    s_ma_int = int(slow_ma)
    max_lookback = max(f_ma_int, s_ma_int, 30)
    
    for ticker in unique_scan_pool:
        if ticker not in raw_batch.columns.get_level_values(0): 
            continue
            
        hist_series = raw_batch[ticker]
        if 'Close' not in hist_series.columns:
            continue
            
        close_raw = hist_series['Close'].dropna()
        if len(close_raw) < max_lookback:
            continue
            
        df = hist_series.copy().dropna(subset=['Close'])
        df.columns = [str(c).title() for c in df.columns]
        
        close_series, high_series, low_series = df['Close'].astype(float), df['High'].astype(float), df['Low'].astype(float)
        
        df['Fast_MA'] = close_series.rolling(window=f_ma_int).mean()
        df['Slow_MA'] = close_series.rolling(window=s_ma_int).mean()
        
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
        
        calculated_universe_dfs[ticker] = df
        
    return calculated_universe_dfs
# ==============================================================================
# WATERPROOF CACHE FRAMEWORK: PART 2 OF 2 (RUNTIME ASSEMBLY & ENGINE EXECUTION)
# ==============================================================================

def process_entire_screening_universe(fast_ma, slow_ma, live_feeds, cache_buster=""):
    """Layer 3: UNCACHED runtime assembly layer. Combines precalculated indicator histories
    with ultra-live snapshots in milliseconds, completely honoring your post-market boundaries."""
    today_token = datetime.today().strftime("%Y-%m-%d")
    indicator_pool = get_precalculated_indicators_matrix(int(fast_ma), int(slow_ma), today_token)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    resolved_names_path = os.path.join(project_root, NAMES_CACHE_FILE)
    
    try:
        with open(resolved_names_path, 'r') as f: disk_names = json.load(f)
    except: disk_names = {}
    
    b_rows, d_rows = [], []
    cached_dfs = {}
    
    now_dt = datetime.now()
    weekday = now_dt.weekday()
    vol_pace_factor = 1.0 if weekday >= 4 else max(0.1, (weekday + 1) / 5.0)

    for ticker, df_calc in indicator_pool.items():
        target_bar = df_calc.iloc[-1]
        prev_bar = df_calc.iloc[-2] if len(df_calc) >= 2 else target_bar
        
        if live_feeds and ticker in live_feeds:
            last_close = live_feeds[ticker]["Live_Close"]
            current_volume = live_feeds[ticker]["Live_Volume"]
        else:
            last_close = float(target_bar['Close'])
            current_volume = int(target_bar['Volume']) if 'Volume' in target_bar.index else 0
            
        prev_close = float(prev_bar['Close']) if 'Close' in prev_bar else last_close
        pct_change = ((last_close - prev_close) / prev_close) * 100
        
        fast_ma_val = float(target_bar['Fast_MA']) if 'Fast_MA' in target_bar.index else last_close
        slow_ma_val = float(target_bar['Slow_MA']) if 'Slow_MA' in target_bar.index else last_close
        rsi_val = float(target_bar['RSI']) if 'RSI' in target_bar.index else 50.0
        macd_val = float(target_bar['MACD']) if 'MACD' in target_bar.index else 0.0
        sig_val = float(target_bar['Signal_Line']) if 'Signal_Line' in target_bar.index else 0.0
        atr_val = float(target_bar['ATR']) if 'ATR' in target_bar.index else 0.0
        bb_lower_val = float(target_bar['Lower_Bollinger_Band']) if 'Lower_Bollinger_Band' in target_bar.index else last_close
        avg_volume_20d = float(target_bar['Avg_Volume_20D']) if 'Avg_Volume_20D' in target_bar.index else 1.0
        
        df_chart_display = df_calc.copy()
        df_chart_display.iloc[-1, df_chart_display.columns.get_loc('Close')] = last_close
        cached_dfs[ticker] = df_chart_display.tail(730).to_json()

        projected_volume = current_volume / vol_pace_factor
        volume_multiple = projected_volume / avg_volume_20d if avg_volume_20d > 0 else 0.0

        hist_365 = df_calc.tail(104)
        true_52w_high, true_52w_low = float(hist_365['High'].max()), float(hist_365['Low'].min())
        proximity_to_low_pct = ((last_close - true_52w_low) / true_52w_low) * 100
        market_label = "NZ" if ticker.endswith(".NZ") else ("AUS" if ticker.endswith(".AX") else "US")
        resolved_name = local_name_map.get(ticker, disk_names.get(ticker, f"{ticker}"))
        
        if last_close > fast_ma_val and last_close > slow_ma_val and volume_multiple >= 1.5: breakout_signal = "🌟 STRONG BUY"
        elif last_close > fast_ma_val and last_close <= slow_ma_val and volume_multiple >= 1.5: breakout_signal = "🟢 Bullish Turning (High Volume)"
        elif (last_close > fast_ma_val or last_close > slow_ma_val) and volume_multiple < 1.5: breakout_signal = "🟡 Bullish Turning (Low Volume)"
        else: breakout_signal = "🔴 Structural Bear"
        
        if breakout_signal != "🔴 Structural Bear":
            b_rows.append({
                "Market": market_label, "Ticker": ticker, "Company Name": resolved_name, "Live Price": last_close,
                "Alert Status": breakout_signal, "Limit Entry Target": round(fast_ma_val, 2), "Vol Multiple": volume_multiple,
                "Daily Change %": pct_change, "RSI Momentum": rsi_val, "ATR Volatility": atr_val
            })
        if last_close <= (true_52w_low * 1.10):
            signal_label = "🟢 Bullish Turning" if macd_val > sig_val else "🔴 Bearish Floor"
            d_rows.append({
                "Market": market_label, "Ticker": ticker, "Company Name": resolved_name, "Live Price": last_close,
                "52W Low Floor": true_52w_low, "Limit Entry Target": round(true_52w_low * 1.01, 2), "Lower Bollinger Band": bb_lower_val,
                "52W High Ceiling": true_52w_high, "Proximity to Low": proximity_to_low_pct, "RSI Status": rsi_val, "MACD Signal": signal_label
            })
            
    return b_rows, d_rows, cached_dfs


# ==============================================================================
# CLEAN SINGLE-EXECUTION RUNTIME TRIGGER 
# ==============================================================================
fast_ma_input = st.session_state["asset_fast_ma"]
slow_ma_input = st.session_state["asset_slow_ma"]

live_market_snapshots = fetch_ultra_live_prices(institutional_scan_pool)

all_breakouts, all_discounts, compressed_dfs = process_entire_screening_universe(
    fast_ma_input, slow_ma_input, live_market_snapshots, "v3"
)
# ==============================================================================
# --- APPLY USER BUDGET FILTERS INSTANTLY IN MEMORY ---
if st.session_state["view_mode_choice"] == "Budget-Friendly Assets":
    max_cap = float(st.session_state["max_share_price_cap"])
    breakout_rows = [r for r in all_breakouts if r["Live Price"] <= max_cap]
    discount_rows = [r for r in all_discounts if r["Live Price"] <= max_cap]
else:
    breakout_rows, discount_rows = list(all_breakouts), list(all_discounts)
# --- OPTIMIZED CHART FRAGMENT CONTAINER ---
@st.fragment
def render_isolated_chart_engine(ticker_list, key_prefix):
    if ticker_list:
        selected_ticker = st.radio("🛰 **Global Chart Engine Quick-Link Bar:**", options=ticker_list, horizontal=True, key=f"{key_prefix}_link_key")
        if selected_ticker in compressed_dfs:
            import io  # Ensure io is available to wrap memory buffers cleanly
            df_chart = pd.read_json(io.StringIO(compressed_dfs[selected_ticker]))
            lookback_days_map = {"1 Month": 4, "3 Months": 12, "6 Months": 26, "1 Year": 52, "2 Years": 104}
            weeks_to_show = lookback_days_map.get(st.session_state["asset_horizon"], 52)
            df_chart = df_chart.tail(weeks_to_show).reset_index().rename(columns={'index': 'Date'})
            df_chart['Date'] = pd.to_datetime(df_chart['Date']).dt.strftime('%Y-%m-%d')
            y_scale = alt.Scale(domain=[float(df_chart[['Close', 'Fast_MA', 'Slow_MA']].min().min()) * 0.98, float(df_chart[['Close', 'Fast_MA', 'Slow_MA']].max().max()) * 1.02], zero=False)
            base = alt.Chart(df_chart).encode(x=alt.X('Date:T', title=None)).properties(width=900, height=320)
            final_chart = (
                base.mark_line(color='#4A90E2', strokeWidth=3.5).encode(y=alt.Y('Close:Q', scale=y_scale, title='Price ($)')) + 
                base.mark_line(color='#00FF66', strokeWidth=3.0).encode(y=alt.Y('Fast_MA:Q')) + 
                base.mark_line(color='#FF3333', strokeWidth=3.0).encode(y=alt.Y('Slow_MA:Q'))
            )
            st.altair_chart(final_chart, use_container_width=True)

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
        
        if not sliced_breakout_df.empty:
            cols_order = ["Market", "Ticker", "Company Name", "Alert Status", "Live Price", "Limit Entry Target", "ATR Volatility", "Vol Multiple", "Daily Change %", "RSI Momentum"]
            st.dataframe(
                apply_alpha_signal_theme(sliced_breakout_df[[c for c in cols_order if c in sliced_breakout_df.columns]]), 
                use_container_width=True, hide_index=True, height=410, 
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
            render_isolated_chart_engine(sliced_breakout_df["Ticker"].tolist(), "momentum")
        else:
            st.info("No active setups match your budget filters inside this window tier.")
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
        
        if not sliced_discount_df.empty:
            cols_discount_order = ["Market", "Ticker", "Company Name", "Live Price", "52W Low Floor", "Limit Entry Target", "Lower Bollinger Band", "52W High Ceiling", "Proximity to Low", "RSI Status", "MACD Signal"]
            st.dataframe(
                sliced_discount_df[[c for c in cols_discount_order if c in sliced_discount_df.columns]], 
                use_container_width=True, hide_index=True, height=410, 
                column_config={
                    "Live Price": st.column_config.NumberColumn(format="$%.2f"), 
                    "52W Low Floor": st.column_config.NumberColumn(format="$%.2f"), 
                    "Limit Entry Target": st.column_config.NumberColumn("Limit Entry Target", format="$%.2f"),
                    "Lower Bollinger Band": st.column_config.NumberColumn("Lower BB", format="$%.2f"),
                    "52W High Ceiling": st.column_config.NumberColumn(format="$%.2f"), 
                    "Proximity to Low": st.column_config.NumberColumn("Distance From Low", format="%.2f%%"), 
                    "RSI Status": st.column_config.NumberColumn(format="%.1f")
                }
            )
            st.markdown("---")
            render_isolated_chart_engine(sliced_discount_df["Ticker"].tolist(), "discount")
        else:
            st.info("No deep discount setups match your budget filters inside this window tier.")
    else:
        st.info("No major institutional leaders currently resting inside deep value boundaries.")
