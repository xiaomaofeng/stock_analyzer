# -*- coding: utf-8 -*-
"""回测页面"""
import sys
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config import get_session_factory
from database.models import DailyPrice
from processors import TechnicalCalculator
from backtest.engine import BacktestEngine, BacktestConfig
from backtest.strategies import MAStrategy, RSIStrategy, MACDStrategy

st.set_page_config(page_title="策略回测", layout="wide")

st.title("🔄 策略回测")

# 侧边栏参数
with st.sidebar:
    st.header("回测参数")
    stock_code = st.text_input("股票代码", value="159892")
    strategy = st.selectbox("策略", ["均线交叉", "RSI超买超卖", "MACD金叉死叉"])
    initial_capital = st.number_input("初始资金", 10000, 10000000, 100000, 10000)
    commission = st.slider("手续费率", 0.0001, 0.005, 0.0003, 0.0001, format="%.4f")
    
    days = st.selectbox("回测时长", [252, 500, 1000], index=1, format_func=lambda x: f"近{x}天(~{x//252}年)")
    
    run_btn = st.button("开始回测", type="primary", use_container_width=True)

if run_btn and stock_code:
    with st.spinner("回测中..."):
        SessionLocal = get_session_factory()
        db = SessionLocal()
        
        try:
            end = datetime.now()
            start = end - timedelta(days=days + 100)
            
            prices = db.query(DailyPrice).filter(
                DailyPrice.stock_code == stock_code,
                DailyPrice.trade_date >= start,
                DailyPrice.trade_date <= end
            ).order_by(DailyPrice.trade_date).all()
            
            if len(prices) < 60:
                st.error("数据不足，请尝试其他股票")
                st.stop()
            
            df = pd.DataFrame([{
                'trade_date': p.trade_date,
                'open_price': float(p.open_price) if p.open_price else 0,
                'high_price': float(p.high_price) if p.high_price else 0,
                'low_price': float(p.low_price) if p.low_price else 0,
                'close_price': float(p.close_price) if p.close_price else 0,
                'volume': p.volume or 0,
            } for p in prices])
            
            # 计算指标
            calc = TechnicalCalculator()
            df = calc.calculate_all(df)
            
            # 配置回测
            config = BacktestConfig(initial_capital=initial_capital, commission_rate=commission)
            engine = BacktestEngine(config)
            
            # 选择策略
            if strategy == "均线交叉":
                strat = MAStrategy(5, 20)
            elif strategy == "RSI超买超卖":
                strat = RSIStrategy(70, 30)
            else:
                strat = MACDStrategy()
            
            engine.set_strategy(strat)
            engine.load_data(df)
            results = engine.run()
            
            # 显示结果
            st.subheader("回测结果")
            
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("总收益率", f"{results['total_return']*100:.2f}%")
            r2.metric("年化收益率", f"{results['annualized_return']*100:.2f}%")
            r3.metric("最大回撤", f"{results['max_drawdown']*100:.2f}%")
            r4.metric("夏普比率", f"{results['sharpe_ratio']:.2f}")
            
            # 净值曲线
            st.subheader("净值曲线")
            daily_values = results['daily_values']
            if daily_values:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(len(daily_values))),
                    y=[v['total_value'] for v in daily_values],
                    mode='lines',
                    name='总资产',
                    line=dict(color='#1890ff', width=2)
                ))
                fig.update_layout(height=400, showlegend=False, xaxis_title="交易日", yaxis_title="总资产")
                st.plotly_chart(fig, use_container_width=True)
            
            # 交易记录
            if results['trades']:
                st.subheader(f"交易记录 ({len(results['trades'])}笔)")
                trades_df = pd.DataFrame(results['trades'][:50])
                st.dataframe(trades_df, use_container_width=True)
                
        finally:
            db.close()
