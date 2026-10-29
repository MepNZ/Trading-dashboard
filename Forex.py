import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator
from ta.trend import MACD

st.set_page_config(page_title="FX Control Desk", layout="wide", initial_sidebar_state="expanded")
st.title("💱 Forex Real-Time Matrix & Forward-Testing Engine")

with st.sidebar:
    st.markdown("### 🌐 FX Currency Pair Selector")
    fx_pair_choice = st.selectbox("Select Core Pair Cross:", options=["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X", "USDJPY=X", "USDCAD=X"], index=0)
    st.markdown("---")
    st.markdown("### 🛠️ Algorithm Confluence Variables")
    fast_ma_slider = st.slider("Fast Signal Window:", min_value=5, max_value=30, value=10)
    slow_ma_slider = st.slider("Slow Trend Window:", min_value=20, max_value=150, value=50)
    rsi_window_slider = st.slider("RSI Momentum Window:", min_value=7, max_value=28, value=14)
    st.markdown("---")
    st.markdown("### 🧪 Paper Trade Workspace")
    sim_entry_date = st.date_input("What-If Entry Date:", value=datetime.today() - timedelta(days=30))
    sim_notional_size = st.number_input("Position Size (Units):", min_value=1000, value=10000, step=1000)

lookback_start = datetime.today() - timedelta(days=365 + 50)
raw_hist = yf.download(tickers=fx_pair_choice, start=lookback_start, interval="1d", progress=False)
raw_live = yf.download(tickers=fx_pair_choice, period="1d", interval="1m", progress=False)

if raw_hist.empty:
    st.error(f"❌ Yahoo Finance returned an empty historical dataframe for {fx_pair_choice}.")
    st.stop()

def clean_and_flatten_dataframe(df, target_pair):
    working_df = df.copy()
    if isinstance(working_df.columns, pd.MultiIndex):
        if target_pair in working_df.columns.get_level_values(1):
            working_df = working_df.xs(target_pair, axis=1, level=1)
        elif target_pair in working_df.columns.get_level_values(0):
            working_df = working_df.xs(target_pair, axis=1, level=0)
    working_df.columns = [str(col).strip().capitalize() for col in working_df.columns]
    return working_df

history_df = clean_and_flatten_dataframe(raw_hist, fx_pair_choice)
live_feed_df = clean_and_flatten_dataframe(raw_live, fx_pair_choice)

if 'Close' not in history_df.columns:
    st.warning("⚠️ Column parsing mismatch detected. Showing keys:")
    st.write(list(history_df.columns))
    st.stop()
history_df['Fast_MA'] = history_df['Close'].rolling(window=int(fast_ma_slider), min_periods=1).mean()
history_df['Slow_MA'] = history_df['Close'].rolling(window=int(slow_ma_slider), min_periods=1).mean()
history_df['RSI'] = RSIIndicator(close=history_df['Close'], window=int(rsi_window_slider)).rsi()

macd_indicator = MACD(close=history_df['Close'])
history_df['MACD'] = macd_indicator.macd()
history_df['MACD_Signal'] = macd_indicator.macd_signal()

if not live_feed_df.empty and 'Close' in live_feed_df.columns:
    live_price = float(live_feed_df['Close'].iloc[-1])
    price_change_raw = live_price - float(history_df['Close'].iloc[-2])
    price_pct_change = (price_change_raw / float(history_df['Close'].iloc[-2])) * 100
    high_today = float(live_feed_df['High'].max())
    low_today = float(live_feed_df['Low'].min())
else:
    live_price = float(history_df['Close'].iloc[-1])
    price_change_raw = 0.0
    price_pct_change = 0.0
    high_today, low_today = live_price, live_price

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric("Live Price Feed", f"{live_price:.5f}", f"{price_pct_change:+.3f}%")
m_col2.metric("Daily High Peak", f"{high_today:.5f}")
m_col3.metric("Daily Low Floor", f"{low_today:.5f}")
m_col4.metric(f"RSI Momentum ({rsi_window_slider})", f"{float(history_df['RSI'].iloc[-1]):.2f}")

st.markdown("---")
# 👑 EXPLICITLY DEFINED AS A 2-COLUMN ARRANGEMENT TO RESOLVE TYPEERRORS
chart_col, signal_col = st.columns(2)

with chart_col:
    st.subheader("📈 Live Interactive Price Engine & Overlays")
    chart_slice = history_df.tail(90)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=chart_slice.index, open=chart_slice['Open'], high=chart_slice['High'], low=chart_slice['Low'], close=chart_slice['Close'], name="Candlesticks"))
    fig.add_trace(go.Scatter(x=chart_slice.index, y=chart_slice['Fast_MA'], mode='lines', name=f'{fast_ma_slider} Fast MA', line=dict(color='#00FF66', width=1.5)))
    fig.add_trace(go.Scatter(x=chart_slice.index, y=chart_slice['Slow_MA'], mode='lines', name=f'{slow_ma_slider} Slow MA', line=dict(color='#FF3333', width=1.5)))
    fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10), height=400, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with signal_col:
    st.subheader("⚡ Confluence Screener")
    fast_val = float(history_df['Fast_MA'].iloc[-1])
    slow_val = float(history_df['Slow_MA'].iloc[-1])
    latest_macd = float(history_df['MACD'].iloc[-1])
    latest_signal = float(history_df['MACD_Signal'].iloc[-1])
    latest_rsi = float(history_df['RSI'].iloc[-1])
    
    if live_price > fast_val and live_price > slow_val: st.success("Trend Status: 🟩 STRONG BULLISH")
    elif live_price < fast_val and live_price < slow_val: st.error("Trend Status: 🔴 STRONG BEARISH")
    else: st.warning("Trend Status: 🟡 CONSOLIDATION")
        
    st.markdown("**Momentum Matrix Signals:**")
    if latest_rsi > 70: st.markdown("• **RSI:** ⚠️ Overbought (Look to Sell)")
    elif latest_rsi < 30: st.markdown("• **RSI:** 🟢 Oversold (Look to Buy)")
    else: st.markdown("• **RSI:** ⚪ Neutral Momentum")
    if latest_macd > latest_signal: st.markdown("• **MACD:** 🟢 Bullish Crossover")
    else: st.markdown("• **MACD:** 🔴 Bearish Crossover")

st.markdown("---")
st.subheader("🧪 Mathematical Forward-Testing Sandbox (\"What-If\" Simulator)")
target_date_parsed = pd.to_datetime(sim_entry_date)
historical_matches = history_df[history_df.index >= target_date_parsed]

if not historical_matches.empty:
    entry_price_calculated = float(historical_matches['Close'].iloc[0])
    actual_entry_date = historical_matches.index[0].strftime('%Y-%m-%d')
    net_pip_move_raw = (live_price - entry_price_calculated)
    pip_multiplier = 100.0 if "JPY" in fx_pair_choice else 10000.0
    total_pips_delta = net_pip_move_raw * pip_multiplier
    percentage_roi_simulated = (net_pip_move_raw / entry_price_calculated) * 100
    total_notional_pnl_value = net_pip_move_raw * sim_notional_size
    
    sim_col1, sim_col2, sim_col3 = st.columns(3)
    with sim_col1: st.info(f"📋 **Simulated Position Entry Details:**\n* **Matched Entry Date:** {actual_entry_date}\n* **Historical Close Price:** {entry_price_calculated:.5f}")
    with sim_col2:
        pnl_color_tag = "green" if total_notional_pnl_value >= 0 else "red"
        st.markdown(f"""<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px;"><span style="font-size: 1.1rem; font-weight: bold; margin-bottom: 5px;">📈 Net Investment Returns:</span><br>Total Pips Move: <b>{total_pips_delta:+.1f} Pips</b><br>Percentage ROI: <span style="color:{pnl_color_tag}; font-weight:bold;">{percentage_roi_simulated:+.2f}%</span></div>""", unsafe_allow_html=True)
    with sim_col3: st.metric(label=f"Simulated Open P&L Value (Base Currency)", value=f"${total_notional_pnl_value:,.2f}", delta=f"{total_pips_delta:+.1f} Pips Since Entry")
        
    st.markdown("**Visual Trajectory Tracking Path Since Position Entry:**")
    path_df = historical_matches.reset_index()
    path_chart = go.Figure()
    path_chart.add_trace(go.Scatter(x=path_df['Date'], y=path_df['Close'], mode='lines+markers', name='Price Path', line=dict(color='#4A90E2', width=2.5)))
    path_chart.add_trace(go.Scatter(x=[path_df['Date'].iloc[0], path_df['Date'].iloc[-1]], y=[entry_price_calculated, entry_price_calculated], mode='lines', name='Your Entry Basis', line=dict(color='#FF9900', dash='dash')))
    path_chart.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=200, template="plotly_white")
    st.plotly_chart(path_chart, use_container_width=True)
else:
    st.warning("Selected 'What-If' date parameters fall completely out of active operational data horizons.")
