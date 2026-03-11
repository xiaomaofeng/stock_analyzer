# -*- coding: utf-8 -*-
"""回测页面 - 多语言版"""
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

st.set_page_config(page_title="Backtest | 策略回测", layout="wide")

I18N = {
    'zh': {
        'title': '🔄 策略回测',
        'params': '回测参数',
        'stock': '股票代码',
        'strategy': '策略',
        'capital': '初始资金',
        'commission': '手续费率',
        'days': '回测时长',
        'run': '开始回测',
        'results': '回测结果',
        'total_return': '总收益率',
        'annual_return': '年化收益',
        'max_dd': '最大回撤',
        'sharpe': '夏普比率',
        'trades': '交易次数',
        'win_rate': '胜率',
        'equity': '净值曲线',
        'trades_record': '交易记录',
        'date': '日期',
        'action': '操作',
        'price': '价格',
        'quantity': '数量',
        'amount': '金额',
        'insufficient': '数据不足，请尝试其他股票',
    },
    'en': {
        'title': '🔄 Strategy Backtest',
        'params': 'Parameters',
        'stock': 'Stock Code',
        'strategy': 'Strategy',
        'capital': 'Initial Capital',
        'commission': 'Commission Rate',
        'days': 'Backtest Period',
        'run': 'Run Backtest',
        'results': 'Results',
        'total_return': 'Total Return',
        'annual_return': 'Annual Return',
        'max_dd': 'Max Drawdown',
        'sharpe': 'Sharpe Ratio',
        'trades': 'Trades',
        'win_rate': 'Win Rate',
        'equity': 'Equity Curve',
        'trades_record': 'Trade Records',
        'date': 'Date',
        'action': 'Action',
        'price': 'Price',
        'quantity': 'Quantity',
        'amount': 'Amount',
        'insufficient': 'Insufficient data, try another stock',
    }
}

lang = st.session_state.get('lang', 'zh')
t = lambda k: I18N[lang].get(k, k)

st.title(t('title'))

with st.sidebar:
    st.header(t('params'))
    stock_code = st.text_input(t('stock'), value="159892")
    
    strategies = ["MA Cross", "RSI", "MACD"] if lang == 'en' else ["均线交叉", "RSI超买超卖", "MACD金叉死叉"]
    strategy = st.selectbox(t('strategy'), strategies)
    
    initial_capital = st.number_input(t('capital'), 10000, 10000000, 100000, 10000)
    commission = st.slider(t('commission'), 0.0001, 0.005, 0.0003, 0.0001, format="%.4f")
    
    days_options = [252, 500, 1000]
    days_labels = [f"{x} days (~{x//252}y)" if lang == 'en' else f"近{x}天(~{x//252}年)" for x in days_options]
    days = st.selectbox(t('days'), options=days_options, format_func=lambda x: days_labels[days_options.index(x)])
    
    run_btn = st.button(t('run'), type='primary', use_container_width=True)

if run_btn and stock_code:
    with st.spinner("Running backtest..." if lang == 'en' else "回测中..."):
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
                st.error(t('insufficient'))
                st.stop()
            
            df = pd.DataFrame([{
                'trade_date': p.trade_date,
                'open_price': float(p.open_price) if p.open_price else 0,
                'high_price': float(p.high_price) if p.high_price else 0,
                'low_price': float(p.low_price) if p.low_price else 0,
                'close_price': float(p.close_price) if p.close_price else 0,
                'volume': p.volume or 0,
            } for p in prices])
            
            calc = TechnicalCalculator()
            df = calc.calculate_all(df)
            
            config = BacktestConfig(initial_capital=initial_capital, commission_rate=commission)
            engine = BacktestEngine(config)
            
            if strategy in ["MA Cross", "均线交叉"]:
                strat = MAStrategy(5, 20)
            elif strategy in ["RSI", "RSI超买超卖"]:
                strat = RSIStrategy(70, 30)
            else:
                strat = MACDStrategy()
            
            engine.set_strategy(strat)
            engine.load_data(df)
            results = engine.run()
            
            st.subheader(t('results'))
            
            r1, r2, r3, r4 = st.columns(4)
            r1.metric(t('total_return'), f"{results['total_return']*100:.2f}%")
            r2.metric(t('annual_return'), f"{results['annualized_return']*100:.2f}%")
            r3.metric(t('max_dd'), f"{results['max_drawdown']*100:.2f}%")
            r4.metric(t('sharpe'), f"{results['sharpe_ratio']:.2f}")
            
            st.subheader(t('equity'))
            daily_values = results['daily_values']
            if daily_values:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(len(daily_values))),
                    y=[v['total_value'] for v in daily_values],
                    mode='lines',
                    name='Equity' if lang == 'en' else '总资产',
                    line=dict(color='#1890ff', width=2)
                ))
                fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            if results['trades']:
                st.subheader(f"{t('trades_record')} ({len(results['trades'])})")
                trades_df = pd.DataFrame(results['trades'][:50])
                trades_df.columns = [t('date'), t('action'), t('price'), t('quantity'), t('amount'), 'PnL']
                st.dataframe(trades_df, use_container_width=True)
                
        finally:
            db.close()
