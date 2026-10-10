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

# NOTE: st.set_page_config removed for native sub-menu sidebar inheritance

st.markdown("""
    <style>
        /* Global Font Scaling & Row Expansion */
        html, body, [data-testid="stAppViewContainer"] {
            font-size: 1.2rem !important;
        }
        
        /* Force Tables to render with large, high-visibility text */
        div[data-testid="stDataFrame"] * {
            font-size: 1.25rem !important;
        }
        
        /* Expand spacing between tracking rows so they don't squash */
        div[data-testid="stDataFrame"] [role="row"] {
            margin-top: 4px !important;
            margin-bottom: 4px !important;
        }

        .block-container { padding-top: 3.5rem !important; padding-bottom: 1rem !important; }
        h1 { font-size: 2.2rem !important; font-weight: 800 !important; color: #111111 !important; }
        .small-header { font-size: 1.3rem !important; font-weight: bold !important; color: #4A90E2 !important; }
    </style>
""", unsafe_allow_html=True)

def apply_alpha_signal_theme(df):
    def style_breakout_cells(row):
        styles = [''] * len(row)
        if 'Alert Status' in row.index:
            val = row['Alert Status']
            idx = row.index.get_loc('Alert Status')
            if val == "⚡ HYPER MOMENTUM": styles[idx] = 'background-color: #007bff; color: #ffffff; font-weight: bold;'
            elif val == "🟩 BULLISH RIDER": styles[idx] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == "🟨 OVEREXTENDED": styles[idx] = 'background-color: #ffe8a1; color: #856404; font-weight: bold;'
        return styles
    return df.style.apply(style_breakout_cells, axis=1)

TARGETS_FILE = "portfolio_targets.json"
CACHE_FILE = "alpha_hunter_cache.json"
CACHE_TTL_MINUTES = 15

disk_memory = {}
if os.path.exists(TARGETS_FILE):
    try:
        with open(TARGETS_FILE, 'r') as f:
            disk_memory = json.load(f)
    except Exception:
        pass

if "local_name_map" not in disk_memory:
    disk_memory["local_name_map"] = {}

runtime_sliders = disk_memory.get("sliders", {})
fast_ma_input = int(runtime_sliders.get("fast_ma", 10))
slow_ma_input = int(runtime_sliders.get("slow_ma", 100))
selected_timeframe = runtime_sliders.get("roi_window", "1 Year")
chart_timeframe_choice = runtime_sliders.get("graph_horizon", "1 Year")

st.title("🔍 Asset Finder")
st.caption("Integrated Multi-Strategy Institutional Alpha Scanner (Enhanced Pool)")

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
# MIKE'S QUANT ALPHA HUNTER: DICTIONARY & CACHE ENGINE (PART 2 OF 3)
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
    cache_valid = False
    if os.path.exists(CACHE_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
        if datetime.now() - file_mod_time < timedelta(minutes=CACHE_TTL_MINUTES):
            cache_valid = True
    if cache_valid:
        try:
            df_cached = pd.read_json(CACHE_FILE)
            df_cached.index = pd.to_datetime(df_cached.index)
            df_cached.columns = pd.MultiIndex.from_tuples([eval(col) for col in df_cached.columns])
            return df_cached
        except Exception:
            pass
    try:
        df_live = yf.download(list(set(ticker_list)), start=start_date, group_by='ticker', actions=False, threads=True, progress=False)
        if not df_live.empty:
            df_serializable = df_live.copy()
            df_serializable.columns = [str(col) for col in df_serializable.columns]
            df_serializable.to_json(CACHE_FILE)
        return df_live
    except Exception:
        return pd.DataFrame()
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: DATA PROCESSING LOOP (PART 3a OF 4)
# ==============================================================================
def extract_ticker_dataframe(df_all, ticker):
    try:
        if df_all.empty or ticker not in df_all.columns.get_level_values(0):
            return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        df = df_all[ticker].copy()
        df.columns = [str(c).title() for c in df.columns]
        return df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    except:
        return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

lookback_days_map = {"1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365, "2 Years": 730}
chosen_lookback_days = lookback_days_map.get(chart_timeframe_choice, 365)
lookback_start_date = datetime.now() - timedelta(days=chosen_lookback_days + 250)

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
    
    current_volume = int(df_calc['Volume'].iloc[-1]) if 'Volume' in df_calc.columns else 0
    avg_volume_20d = float(df_calc['Avg_Volume_20D'].iloc[-1]) if 'Avg_Volume_20D' in df_calc.columns else 1.0
    volume_multiple = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0.0
    
    hist_365 = df_calc[df_calc.index >= pd.to_datetime(datetime.now() - timedelta(days=365)).tz_localize(df_calc.index.tz)] if not df_calc.empty else df_calc
    true_52w_high, true_52w_low = float(hist_365['High'].max()), float(hist_365['Low'].min())
    proximity_to_low_pct = ((last_close - true_52w_low) / true_52w_low) * 100
    
    market_label = "NZ" if ticker.endswith(".NZ") else ("AUS" if ticker.endswith(".AX") else "US")
    
    if last_close > fast_ma_val and last_close > slow_ma_val and rsi_val < 72.0:
        if volume_multiple >= 2.0 and macd_val > sig_val and rsi_val >= 55.0: breakout_signal = "⚡ HYPER MOMENTUM"
        elif rsi_val >= 68.0: breakout_signal = "🟨 OVEREXTENDED"
        else: breakout_signal = "🟩 BULLISH RIDER"

        breakout_rows.append({
            "Market": market_label, "Ticker": ticker, "Company Name": local_name_map.get(ticker, f"{ticker} Leader"),
            "Live Price": last_close, "Alert Status": breakout_signal, "Vol Multiple": volume_multiple, 
            "Daily Change %": pct_change, "RSI Momentum": rsi_val, "ATR Volatility": atr_val
        })
    
    if last_close <= (true_52w_low * 1.10):
        signal_label = "🟢 Bullish Turning" if macd_val > sig_val else "🔴 Bearish Floor"
        discount_rows.append({
            "Market": market_label, "Ticker": ticker, "Company Name": local_name_map.get(ticker, f"{ticker} Leader"),
            "Live Price": last_close, "52W Low Floor": true_52w_low, "52W High Ceiling": true_52w_high,
            "Proximity to Low": proximity_to_low_pct, "RSI Status": rsi_val, "MACD Signal": signal_label
        })
# ==============================================================================
# MIKE'S QUANT ALPHA HUNTER: DASHBOARD INTERFACE LAYOUT (PART 3b OF 4)
# ==============================================================================
tab_momentum, tab_discount = st.tabs(["🔥 Breakouts", "📉 Possible Value Discounts"])

def sync_changes_to_master_repository(updated_memory):
    """Programmatically patches portfolio_targets.json directly onto your GitHub repo"""
    import requests
    import base64
    
    # Securely inherit your centralized Streamlit cloud tokens
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    
    if not token or not repo:
        # Fallback to standard local file write if running offline on your laptop
        try:
            with open(TARGETS_FILE, 'w') as f: json.dump(updated_memory, f, indent=4)
            return True
        except Exception as e:
            st.error(f"Local Write Error: {str(e)}")
            return False
            
    url = f"https://api.github.com{repo}/contents/{TARGETS_FILE}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    try:
        # Step 1: Fetch the active file blob sha to prevent overwrite collisions
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None
        
        # Step 2: Push the updated JSON structure live to GitHub
        new_content = base64.b64encode(json.dumps(updated_memory, indent=4).encode("utf-8")).decode("utf-8")
        payload = {"message": "📡 Asset Finder: Added custom ticker metadata", "content": new_content}
        if sha: payload["sha"] = sha
        
                # Step 3: Commit the changes back to GitHub
        put_r = requests.put(url, headers=headers, json=payload)

        # Step 4: Verify the API response status code safely
        if put_r.status_code in (200, 201):
            st.success("Changes successfully synced to the master repository!")
            return True
        else:
            st.error(f"GitHub Sync Failed. Status code: {put_r.status_code}")
            return False

    except Exception as e:
        st.error(f"Repository connection error: {str(e)}")
        return False

with tab_momentum:
    st.markdown("<p class='small-header'>Institutional Velocity Screening Grid</p>", unsafe_allow_html=True)
    if breakout_rows:
        breakout_df = pd.DataFrame(breakout_rows).sort_values(by="Daily Change %", ascending=False).head(20)
        momentum_tickers = sorted(list(set(breakout_df["Ticker"].tolist())))
        cols_order = ["Market", "Ticker", "Company Name", "Alert Status", "Live Price", "ATR Volatility", "Vol Multiple", "Daily Change %", "RSI Momentum"]
        st.dataframe(apply_alpha_signal_theme(breakout_df[[c for c in cols_order if c in breakout_df.columns]]), use_container_width=True, hide_index=True, height=250, column_config={"Live Price": st.column_config.NumberColumn(format="$%.2f"), "ATR Volatility": st.column_config.NumberColumn("Daily ATR ($)", format="$%.2f"), "Vol Multiple": st.column_config.NumberColumn("Volume Surge", format="%.2fx"), "Daily Change %": st.column_config.NumberColumn(format="%+.2f%%"), "RSI Momentum": st.column_config.NumberColumn(format="%.1f")})
        
        st.markdown("---")
        selected_m_ticker = st.selectbox("🛰️ **Select Ticker to view chart:**", options=momentum_tickers, key="m_select_key")
        if selected_m_ticker in operational_dfs:
            fallback_name = local_name_map.get(selected_m_ticker, f"{selected_m_ticker} Asset")
            if st.button(f"➕ Push {selected_m_ticker} into Core Cockpit Targets", key="m_push_btn"):
                disk_memory["local_name_map"][selected_m_ticker] = fallback_name
                if sync_changes_to_master_repository(disk_memory):
                    st.success(f"🚀 Alignment Saved! Click '💾 Save Matrix Boundary Changes' in the main dashboard to deploy live.")
                    st.rerun()
            
            chart_sliced = operational_dfs[selected_m_ticker].tail(chosen_lookback_days).copy().reset_index()
            if 'index' in chart_sliced.columns: chart_sliced = chart_sliced.rename(columns={'index': 'Date'})
            if not chart_sliced.empty and 'Fast_MA' in chart_sliced.columns:
                chart_sliced['Date'] = pd.to_datetime(chart_sliced['Date']).dt.strftime('%Y-%m-%d')
                y_scale = alt.Scale(domain=[float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].min().min()) * 0.98, float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].max().max()) * 1.02], zero=False)
                base = alt.Chart(chart_sliced).encode(x=alt.X('Date:T', title=None)).properties(width=900, height=320)
                st.altair_chart(base.mark_line(color='#4A90E2', strokeWidth=3.5).encode(y=alt.Y('Close:Q', scale=y_scale, title='Price ($)')) + base.mark_line(color='#00FF66', strokeWidth=3.0).encode(y=alt.Y('Fast_MA:Q')) + base.mark_line(color='#FF3333', strokeWidth=3.0).encode(y=alt.Y('Slow_MA:Q')), use_container_width=True)
    else: st.info("No tickers matching crossover momentum velocity rules right now.")

with tab_discount:
    st.markdown("<p class='small-header'>Mean-Reversion Floor Screening Grid</p>", unsafe_allow_html=True)
    if discount_rows:
        discount_df = pd.DataFrame(discount_rows).sort_values(by="Proximity to Low", ascending=True).head(20)
        discount_tickers = sorted(list(set(discount_df["Ticker"].tolist())))
        cols_discount_order = ["Market", "Ticker", "Company Name", "Live Price", "52W Low Floor", "52W High Ceiling", "Proximity to Low", "RSI Status", "MACD Signal"]
        st.dataframe(discount_df[[c for c in cols_discount_order if c in discount_df.columns]], use_container_width=True, hide_index=True, height=220, column_config={"Live Price": st.column_config.NumberColumn(format="$%.2f"), "52W Low Floor": st.column_config.NumberColumn(format="$%.2f"), "52W High Ceiling": st.column_config.NumberColumn(format="$%.2f"), "Proximity to Low": st.column_config.NumberColumn("Distance From Low", format="%.2f%%"), "RSI Status": st.column_config.NumberColumn(format="%.1f")})
        
        st.markdown("---")
        selected_d_ticker = st.selectbox("🛰️ **Select Laboratory Target Scan Node:**", options=discount_tickers, key="d_select_key")
        if selected_d_ticker in operational_dfs:
            fallback_name = local_name_map.get(selected_d_ticker, f"{selected_d_ticker} Asset")
            if st.button(f"➕ Push {selected_d_ticker} into Core Cockpit Targets", key="d_push_btn"):
                disk_memory["local_name_map"][selected_d_ticker] = fallback_name
                if sync_changes_to_master_repository(disk_memory):
                    st.success(f"🚀 Alignment Saved! Remember to save changes on your main cockpit view to push live.")
                    st.rerun()
                    
            chart_sliced = operational_dfs[selected_d_ticker].tail(chosen_lookback_days).copy().reset_index()
            if 'index' in chart_sliced.columns: chart_sliced = chart_sliced.rename(columns={'index': 'Date'})
            if not chart_sliced.empty and 'Fast_MA' in chart_sliced.columns:
                chart_sliced['Date'] = pd.to_datetime(chart_sliced['Date']).dt.strftime('%Y-%m-%d')
                y_scale = alt.Scale(domain=[float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].min().min()) * 0.98, float(chart_sliced[['Close', 'Fast_MA', 'Slow_MA']].max().max()) * 1.02], zero=False)
                base = alt.Chart(chart_sliced).encode(x=alt.X('Date:T', title=None)).properties(width=900, height=320)
                st.altair_chart(base.mark_line(color='#4A90E2', strokeWidth=3.5).encode(y=alt.Y('Close:Q', scale=y_scale, title='Price ($)')) + base.mark_line(color='#00FF66', strokeWidth=3.0).encode(y=alt.Y('Fast_MA:Q')) + base.mark_line(color='#FF3333', strokeWidth=3.0).encode(y=alt.Y('Slow_MA:Q')), use_container_width=True)
    else: st.info("No major institutional leaders currently resting inside deep value boundaries.")
