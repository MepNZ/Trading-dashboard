# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: CONFIG & STYLING LAYERS (CHUNK 1 OF 6)
# ==============================================================================
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import altair as alt
import io
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_custom_file_company_map():
    """
    Loads your exact CSV structural layout directly into session memory.
    If the ticker_names.csv file is found on your laptop, it parses it.
    Otherwise, it defaults to a clean backup memory cache.
    """
    import os
    if 'company_name_map' not in st.session_state:
        csv_path = "ticker_names.csv"
        parsed_dictionary = {}
        
        if os.path.exists(csv_path):
            try:
                df_names = pd.read_csv(csv_path)
                df_names['Ticker'] = df_names['Ticker'].astype(str).str.strip()
                df_names['True_Name'] = df_names['True_Name'].astype(str).str.strip()
                parsed_dictionary = dict(zip(df_names['Ticker'], df_names['True_Name']))
            except Exception:
                pass
                
        st.session_state.company_name_map = parsed_dictionary
        
        return st.session_state.company_name_map

st.set_page_config(
    page_title="Asset Finder",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

def apply_alpha_signal_theme(df):
    def style_breakout_rows(row):
        styles = [''] * len(row)
        vol_multiple = float(row['Vol Multiple']) if 'Vol Multiple' in row.index else 0.0
        alert_status = str(row['Alert Status']) if 'Alert Status' in row.index else ""
        elite_statuses = ["🌟 STRONG BUY", "🟩 BULLISH BREAKOUT", "🟢 Bullish Turning (High Volume)"]
        if alert_status in elite_statuses and vol_multiple >= 2.5:
            return ['background-color: #0A1128; color: #00E5FF; font-weight: 700; border: 1px solid #00E5FF;'] * len(row)
        if 'Alert Status' in row.index:
            idx = row.index.get_loc('Alert Status')
            if alert_status == "🌟 STRONG BUY": styles[idx] = 'background-color: #0A1128; color: #00E5FF; font-weight: bold;'
            elif alert_status == "🟩 BULLISH BREAKOUT": styles[idx] = 'background-color: #1a2e3b; color: #38bdf8; font-weight: bold;'
            elif alert_status == "🟢 Bullish Turning (High Volume)": styles[idx] = 'background-color: #1e3a1e; color: #38ef7d; font-weight: bold;'
            elif alert_status == "🟡 Bullish Turning (Low Volume)": styles[idx] = 'background-color: #3a351e; color: #f1c40f; font-weight: bold;'
            elif alert_status == "🔴 Structural Bear": styles[idx] = 'background-color: #3a1e1e; color: #e74c3c; font-weight: bold;'
        return styles
    return df.style.apply(style_breakout_rows, axis=1)

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
    st.slider("Fast Moving Average (MA)", min_value=5, max_value=30, value=st.session_state["asset_fast_ma"], step=1, key="asset_fast_ma")
    st.slider("Slow Moving Average (MA)", min_value=20, max_value=150, value=st.session_state["asset_slow_ma"], step=5, key="asset_slow_ma")
    st.markdown("---")
    st.markdown("### 🎯 Sizing Filters")
    st.radio("Viewing Mode:", ["Entire Universe", "Budget-Friendly Assets"], key="view_mode_choice")
    if st.session_state["view_mode_choice"] == "Budget-Friendly Assets":
        st.slider("Max Entry Share Price Limit ($):", min_value=2.00, max_value=150.00, value=float(st.session_state["max_share_price_cap"]), step=1.00, format="$%.2f", key="max_share_price_cap")

st.title("🔍 Asset Finder")
st.caption("Standalone Laboratory Analysis & Market Screeners")
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: UNIVERSE MATRIX POOLS (CHUNK 2 OF 6)
# ==============================================================================
institutional_scan_pool = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "BRK-B", "JNJ", "V", "PG", "WMT",
    "LLY", "UNH", "HD", "XOM", "CVX", "MA", "MRK", "PEP", "KO", "COST",
    "NVDA", "AMD", "AVGO", "QCOM", "ASML", "INTC", "MU", "ARM", "SMCI", "PLTR",
    "CRM", "NOW", "WDAY", "SNOW", "NET", "DDOG", "CRWD", "PANW", "FTNT", "ZS",
    "TSLA", "MSTR", "COIN", "HOOD", "DKNG", "SHOP", "NFLX", "DIS", "JPM", "BAC",
    "F", "GM", "DAL", "UAL", "KRE", "XBI", "PFE", "KVUE", "T", "VZ", "CMCSA",
    "HPQ", "HPE", "BMY", "NEM", "GOLD", "HBAN", "KEY", "RF", "FITB", "SOFI",
    "SNAP", "U", "CLF", "AA", "FCX", "SBUX", "CSCO", "ACN", "TXN", "AMAT",
    "GS", "MS", "WFC", "C", "BLK", "AXP", "INTU", "PGR", "CB", "BX", "SCHW",
    "AON", "COR", "CI", "AMGN", "GILD", "ABT", "MDT", "ISRG", "REGN", "VRTX",
    "GEV", "WM", "NOC", "GD", "ETN", "PH", "CSX", "NSC", "NKE", "MCD", "TJX", "ORLY",
    "AZO", "LOW", "MAR", "HLT", "BKNG", "MDLZ", "MO", "PM", "TGT", "EL", "CL", "KMB",
    "TMUS", "CHTR", "TTWO", "RBLX", "OKTA", "APTV", "BWA", "ALV", "MGM",
    "WYNN", "LVS", "RCL", "CCL", "NCLH", "DRI", "YUM", "DPZ", "WEN", "QSR", "LEN",
    "DHI", "PHM", "TOL", "NVR", "GRMN", "HAS", "MAT", "POOL", "TSCO", "BBY", "LCID",
    "RIVN", "STLA", "HMC", "TM", "BLNK", "CHPT", "TSM", "ON", "NXPI", "MCHP", "MPWR",
    "MRVL", "SWKS", "WOLF", "INFY", "WIT", "CTSH", "EPAM", "FICO", "GEN",
    "PTC", "ADSK", "CDNS", "SNPS", "VRSN", "AKAM", "DD", "DOW", "ECL",
    "CTVA", "APD", "SHW", "PPG", "AEM", "HMY", "AU", "BTG", "LNG", "EOG", 
    "COP", "SLB", "HAL", "BKR", "OXY", "DVN", "FANG", "APA", 
    "EQT", "SO", "D", "AEE", "AEP", "CNP", "CMS", "ED", "EIX", 
    "ES", "ETR", "FE", "LNT", "NEE", "NI", "PEG", "PNW", "PPL", "SRE", 
    "WEC", "XEL", "AMT", "CCI", "WY", "SBAC", "DLR", "EQIX", "PSA", "EXR",
    "CUBE", "IRM", "O", "NNN", "ADC", "WPC", "SPG", "KIM", "REG", "FRT", 
    "MAA", "CPT", "COF", "IBKR", "LPLA", "RJF", "STT", "NTRS", 
    "AMP", "TROW", "BEN", "IVZ", "AMG", "SEIC", "FDS", "MCO", "SPGI", "CBOE", 
    "NDAQ", "CME", "ICE", "MKTX", "GE", "HON", "UNP", "RTX", "ADI",
    "ADBE", "ABNB", "AFL", "A", "ALK", "ALB", "ARE", "ALGN", "ALLE", "ALL",
    "GOOG", "AMCR", "AIG", "AWK", "AME", "APH", "APO", "ADM", "ANET", "AJG", "AIZ", "ATO",
    "AVY", "AXON", "BALL", "BBWI", "BAX", "BDX", "WRB", "BIO", "TECH", "BIIB", "BA",
    "BXP", "BSX", "BR", "BRO", "BF-B", "BLDR", "BG", "CHRW", "CAH", "KMX", 
    "CARR", "CAT", "CBRE", "CDW", "CE", "CNC", "CRL", "CMG", "CHD", "CINF",
    "CTAS", "CFG", "CLX", "CAG", "STZ", "CEG", "COO", "CPRT", "GLW",
    "CSGP", "CVS", "DHR", "DVA", "DE", "XRAY", "DXCM", "DG", "DLTR",
    "FMC", "FTV", "FOXA", "FOX", "FSLR", "IT", "GEHC", "GNRC", "GIS", "GPC", "GL", "GPN",
    "HIG", "HCA", "HSIC", "HSY", "HRL", "HST", "HWM", "HUBB", "HUM", "HII",
    "IEX", "IDXX", "ITW", "ILMN", "INCY", "IR", "PODD", "IFF",
    "INVH", "IQV", "JBHT", "JBL", "JKHY", "J", "SJM", "KMI", "KLAC", "KHC", "KR", "LHX",
    "LH", "LRCX", "LW", "LDOS", "LNC", "LYV", "LKQ", "LUMN", "LYB", "MTB", "MPC", "MLM",
    "MAS", "MTCH", "MKC", "MCK", "MET", "MTD", "MRNA", "MHK", "TAP", "MNST",
    "MOS", "MSI", "MSCI", "NTAP", "NWL", "NXT", "NWSA", "NWS", "NDSN", "NRG", "NUE",
    "ODFL", "OMC", "ORCL", "OTIS", "PCAR", "PKG", "PARA", "PAYX", "PAYC", "PYPL", "PCG",
    "PSX", "PNR", "PRU", "PWR", "DGX", "RL", "RMD", "RVTY", "RHI", "ROK", "ROL", "ROP",
    "STX", "SNA", "SOLV", "LUV", "SWK", "STE", "SYK", "SYF", "SYY", "TPR",
    "TRGP", "TDY", "TFX", "TER", "TXT", "TMO", "TT", "TDG", "TRV", "TRMB", "TFC", "TYL", "TSN",
    "USB", "UBER", "UDR", "ULTA", "UPS", "URI", "UHS", "VLO", "VTR", "VRSK", "VFC", "VTRS",
    "VICI", "VMC", "WAB", "WAT", "WELL", "WST", "WDC", "WMB", "WHR", "ZBRA", "ZBH", "ZTS",
    "AIA.NZ", "AIR.NZ", "ANZ.NZ", "ARG.NZ", "ATM.NZ", "BGP.NZ", "CEN.NZ", "CNU.NZ", "EBO.NZ",
    "FBU.NZ", "FPH.NZ", "FSF.NZ", "GNE.NZ", "HLG.NZ", "IFT.NZ", "IPL.NZ", "KMD.NZ", "KPG.NZ",
    "MCY.NZ", "MEL.NZ", "MFT.NZ", "MPG.NZ", "NZX.NZ", "PFI.NZ", "POT.NZ", "PCT.NZ", "RYM.NZ",
    "SAN.NZ", "SCL.NZ", "SKC.NZ", "SKL.NZ", "SKO.NZ", "SML.NZ", "SPK.NZ", "SUM.NZ", "THL.NZ",
    "TRA.NZ", "TWR.NZ", "VCT.NZ", "VGL.NZ", "VHP.NZ", "WBC.NZ", "WHS.NZ",
    "ALL.AX", "ALQ.AX", "AMC.AX", "AMP.AX", "ANZ.AX", "APA.AX", "ASX.AX", "BHP.AX", "BXB.AX",
    "CBA.AX", "COH.AX", "COL.AX", "CPU.AX", "CSL.AX", "DXS.AX", "FMG.AX", "GMG.AX", "IAG.AX",
    "JHX.AX", "MQG.AX", "MPL.AX", "NAB.AX", "ORG.AX", "ORI.AX", "PLS.AX", "QAN.AX", "QBE.AX",
    "REA.AX", "RHC.AX", "RIO.AX", "RMD.AX", "SCG.AX", "SHL.AX", "SGP.AX", "STO.AX", "TAH.AX",
    "TCL.AX", "TLS.AX", "TWE.AX", "VCX.AX", "WBC.AX", "WES.AX", "WDS.AX", "WOW.AX", "XRO.AX",
    "MIN.AX", "NST.AX"
]

local_name_map = {
    "F": "Ford Motor Co.", "GM": "General Motors", "PFE": "Pfizer Inc.", "T": "AT&T Inc.",
    "MDT": "Medtronic plc", "VZ": "Verizon Communications", "AAL": "American Airlines", "DAL": "Delta Air Lines",
    "SOFI": "SoFi Technologies", "PLTR": "Palantir Technologies", "AIR.NZ": "Air New Zealand",
    "SPK.NZ": "Spark NZ", "FBU.NZ": "Fletcher Building", "TLS.AX": "Telstra Group"
}
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: DATA RETRIEVAL ENGINE (CHUNK 3 OF 6)
# ==============================================================================

@st.cache_data(ttl=28800)
def fetch_all_market_data_batch_historical(ticker_list, start_date, execution_day_token):
    try:
        unique_tickers = list(dict.fromkeys(ticker_list))
        chunk_size = 15
        ticker_chunks = [unique_tickers[i:i+chunk_size] for i in range(0, len(unique_tickers), chunk_size)]
        chunked_dfs = []
        static_end_boundary = datetime.strptime(execution_day_token, "%Y-%m-%d") - timedelta(days=1)

        def download_chunk(sub_list):
            max_retries = 3
            backoff_factor = 2
            for attempt in range(max_retries):
                try:
                    df_chunk = yf.download(
                        sub_list, 
                        start=start_date, 
                        end=static_end_boundary, 
                        interval="1d", 
                        group_by='ticker', 
                        actions=False, 
                        threads=True, 
                        progress=False
                    )
                    if not df_chunk.empty:
                        return df_chunk.dropna(how='all', axis=1)
                except Exception:
                    if attempt == max_retries - 1:
                        break
                    time.sleep(backoff_factor ** attempt)
            return pd.DataFrame()

        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_chunk = {executor.submit(download_chunk, chunk): chunk for chunk in ticker_chunks}
            for future in as_completed(future_to_chunk):
                df_chunk = future.result()
                if df_chunk is not None and not df_chunk.empty:
                    chunked_dfs.append(df_chunk)
                    
        if chunked_dfs:
            combined_df = pd.concat(chunked_dfs, axis=1)
            if isinstance(combined_df.columns, pd.MultiIndex):
                combined_df = combined_df.sort_index(axis=1, level=0)
            return combined_df

    except Exception as e:
        st.sidebar.error(f"Threaded Historical failure: {str(e)}")
    return pd.DataFrame()

@st.cache_data(ttl=180)
def fetch_ultra_live_prices(ticker_list, cache_buster_token=""):
    try:
        unique_tickers = list(dict.fromkeys(ticker_list))
        live_prices_map = {}
        df_live = yf.download(unique_tickers[:100], period="1d", group_by='ticker', actions=False, threads=True, progress=False)
        
        if not df_live.empty:
            for ticker in unique_tickers[:100]:
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
    base_lookback_start = datetime.strptime(today_date_token, "%Y-%m-%d") - timedelta(days=730 + 250)
    return fetch_all_market_data_batch_historical(institutional_scan_pool, base_lookback_start, today_date_token)
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: VECTOR GENERATOR DESK (CHUNK 4 OF 6)
# ==============================================================================

@st.cache_data(ttl=28800)
def get_precalculated_indicators_matrix(fast_ma, slow_ma, today_date_token):
    raw_batch = get_cached_raw_universe_matrix(today_date_token)
    calculated_universe_dfs = {}
    
    if raw_batch.empty:
        return calculated_universe_dfs
        
    f_ma_int, s_ma_int = int(fast_ma), int(slow_ma)
    available_tickers = list(raw_batch.columns.get_level_values(0).unique())
    
    close_matrix = raw_batch.xs('Close', axis=1, level=1)
    high_matrix = raw_batch.xs('High', axis=1, level=1)
    low_matrix = raw_batch.xs('Low', axis=1, level=1)
    vol_matrix = raw_batch.xs('Volume', axis=1, level=1)

    fast_ma_matrix = close_matrix.rolling(window=f_ma_int, min_periods=1).mean()
    slow_ma_matrix = close_matrix.rolling(window=s_ma_int, min_periods=1).mean()
    
    bb_mean_20 = close_matrix.rolling(window=20, min_periods=1).mean()
    bb_std_20 = close_matrix.rolling(window=20, min_periods=1).std().fillna(0)
    lower_bb_matrix = bb_mean_20 - (2 * bb_std_20)
    
    tr_hl = high_matrix - low_matrix
    tr_hpc = (high_matrix - close_matrix.shift(1)).abs()
    tr_lpc = (low_matrix - close_matrix.shift(1)).abs()
    
    tr_matrix = pd.concat([tr_hl, tr_hpc, tr_lpc], axis=1, keys=['TR1', 'TR2', 'TR3'])
    tr_df = tr_matrix.T.groupby(level=1).max().T.fillna(0.0)
    
    atr_matrix = tr_df.rolling(window=14, min_periods=1).mean()
    avg_vol_20d_matrix = vol_matrix.rolling(window=20, min_periods=1).mean()
    
    delta_matrix = close_matrix.diff()
    gain_matrix = delta_matrix.clip(lower=0).rolling(window=14, min_periods=1).mean()
    loss_matrix = (-delta_matrix.clip(upper=0)).rolling(window=14, min_periods=1).mean()
    rsi_matrix = 100 - (100 / (1 + (gain_matrix / loss_matrix.replace(0, np.nan)))).fillna(50)
    
    macd_matrix = close_matrix.ewm(span=12, adjust=False).mean() - close_matrix.ewm(span=26, adjust=False).mean()
    sig_matrix = macd_matrix.ewm(span=9, adjust=False).mean()

    for ticker in available_tickers:
        try:
            if ticker not in close_matrix.columns: continue
            df = pd.DataFrame(index=raw_batch.index)
            df['Open'] = raw_batch[ticker]['Open']
            df['High'] = raw_batch[ticker]['High']
            df['Low'] = raw_batch[ticker]['Low']
            df['Close'] = raw_batch[ticker]['Close']
            df['Volume'] = raw_batch[ticker]['Volume']
            
            df['Fast_MA'] = fast_ma_matrix[ticker]
            df['Slow_MA'] = slow_ma_matrix[ticker]
            df['Lower_Bollinger_Band'] = lower_bb_matrix[ticker]
            df['ATR'] = atr_matrix[ticker]
            df['Avg_Volume_20D'] = avg_vol_20d_matrix[ticker]
            df['RSI'] = rsi_matrix[ticker]
            df['MACD'] = macd_matrix[ticker]
            df['Signal_Line'] = sig_matrix[ticker]
            
            df = df.dropna(subset=['Close'])
            if len(df) >= 5:
                calculated_universe_dfs[ticker] = df
        except: 
            continue
            
    return calculated_universe_dfs
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: SCREENING RADAR MATRIX (CHUNK 5 OF 6)
# ==============================================================================
@st.cache_data(ttl=180)
def process_entire_screening_universe(fast_ma, slow_ma, _live_feeds, cache_buster=""):
    today_token = datetime.today().strftime("%Y-%m-%d")
    raw_batch = get_cached_raw_universe_matrix(today_token)
    
    try:
        with open(NAMES_CACHE_FILE, 'r') as f: disk_names = json.load(f)
    except: disk_names = {}
    
    b_rows, d_rows = [], []
    cached_dfs = {}
    now_dt = datetime.now()
    weekday = now_dt.weekday()
    vol_pace_factor = 1.0 if weekday >= 4 else max(0.1, (weekday + 1) / 5.0)

    if raw_batch.empty or not hasattr(raw_batch, 'columns') or len(raw_batch.columns) == 0:
        return [], [], {}

    f_ma_int, s_ma_int = int(fast_ma), int(slow_ma)
    available_tickers = list(raw_batch.columns.get_level_values(0).unique())
    
    close_matrix = raw_batch.xs('Close', axis=1, level=1)
    high_matrix = raw_batch.xs('High', axis=1, level=1)
    low_matrix = raw_batch.xs('Low', axis=1, level=1)
    vol_matrix = raw_batch.xs('Volume', axis=1, level=1)

    fast_ma_matrix = close_matrix.rolling(window=f_ma_int, min_periods=1).mean()
    slow_ma_matrix = close_matrix.rolling(window=s_ma_int, min_periods=1).mean()
    bb_mean_20 = close_matrix.rolling(window=20, min_periods=1).mean()
    bb_std_20 = close_matrix.rolling(window=20, min_periods=1).std().fillna(0)
    lower_bb_matrix = bb_mean_20 - (2 * bb_std_20)
    
    tr_hl = high_matrix - low_matrix
    tr_hpc = (high_matrix - close_matrix.shift(1)).abs()
    tr_lpc = (low_matrix - close_matrix.shift(1)).abs()

    tr_matrix = pd.concat([tr_hl, tr_hpc, tr_lpc], axis=1, keys=['TR1', 'TR2', 'TR3'])
    tr_df = tr_matrix.T.groupby(level=1).max().T.fillna(0.0)

    atr_matrix = tr_df.rolling(window=14, min_periods=1).mean()
    avg_vol_matrix = vol_matrix.rolling(window=20, min_periods=1).mean()

    delta_matrix = close_matrix.diff()
    gain_matrix = delta_matrix.clip(lower=0).rolling(window=14, min_periods=1).mean()
    loss_matrix = (-delta_matrix.clip(upper=0)).rolling(window=14, min_periods=1).mean()
    rsi_matrix = 100 - (100 / (1 + (gain_matrix / loss_matrix.replace(0, np.nan)))).fillna(50)

    macd_matrix = close_matrix.ewm(span=12, adjust=False).mean() - close_matrix.ewm(span=26, adjust=False).mean()
    sig_matrix = macd_matrix.ewm(span=9, adjust=False).mean()

    for ticker in available_tickers:
        try:
            if ticker not in close_matrix.columns: continue
            
            last_close = _live_feeds[ticker]["Live_Close"] if _live_feeds and ticker in _live_feeds else float(close_matrix[ticker].iloc[-1])
            current_volume = _live_feeds[ticker]["Live_Volume"] if _live_feeds and ticker in _live_feeds else int(vol_matrix[ticker].iloc[-1])
            
            prev_close = float(close_matrix[ticker].iloc[-2]) if len(close_matrix) > 1 else last_close
            pct_change = ((last_close - prev_close) / prev_close) * 100
            
            fast_ma_val = float(fast_ma_matrix[ticker].iloc[-1])
            slow_ma_val = float(slow_ma_matrix[ticker].iloc[-1])
            rsi_val = float(rsi_matrix[ticker].iloc[-1])
            macd_val = float(macd_matrix[ticker].iloc[-1])
            sig_val = float(sig_matrix[ticker].iloc[-1])
            
            if ticker in atr_matrix.columns and not atr_matrix[ticker].dropna().empty:
                atr_val = float(atr_matrix[ticker].dropna().iloc[-1])
            
            else:
                atr_val = float(last_close * 0.02)
            bb_lower_val = float(lower_bb_matrix[ticker].iloc[-1])
            avg_volume_20d = float(avg_vol_matrix[ticker].iloc[-1]) if avg_vol_matrix[ticker].iloc[-1] > 0 else 1.0

            volume_multiple = (current_volume / vol_pace_factor) / avg_volume_20d
            true_52w_high = float(high_matrix[ticker].tail(104).max())
            true_52w_low = float(low_matrix[ticker].tail(104).min())
            proximity_to_low_pct = ((last_close - true_52w_low) / true_52w_low) * 100
            market_label = "NZ" if ticker.endswith(".NZ") else ("AUS" if ticker.endswith(".AX") else "US")
            # --- INCORPORATED CUSTOM CSV LOOKUP ENGINE ---
            file_names_map = get_custom_file_company_map()
            resolved_name = file_names_map.get(ticker, ticker)
            # ---------------------------------------------
            # Define the fee-adjusted targets directly above your signal engine (Line 389)
            safe_daily_limit_target = round((last_close - (0.50 * atr_val)) * 0.981, 2)
            safe_take_profit_target = round((safe_daily_limit_target + (2.0 * atr_val)) * 1.019, 2)

                        # --- TIGHTENED FOR HIGH-CONVICTION BREAKOUTS (REPLACES LINE 398-403) ---
            if last_close > fast_ma_val and last_close > slow_ma_val:
                # Requires a powerful 2.5x volume shockwave and confirmed upward momentum (RSI > 60)
                if volume_multiple >= 2.5 and rsi_val >= 60.0:
                    breakout_signal = "🌟 STRONG BUY"
                else:
                    breakout_signal = "🟩 BULLISH BREAKOUT"
            elif last_close > fast_ma_val and last_close <= slow_ma_val:
                # Keeps your early turning alerts active but raises the volume confirmation bar to 2.0x
                breakout_signal = "🟢 Bullish Turning (High Volume)" if volume_multiple >= 2.0 else "🟡 Bullish Turning (Low Volume)"
            else:
                breakout_signal = "🔴 Structural Bear"
            # ----------------------------------------------------------------------

            if breakout_signal != "🔴 Structural Bear":
                b_rows.append({
                    "Market": market_label, 
                    "Ticker": ticker, 
                    "Company Name": resolved_name, 
                    "Live Price": last_close, 
                    "Alert Status": breakout_signal, 
                    "Limit Entry Target": safe_daily_limit_target,   # UPDATED
                    "Take Profit Target": safe_take_profit_target,   # ADDED
                    "Vol Multiple": volume_multiple, 
                    "Daily Change %": pct_change, 
                    "RSI Momentum": rsi_val, 
                    "ATR Volatility": atr_val
                })

            if last_close <= (true_52w_low * 1.25):
                signal_label = "🟢 Bullish Turning" if macd_val > sig_val else "🔴 Bearish Floor"
                d_rows.append({
                    "Market": market_label, 
                    "Ticker": ticker, 
                    "Company Name": resolved_name, 
                    "Live Price": last_close, 
                    "52W Low Floor": true_52w_low, 
                    "Limit Entry Target": safe_daily_limit_target,   # UPDATED
                    "Lower Bollinger Band": bb_lower_val, 
                    "52W High Ceiling": true_52w_high, 
                    "Proximity to Low": proximity_to_low_pct, 
                    "RSI Status": rsi_val, 
                    "MACD Signal": signal_label
                })
            
            try:
                ticker_history_df = pd.DataFrame(index=raw_batch.index)
                ticker_history_df['Close'] = close_matrix[ticker]
                ticker_history_df['Fast_MA'] = fast_ma_matrix[ticker]
                ticker_history_df['Slow_MA'] = slow_ma_matrix[ticker]
                
                if ticker_history_df.index.tz is not None:
                    ticker_history_df.index = ticker_history_df.index.tz_localize(None)
                    
                ticker_history_df = ticker_history_df.dropna(subset=['Close'])
                cached_dfs[ticker] = ticker_history_df.to_json(date_format='iso')
            except:
                pass

        except: 
            continue

    return b_rows, d_rows, cached_dfs
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: USER INTERFACE DESK (CHUNK 6 OF 6)
# ==============================================================================

# 1. Enforce strict type casting and fallback safeguards on your inputs
fast_ma_input = int(st.session_state.get("asset_fast_ma", default_fast_ma))
slow_ma_input = int(st.session_state.get("asset_slow_ma", default_slow_ma))

# 2. Create a static time key that changes precisely every 3 minutes
live_feed_refresh_token = datetime.now().strftime("%Y-%m-%d %H:") + str(int(datetime.now().minute / 3))

# 3. --- THE INSTANT PERSISTENCE ENGINE ---
# Check if we already computed this exact technical matrix layout for this 3-minute block
if (
    "cached_radar_token" not in st.session_state or 
    st.session_state["cached_radar_token"] != live_feed_refresh_token or
    "stored_breakouts" not in st.session_state or
    "stored_discounts" not in st.session_state or
    "stored_compressed_dfs" not in st.session_state
):
    # This 30-second run executes ONLY once every 3 minutes, or if sliders change
    live_market_snapshots = fetch_ultra_live_prices(institutional_scan_pool, cache_buster_token=live_feed_refresh_token)
    
    all_breakouts, all_discounts, compressed_dfs = process_entire_screening_universe(
        fast_ma=fast_ma_input, 
        slow_ma=slow_ma_input, 
        _live_feeds=live_market_snapshots, 
        cache_buster=live_feed_refresh_token
    )
    
    # Store the final UI objects directly in the fast session memory vault
    st.session_state["stored_breakouts"] = all_breakouts
    st.session_state["stored_discounts"] = all_discounts
    st.session_state["stored_compressed_dfs"] = compressed_dfs
    st.session_state["cached_radar_token"] = live_feed_refresh_token
else:
    # Pulling directly from RAM. When switching screens, this step takes 0.0 seconds
    all_breakouts = st.session_state["stored_breakouts"]
    all_discounts = st.session_state["stored_discounts"]
    compressed_dfs = st.session_state["stored_compressed_dfs"]

# 4. Handle UI Filters based on your Budget-Friendly settings toggle
if st.session_state.get("view_mode_choice", "Entire Universe") == "Budget-Friendly Assets":
    max_cap = float(st.session_state.get("max_share_price_cap", 50.0))
    breakout_rows = [r for r in all_breakouts if r["Live Price"] <= max_cap]
    discount_rows = [r for r in all_discounts if r["Live Price"] <= max_cap]
else:
    breakout_rows, discount_rows = list(all_breakouts), list(all_discounts)

@st.fragment
def render_isolated_chart_engine(ticker_list, key_prefix):
    if ticker_list:
        selected_ticker = st.radio("🛰 **Global Chart Engine Quick-Link Bar:**", options=ticker_list, horizontal=True, key=f"{key_prefix}_link_key")
        if selected_ticker in compressed_dfs:
            df_chart = pd.read_json(io.StringIO(compressed_dfs[selected_ticker]))
            lookback_days_map = {"1 Month": 21, "3 Months": 63, "6 Months": 126, "1 Year": 252, "2 Years": 504}
            weeks_to_show = lookback_days_map.get(st.session_state.get("asset_horizon", "1 Year"), 52)
            df_chart = df_chart.tail(weeks_to_show).reset_index().rename(columns={'index': 'Date'})
            df_chart['Date'] = pd.to_datetime(df_chart['Date']).dt.strftime('%Y-%m-%d')
            
            y_min = float(df_chart[['Close', 'Fast_MA', 'Slow_MA']].min().min())
            y_max = float(df_chart[['Close', 'Fast_MA', 'Slow_MA']].max().max())
            y_scale = alt.Scale(domain=[y_min * 0.98, y_max * 1.02], zero=False)
            
            base = alt.Chart(df_chart).encode(x=alt.X('Date:T', title=None)).properties(width='container', height=320)
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
        status_rank_map = {"🌟 STRONG BUY": 0, "🟩 BULLISH BREAKOUT": 1, "🟢 Bullish Turning (High Volume)": 2, "🟡 Bullish Turning (Low Volume)": 3}
        raw_m_df["Rank_Weight"] = raw_m_df["Alert Status"].map(status_rank_map).fillna(4)
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
        else: st.info("No active setups match your budget filters inside this window tier.")
    else: st.info("No tickers matching crossover momentum velocity rules right now.")

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
        else: st.info("No deep discount setups match your budget filters inside this window tier.")
    else: st.info("No major institutional leaders currently resting inside deep value boundaries.")
