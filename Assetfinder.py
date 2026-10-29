import streamlit as st
import pandas as pd
import numpy as np
import math
import yfinance as yf
import altair as alt
from datetime import datetime, timedelta
import os
import json

# =============================================================================
# 1. WINDOW SETUP & LIGHT-THEME STYLING
# =============================================================================
st.set_page_config(
    page_title="Asset Finder",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Core page title configurations optimized for Light Theme text contrast
st.markdown("""
    <style>
        /* 🟢 Pushed top padding to 2.5rem to permanently clear browser header title cut-off issues */
        .block-container { padding-top: 2.5rem !important; padding-bottom: 0.5rem !important; max-width: 100% !important; }
        div[data-testid="stTitle"] { margin-top: -20px !important; margin-bottom: -10px !important; }
        h1 { font-size: 2.0rem !important; font-weight: 800 !important; color: #111111 !important; }
        .small-header { font-size: 1.25rem !important; font-weight: bold !important; color: #007bff !important; margin-bottom: 4px !important; }
        
        /* 👑 STYLES THE DATAFRAME IN LIGHT MODE WITH CRISP BLACK FOR ALL TEXT ELEMENTS */
        div[data-testid="stDataFrame"] *, 
        div[data-testid="stDataFrame"] [role="columnheader"] span,
        div[data-testid="stDataFrame"] div {
            color: #111111 !important;
            font-weight: 600 !important;
        }
    </style>
""", unsafe_allow_html=True)

# 🟢 Render page headers immediately on screen so you never see a blank canvas
st.title("💼 Financial Asset Discovery Dashboard")

# =============================================================================
# 2. DICTIONARY MAPPING FOR COMPLETE TICKER DATASET (JSON MASTER SYNC)
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
# 3. HIGH-SPEED CHUNKED CONCURRENT LIVE DATA DOWNLOAD LAYER
# =============================================================================
# 🟢 Separate function focused strictly on caching smaller, 50-stock data blocks
@st.cache_data(ttl=300, show_spinner=False)
def fetch_single_chunk_cached(chunk_list, lookback_date):
    try:
        chunk_data = yf.download(chunk_list, start=lookback_date, progress=False, group_by='ticker')
        if not chunk_data.empty:
            if len(chunk_list) == 1:
                t_name = chunk_list[0]
                chunk_data.columns = [f"{col}_{t_name}" for col in chunk_data.columns]
                return chunk_data
            
            new_cols = []
            for item, ticker in chunk_data.columns.values:
                if item in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    new_cols.append(f"{item}_{ticker}")
                else:
                    new_cols.append(f"{ticker}_{item}")
            chunk_data.columns = new_cols
            return chunk_data
    except Exception:
        pass
    return pd.DataFrame()

# Main workflow engine that handles visual progress updates live on screen
def fetch_live_market_data(tickers):
    if not tickers:
        return pd.DataFrame()
        
    lookback_start = datetime.today() - timedelta(days=90)
    chunk_size = 50
    ticker_chunks = [tickers[i:i + chunk_size] for i in range(0, len(tickers), chunk_size)]
    
    master_frames = []
    
    # 🟢 Renders directly to the live viewport container immediately
    progress_bar = st.progress(0, text="📥 Ingesting live market data arrays...")
    
    for idx, chunk in enumerate(ticker_chunks):
        # Call our sub-cached downloader row by row
        chunk_df = fetch_single_chunk_cached(chunk, lookback_start)
        if not chunk_df.empty:
            master_frames.append(chunk_df)
            
        # Update progress tracking layout fluidly on screen
        progress_pct = int(((idx + 1) / len(ticker_chunks)) * 100)
        progress_bar.progress(progress_pct, text=f"📥 Loaded {min((idx+1)*chunk_size, len(tickers))} of {len(tickers)} assets...")
    
    # Remove progress bar layout cleanly once complete
    progress_bar.empty()
    
    if not master_frames:
        return pd.DataFrame()
        
    return pd.concat(master_frames, axis=1).ffill().bfill()
# =============================================================================
# 4. UPGRADED BREAKOUT ALGORITHMS & MATHEMATICAL CONFLUENCE SCORING
# =============================================================================
def calculate_momentum_matrix(raw_batch, tickers, fast_ma, slow_ma):
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
            df['Avg_Vol_20D'] = df['Volume'].rolling(window=20, min_periods=1).mean()
            df['ATR'] = df['TR'].rolling(window=14, min_periods=1).mean()
            
            delta = df['Close'].diff()
            gain = delta.clip(lower=0).rolling(window=14, min_periods=1).mean()
            loss = (-delta.clip(upper=0)).rolling(window=14, min_periods=1).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)))).fillna(50)
            
            c_today, f_today, s_today = float(df['Close'].iloc[-1]), float(df['Fast_MA'].iloc[-1]), float(df['Slow_MA'].iloc[-1])
            c_yest = float(df['Close'].iloc[-2])
            
            pct_change = ((c_today - c_yest) / c_yest) * 100
            current_volume = int(df['Volume'].iloc[-1])
            avg_volume_20d = float(df['Avg_Vol_20D'].iloc[-1]) if df['Avg_Vol_20D'].iloc[-1] > 0 else 1.0
            volume_multiple = current_volume / avg_volume_20d
            rsi_val = float(df['RSI'].iloc[-1])
            atr_val = float(df['ATR'].iloc[-1]) if not np.isnan(df['ATR'].iloc[-1]) else (c_today * 0.02)
            
            market_label = "NZ" if ticker.endswith(".NZ") else ("AUS" if ticker.endswith(".AX") else "US")
            resolved_name = disk_names.get(ticker, f"{ticker}")
            
            safe_daily_limit_target = round((c_today - (0.50 * atr_val)) * 0.981, 2)
            safe_take_profit_target = round((safe_daily_limit_target + (2.0 * atr_val)) * 1.019, 2)

            if c_today > f_today and c_today > s_today:
                breakout_signal = "🟩 DUAL-TREND BREAKOUT"
            elif c_today > f_today and c_today <= s_today:
                breakout_signal = "🟢 Turning Bullish (High Vol)" if volume_multiple >= 1.1 else "🟡 Turning Bullish (Low Vol)"
            else:
                breakout_signal = "🔴 Structural Bear"

            stars = 0
            if c_today > f_today: stars += 1
            if c_today > s_today: stars += 1
            if volume_multiple >= 1.5: stars += 1
            if 45 <= rsi_val <= 68: stars += 1
            if pct_change > 0: stars += 1
            star_rating = "⭐" * stars if stars > 0 else "❌"

            if stars >= 1 or breakout_signal != "🔴 Structural Bear":
                b_rows.append({
                    "Market": market_label, "Ticker": ticker, "Company Name": resolved_name, 
                    "Alert Status": breakout_signal, "Score": star_rating, "Live Price": c_today, 
                    "Limit Entry Target": safe_daily_limit_target, "Take Profit Target": safe_take_profit_target, 
                    "Vol Multiple": volume_multiple, "ATR Risk": atr_val, "Daily Change %": pct_change, "RSI Momentum": rsi_val
                })
        except: continue
    return b_rows

# =============================================================================
# 5. USER PREFERENCE SIDEBAR CONTROLS
# =============================================================================
with st.sidebar:
    st.markdown("### 🌐 Market Universe Horizon")
    market_choice = st.multiselect(
        "Select Active Trading Horizons:",
        options=["US", "NZ", "AUS"],
        default=["US", "NZ", "AUS"]
    )
    
    # 🟢 NEW UPGRADE: On-Demand Gatekeeper switch to keep remaining 403 US stocks in reserve by default
    include_all_us = st.checkbox("Load Extended S&P 500 (Remaining 403 Stocks)", value=False)

    st.markdown("---")
    st.markdown("### 🛠 Technical Settings Layer")
    fast_ma_slider = st.slider("Fast MA Filter Window:", min_value=5, max_value=30, value=10, step=1)
    slow_ma_slider = st.slider("Slow MA Filter Window:", min_value=20, max_value=150, value=50, step=5)
    
    st.markdown("---")
    st.markdown("### 🎯 Display Filters")
    show_bears = st.checkbox("Include Structural Bears in Matrix", value=False)
    min_vol_multiple = st.slider("Minimum Vol Multiple Filter:", min_value=0.0, max_value=5.0, value=0.0, step=0.1, format="%.1fx")
    min_stars = st.slider("Minimum Confluence Rating (Stars):", min_value=0, max_value=5, value=0, step=1, format="%d ⭐")

# =============================================================================
# 🟢 ON-DEMAND TICKER SELECTION PATHWAY
# =============================================================================
csv_path = "ticker_names.csv"
ticker_universe = []

if os.path.exists(csv_path):
    try:
        m_df = pd.read_csv(csv_path, encoding='latin-1')
        m_df.columns = m_df.columns.astype(str).str.strip()
        
        for _, row in m_df.iterrows():
            t_col = str(row['Ticker']).strip().upper()
            m_col = str(row['Market']).strip().upper()
            p_col = str(row['Core_Priority']).strip()
            
            # Condition A: Always load the Top 100 US Megacaps if "US" horizon is checked
            if m_col == "US" and p_col == "Top100" and "US" in market_choice:
                ticker_universe.append(t_col)
                
            # Condition B: Load remaining 403 US tickers ONLY if explicit sidebar toggle is clicked
            elif m_col == "US" and p_col == "Standard" and "US" in market_choice and include_all_us:
                ticker_universe.append(t_col)
                
            # Condition C: Load NZX assets ONLY if "NZ" horizon is checked
            elif m_col == "NZ" and "NZ" in market_choice:
                ticker_universe.append(t_col)
                
            # Condition D: Load ASX assets ONLY if "AUS" horizon is checked
            elif m_col == "AUS" and "AUS" in market_choice:
                ticker_universe.append(t_col)
    except Exception as parse_error:
        st.sidebar.error(f"Source file routing error: {str(parse_error)}")

# Fallback block to keep app operational if everything is deselected
if not ticker_universe:
    ticker_universe = ["AAPL", "NVDA"]

raw_batch_data = fetch_live_market_data(ticker_universe)
raw_breakouts = calculate_momentum_matrix(raw_batch_data, ticker_universe, fast_ma_slider, slow_ma_slider)

if raw_breakouts:
    prices_list = [row["Live Price"] for row in raw_breakouts]
    absolute_max_price = max(math.ceil(max(prices_list)) if prices_list else 1000, 500)
else:
    absolute_max_price = 1000

with st.sidebar:
    st.markdown("---")
    st.markdown("### 💸 Price Restrictions")
    max_price_filter = st.slider("Maximum Live Price to Display:", min_value=5, max_value=absolute_max_price, value=absolute_max_price, step=5, format="$%d")
# =============================================================================
# 6. INSTANT DATA SCREENER GRID VIEW (HTML INTERACTIVE SORT ENGINE)
# =============================================================================
if raw_breakouts:
    df_grid = pd.DataFrame(raw_breakouts)
    
    df_grid = df_grid[df_grid["Market"].isin(market_choice)]
    
    if not show_bears:
        df_grid = df_grid[df_grid["Alert Status"] != "🔴 Structural Bear"]
        
    df_grid = df_grid[(df_grid["Live Price"] <= max_price_filter) & (df_grid["Vol Multiple"] >= min_vol_multiple)]
    
    df_grid["Star_Count"] = df_grid["Score"].apply(lambda x: len(x) if x != "❌" else 0)
    df_grid = df_grid[df_grid["Star_Count"] >= min_stars]
    df_grid = df_grid.drop(columns=["Star_Count"])
    
    if not df_grid.empty:
        # 🟢 Default sorted immediately by Relative Volume Multiple (RVOL) breakout activity
        df_grid = df_grid.sort_values(by=["Vol Multiple"], ascending=False)
        
        cols_order = ["Market", "Ticker", "Company Name", "Alert Status", "Score", "Live Price", "Limit Entry Target", "Take Profit Target", "Vol Multiple", "ATR Risk", "Daily Change %", "RSI Momentum"]
        df_grid = df_grid[[c for c in cols_order if c in df_grid.columns]]
        
        df_grid.columns = ["Market", "Ticker", "Asset Name", "System Status", "Confluence", "Price", "Limit Entry Target", "Take Profit Target", "RVOL Multiplier", "ATR Risk ($)", "Daily Change %", "RSI Momentum"]
        
        df_display = df_grid.copy()
        df_display["Price"] = df_display["Price"].map("${:,.2f}".format)
        df_display["Limit Entry Target"] = df_display["Limit Entry Target"].map("${:,.2f}".format)
        df_display["Take Profit Target"] = df_display["Take Profit Target"].map("${:,.2f}".format)
        
        df_display["RVOL Multiplier"] = df_display["RVOL Multiplier"].apply(
            lambda x: f"🟢 {x:,.2f}x" if x >= 1.50 else f"{x:,.2f}x"
        )
        
        df_display["ATR Risk ($)"] = df_display["ATR Risk ($)"].map("${:,.2f}".format)
        
        df_display["Daily Change %"] = df_display["Daily Change %"].apply(
            lambda x: f"🟢 {x:+.2f}%" if x >= 3.00 else f"{x:+.2f}%"
        )
        
        df_display["RSI Momentum"] = df_display["RSI Momentum"].apply(
            lambda x: f"🟢 {x:,.1f}" if x >= 60.0 else f"{x:,.1f}"
        )

        html_table = df_display.to_html(index=False, escape=False, table_id="interactive-screener")
        
        screener_combined_html = f"""
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: transparent;
            }}
            .scroll-window {{
                max-height: 650px;
                overflow-y: auto !important;
                overflow-x: auto !important;
                border: 1px solid #D1D5DB;
            }}
            #interactive-screener {{
                width: 100%;
                border-collapse: collapse;
                font-family: sans-serif;
                background-color: #FFFFFF !important;
            }}
            #interactive-screener th {{
                position: -webkit-sticky !important;
                position: sticky !important;
                top: 0 !important;
                z-index: 10 !important;
                background-color: #E5E7EB !important;
                color: #111111 !important;
                font-size: 1.00rem !important;
                font-weight: bold !important;
                padding: 0px 12px !important;
                height: 90px !important;
                display: table-cell !important;
                vertical-align: middle !important;
                line-height: 90px !important;
                text-align: left;
                border-bottom: 3px solid #007bff !important;
                white-space: nowrap !important;
                cursor: pointer !important;
                user-select: none;
            }}
            #interactive-screener th::after {{
                content: " ↕";
                font-size: 0.8rem;
                color: #888;
                padding-left: 5px;
                display: inline-block !important;
                vertical-align: middle !important;
                line-height: normal !important;
            }}
            #interactive-screener td {{
                color: #222222 !important;
                font-size: 0.95rem !important;
                padding: 12px 12px !important;
                border-bottom: 1px solid #E5E7EB !important;
                white-space: nowrap !important;
            }}
            #interactive-screener tr:nth-child(even) {{ background-color: #F9FAFB !important; }}
            #interactive-screener tr:hover {{ background-color: #F3F4F6 !important; }}
        </style>
        
        <div class='scroll-window'>
            {html_table}
        </div>
        
        <script>
            document.querySelectorAll("#interactive-screener th").forEach((header, index) => {{
                header.addEventListener("click", () => {{
                    const table = document.getElementById("interactive-screener");
                    const tbody = table.querySelector("tbody");
                    const rows = Array.from(tbody.querySelectorAll("tr"));
                    const isAscending = header.classList.contains("sort-asc");
                    
                    table.querySelectorAll("th").forEach(th => th.classList.remove("sort-asc", "sort-desc"));
                    
                    rows.sort((rowA, rowB) => {{
                        let cellA = rowA.children[index].textContent.replace(/[\\$,%x\\s]/g, "").trim();
                        let cellB = rowB.children[index].textContent.replace(/[\\$,%x\\s]/g, "").trim();
                        
                        cellA = cellA.replace(/🟢/g, "").trim();
                        cellB = cellB.replace(/🟢/g, "").trim();
                        
                        const numA = parseFloat(cellA);
                        const numB = parseFloat(cellB);
                        
                        if (!isNaN(numA) && !isNaN(numB)) return isAscending ? numB - numA : numA - numB;
                        return isAscending ? cellB.localeCompare(cellA) : cellA.localeCompare(cellB);
                    }});
                    
                    header.classList.toggle("sort-asc", !isAscending);
                    header.classList.toggle("sort-desc", isAscending);
                    
                    rows.forEach(row => tbody.appendChild(row));
                }});
            }});
        </script>
        """
        
        st.components.v1.html(screener_combined_html, height=700, scrolling=False)
        st.markdown("<br>", unsafe_allow_html=True)        

        # =============================================================================
        # 7. HIGH-SPEED LIGHTWEIGHT OVERLAY CHART
        # =============================================================================
        st.markdown("---")
        st.markdown("<div class='small-header'>📈 Global Chart Engine Analytics Overlay</div>", unsafe_allow_html=True)
        
        available_charts = df_grid["Ticker"].tolist()
        selected_ticker = st.radio("Select an Asset to View Moving Average Overlays:", options=available_charts, horizontal=True)
        
        if selected_ticker and not raw_batch_data.empty:
            try:
                close_col = f"Close_{selected_ticker}" if f"Close_{selected_ticker}" in raw_batch_data.columns else 'Close'
                chart_df = pd.DataFrame({'Close': raw_batch_data[close_col]}).ffill().bfill().dropna(subset=['Close'])
                
                chart_df['Fast_MA_Line'] = chart_df['Close'].rolling(window=int(fast_ma_slider), min_periods=1).mean()
                chart_df['Slow_MA_Line'] = chart_df['Close'].rolling(window=int(slow_ma_slider), min_periods=1).mean()
                
                chart_df = chart_df.tail(120)
                chart_df.index = pd.to_datetime(chart_df.index).strftime('%Y-%m-%d')
                chart_df = chart_df.reset_index().rename(columns={'index': 'Date'})
                chart_df.columns = [str(c) for c in chart_df.columns]
                
                y_scale = alt.Scale(domain=[chart_df['Close'].min() * 0.95, chart_df['Close'].max() * 1.05], clamp=True)
                base = alt.Chart(chart_df).encode(x='Date:T').properties(height=300)
                
                c_line = base.mark_line(color='#4A90E2', strokeWidth=3).encode(y=alt.Y('Close:Q', scale=y_scale, title="Price ($)"))
                f_line = base.mark_line(color='#00FF66', strokeWidth=2).encode(y='Fast_MA_Line:Q')
                s_line = base.mark_line(color='#FF3333', strokeWidth=2).encode(y='Slow_MA_Line:Q')
                
                st.altair_chart(alt.layer(c_line, f_line, s_line), use_container_width=True)
                st.caption(f"🔵 Blue = Price | 🟢 Green = {fast_ma_slider}-Day Fast MA | 🔴 Red = {slow_ma_slider}-Day Slow MA")
            except Exception as chart_fault:
                st.info("Chart alignment processing. Checking data parameters.")
    else:
        st.sidebar.info("No active setups match your filtering criteria right now.")
else:
    st.sidebar.info("No tickers matching crossover momentum velocity rules right now.")
