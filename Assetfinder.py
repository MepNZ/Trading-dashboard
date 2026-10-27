import streamlit as st
import pandas as pd
import numpy as np
import math
import yfinance as yf
import altair as alt
from datetime import datetime, timedelta

# =============================================================================
# 1. WINDOW SETUP & HIGH-CONTRAST DARK LAYOUT STYLING
# =============================================================================
st.set_page_config(
    page_title="Asset Finder",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; max-width: 100% !important; }
        div[data-testid="stTitle"] { margin-top: -20px !important; margin-bottom: -10px !important; }
        h1 { font-size: 2.0rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
        .small-header { font-size: 1.25rem !important; font-weight: bold !important; color: #4A90E2 !important; margin-bottom: 4px !important; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. DICTIONARY MAPPING FOR COMPLETE TICKER DATASET (28 ACTIVE TICKERS)
# =============================================================================
def load_company_names_matrix():
    return {
        "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp.", "GOOGL": "Alphabet Inc.", "AMZN": "Amazon.com Inc.",
        "META": "Meta Platforms", "NVDA": "NVIDIA Corp.", "TSLA": "Tesla Inc.", "PLTR": "Palantir Technologies",
        "JPM": "JPMorgan Chase & Co.", "AMD": "Advanced Micro Devices", "XOM": "Exxon Mobil Corp.", 
        "F": "Ford Motor Co.", "GM": "General Motors", "PFE": "Pfizer Inc.", "T": "AT&T Inc.",
        "MDT": "Medtronic plc", "VZ": "Verizon Communications", "SOFI": "SoFi Technologies", 
        "AIR.NZ": "Air New Zealand", "SPK.NZ": "Spark NZ", "FBU.NZ": "Fletcher Building", 
        "CEN.NZ": "Contact Energy", "MEL.NZ": "Meridian Energy", "BHP.AX": "BHP Group", 
        "CBA.AX": "Commonwealth Bank", "TLS.AX": "Telstra Group", "FMG.AX": "Fortescue Ltd", "RIO.AX": "Rio Tinto"
    }

# =============================================================================
# 3. HIGH-SPEED CONCURRENT LIVE DATA DOWNLOAD LAYER
# =============================================================================
@st.cache_data(ttl=300) # Locked 5-minute live memory cache safety buffer
def fetch_live_market_data(tickers):
    """
    Downloads structural matrix from yfinance and flattens column headers 
    to prevent row dropouts from new library layout updates.
    """
    lookback_start = datetime.today() - timedelta(days=365)
    try:
        fresh_data = yf.download(tickers, start=lookback_start, progress=False)
        
        # FIX: Flattens MultiIndex column headers to keep old-school code running perfectly
        if isinstance(fresh_data.columns, pd.MultiIndex):
            fresh_data.columns = ['_'.join(col).strip() for col in fresh_data.columns.values]
            
        return fresh_data
    except Exception as e:
        st.error(f"yfinance bulk ingestion fault: {str(e)}")
        return pd.DataFrame()

# =============================================================================
# 4. ORIGINAL BREAKOUT ALGORITHMS & MATHEMATICAL MATRIX RULES
# =============================================================================
def calculate_momentum_matrix(raw_batch, tickers, fast_ma, slow_ma):
    if raw_batch.empty: 
        return []
    disk_names = load_company_names_matrix()
    b_rows = []
    f_ma_int, s_ma_int = int(fast_ma), int(slow_ma)
    
    for ticker in tickers:
        try:
            # Build safe tracking mappings from newly flattened database columns
            open_col = f"Open_{ticker}" if f"Open_{ticker}" in raw_batch.columns else 'Open'
            high_col = f"High_{ticker}" if f"High_{ticker}" in raw_batch.columns else 'High'
            low_col = f"Low_{ticker}" if f"Low_{ticker}" in raw_batch.columns else 'Low'
            close_col = f"Close_{ticker}" if f"Close_{ticker}" in raw_batch.columns else 'Close'
            vol_col = f"Volume_{ticker}" if f"Volume_{ticker}" in raw_batch.columns else 'Volume'
            
            if close_col not in raw_batch.columns:
                continue
                
            df = pd.DataFrame({
                'Open': raw_batch[open_col],
                'High': raw_batch[high_col],
                'Low': raw_batch[low_col],
                'Close': raw_batch[close_col],
                'Volume': raw_batch[vol_col]
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
            c_yest, f_yest, s_yest = float(df['Close'].iloc[-2]), float(df['Fast_MA'].iloc[-2]), float(df['Slow_MA'].iloc[-2])
            c_db4, f_db4, s_db4 = float(df['Close'].iloc[-3]), float(df['Fast_MA'].iloc[-3]), float(df['Slow_MA'].iloc[-3])
            
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
                was_below_yest = (c_yest <= f_yest or c_yest <= s_yest)
                was_below_db4 = (c_db4 <= f_db4 or c_db4 <= s_db4)
                breakout_signal = "🚀 FRESH DAY-1 BREAKOUT" if (was_below_yest or was_below_db4) else "🟩 SUSTAINED TREND"
            elif c_today > f_today and c_today <= s_today:
                breakout_signal = "🟢 Bullish Turning (High Volume)" if volume_multiple >= 1.1 else "🟡 Bullish Turning (Low Volume)"
            else:
                breakout_signal = "🔴 Structural Bear"

            b_rows.append({
                "Market": market_label, "Ticker": ticker, "Company Name": resolved_name, 
                "Alert Status": breakout_signal, "Live Price": c_today, "Limit Entry Target": safe_daily_limit_target,
                "Take Profit Target": safe_take_profit_target, "Vol Multiple": volume_multiple, 
                "Daily Change %": pct_change, "RSI Momentum": rsi_val
            })
        except: continue
    return b_rows
# =============================================================================
# 5. USER PREFERENCE SIDEBAR CONTROLS
# =============================================================================
with st.sidebar:
    st.markdown("### 🛠     Technical Settings Layer")
    fast_ma_slider = st.slider("Fast MA Filter Window:", min_value=5, max_value=30, value=10, step=1)
    slow_ma_slider = st.slider("Slow MA Filter Window:", min_value=20, max_value=150, value=50, step=5)
    
    st.markdown("---")
    st.markdown("### 🎯 Display Filters")
    show_bears = st.checkbox("Include Structural Bears in Matrix", value=True)

# Run data collection matrix instantaneously
ticker_universe = list(load_company_names_matrix().keys())
raw_batch_data = fetch_live_market_data(ticker_universe)

raw_breakouts = calculate_momentum_matrix(raw_batch_data, ticker_universe, fast_ma_slider, slow_ma_slider)

if raw_breakouts:
    prices_list = [row["Live Price"] for row in raw_breakouts]
    absolute_max_price = math.ceil(max(prices_list)) if prices_list else 1000
    absolute_max_price = max(absolute_max_price, 500) 
else:
    absolute_max_price = 1000

with st.sidebar:
    st.markdown("---")
    st.markdown("### 💸 Price Restrictions")
    max_price_filter = st.slider(
        "Maximum Live Price to Display:", 
        min_value=5, 
        max_value=absolute_max_price, 
        value=absolute_max_price, 
        step=5,
        format="$%d"
    )

# =============================================================================
# 6. INSTANT DATA SCREENER GRID VIEW
# =============================================================================
if raw_breakouts:
    df_grid = pd.DataFrame(raw_breakouts)
    
    if not show_bears:
        df_grid = df_grid[df_grid["Alert Status"] != "🔴 Structural Bear"]
        
    df_grid = df_grid[df_grid["Live Price"] <= max_price_filter]
    
    if not df_grid.empty:
        df_grid = df_grid.sort_values(by=["Daily Change %"], ascending=False)
        cols_order = ["Market", "Ticker", "Company Name", "Alert Status", "Live Price", "Limit Entry Target", "Take Profit Target", "Vol Multiple", "Daily Change %", "RSI Momentum"]
        df_grid = df_grid[[c for c in cols_order if c in df_grid.columns]]
        
        st.dataframe(
            df_grid,
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                "Alert Status": st.column_config.Column("Alert Status"),
                "Live Price": st.column_config.NumberColumn("Live Price", format="$%.2f"),
                "Limit Entry Target": st.column_config.NumberColumn("Limit Entry Target", format="$%.2f"),
                "Take Profit Target": st.column_config.NumberColumn("Take Profit Target", format="$%.2f"),
                "Vol Multiple": st.column_config.NumberColumn("Vol Multiple", format="%.2fx"),
                "Daily Change %": st.column_config.NumberColumn("Daily Change %", format="%+.2f%%"),
                "RSI Momentum": st.column_config.NumberColumn("RSI Momentum", format="%.1f")
            }
        )
        
        # =============================================================================
        # 7. HIGH-SPEED LIGHTWEIGHT OVERLAY CHART
        # =============================================================================
        st.markdown("---")
        st.markdown("<div class='small-header'>📈 Global Chart Engine Analytics Overlay</div>", unsafe_allow_html=True)
        
        available_charts = df_grid["Ticker"].tolist()
        selected_ticker = st.radio(
            "Select an Asset to View Moving Average Overlays:",
            options=available_charts,
            horizontal=True
        )
        
        if selected_ticker and not raw_batch_data.empty:
            try:
                close_col = f"Close_{selected_ticker}" if f"Close_{selected_ticker}" in raw_batch_data.columns else 'Close'
                
                chart_df = pd.DataFrame({
                    'Close': raw_batch_data[close_col]
                }).ffill().bfill().dropna(subset=['Close'])
                
                # Render slider indicators instantly using memory data entries
                chart_df['Fast_MA_Line'] = chart_df['Close'].rolling(window=int(fast_ma_slider), min_periods=1).mean()
                chart_df['Slow_MA_Line'] = chart_df['Close'].rolling(window=int(slow_ma_slider), min_periods=1).mean()
                
                chart_df = chart_df.tail(120).reset_index()
                chart_df.columns = [str(c) for c in chart_df.columns]
                chart_df.rename(columns={chart_df.columns[0]: 'Date'}, inplace=True)
                chart_df['Date'] = pd.to_datetime(chart_df['Date']).dt.strftime('%Y-%m-%d')
                
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
        st.info("No active setups match your filtering criteria right now.")
else:
    st.info("No tickers matching crossover momentum velocity rules right now.")
