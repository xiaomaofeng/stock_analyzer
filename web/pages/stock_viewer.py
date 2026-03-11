# -*- coding: utf-8 -*-
"""个股分析 - 详细图表"""
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
from plotly.subplots import make_subplots

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator
from analysis import TrendAnalyzer
from analysis.risk_metrics import RiskMetrics

st.set_page_config(page_title="Stock Viewer | 个股分析", layout="wide")

I18N = {
    'zh': {
        'title': '📈 个股分析',
        'select_stock': '选择股票',
        'time_range': '时间范围',
        'days': '{}天',
        'latest_price': '最新价',
        'change': '涨跌幅',
        'volume': '成交量',
        'high_52w': '52周最高',
        'low_52w': '52周最低',
        'kline': 'K线图',
        'trend_analysis': '趋势分析',
        'technical_indicators': '技术指标',
        'risk_metrics': '风险指标',
        'direction': '趋势方向',
        'strength': '趋势强度',
        'duration': '持续天数',
        'support': '支撑位',
        'resistance': '阻力位',
        'annual_return': '年化收益',
        'volatility': '波动率',
        'max_dd': '最大回撤',
        'sharpe': '夏普比率',
    },
    'en': {
        'title': '📈 Stock Viewer',
        'select_stock': 'Select Stock',
        'time_range': 'Time Range',
        'days': '{} days',
        'latest_price': 'Latest Price',
        'change': 'Change',
        'volume': 'Volume',
        'high_52w': '52W High',
        'low_52w': '52W Low',
        'kline': 'Candlestick Chart',
        'trend_analysis': 'Trend Analysis',
        'technical_indicators': 'Technical Indicators',
        'risk_metrics': 'Risk Metrics',
        'direction': 'Direction',
        'strength': 'Strength',
        'duration': 'Duration',
        'support': 'Support',
        'resistance': 'Resistance',
        'annual_return': 'Annual Return',
        'volatility': 'Volatility',
        'max_dd': 'Max Drawdown',
        'sharpe': 'Sharpe Ratio',
    }
}

lang = st.session_state.get('lang', 'zh')
t = lambda k: I18N[lang].get(k, k)

st.title(t('title'))

SessionLocal = get_session_factory()
db = SessionLocal()

try:
    stocks = db.query(Stock).order_by(Stock.stock_code).all()
    if not stocks:
        st.info("No stocks in database. Please add stocks from Stock Query.")
        st.stop()
    
    stock_options = [f"{s.stock_code} - {s.stock_name}" for s in stocks]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected = st.selectbox(t('select_stock'), options=stock_options)
        stock_code = selected.split(" - ")[0]
    
    with col2:
        days = st.selectbox(t('time_range'), options=[60, 120, 252, 500], format_func=lambda x: t('days').format(x))
    
    # 加载数据
    prices = db.query(DailyPrice).filter(
        DailyPrice.stock_code == stock_code
    ).order_by(DailyPrice.trade_date.desc()).limit(days).all()
    
    if not prices:
        st.error(f"No data for {stock_code}")
        st.stop()
    
    df = pd.DataFrame([{
        'trade_date': p.trade_date,
        'open_price': float(p.open_price) if p.open_price else 0,
        'high_price': float(p.high_price) if p.high_price else 0,
        'low_price': float(p.low_price) if p.low_price else 0,
        'close_price': float(p.close_price) if p.close_price else 0,
        'volume': p.volume or 0,
        'change_pct': float(p.change_pct) if p.change_pct else 0,
    } for p in reversed(prices)])
    
    latest = df.iloc[-1]
    
    # 基本信息
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(t('latest_price'), f"{latest['close_price']:.3f}", f"{latest['change_pct']:.2f}%")
    c2.metric(t('change'), f"{latest['change_pct']:+.2f}%")
    c3.metric(t('volume'), f"{latest['volume']/10000:.0f}万")
    c4.metric(t('high_52w'), f"{df['high_price'].max():.3f}")
    c5.metric(t('low_52w'), f"{df['low_price'].min():.3f}")
    
    # K线图
    st.subheader(t('kline'))
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(
        x=df['trade_date'],
        open=df['open_price'],
        high=df['high_price'],
        low=df['low_price'],
        close=df['close_price']
    ), row=1, col=1)
    colors = ['red' if df.iloc[i]['close_price'] >= df.iloc[i]['open_price'] else 'green' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df['trade_date'], y=df['volume'], marker_color=colors), row=2, col=1)
    fig.update_layout(height=600, showlegend=False, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # 分析和指标
    tab1, tab2, tab3 = st.tabs([t('trend_analysis'), t('technical_indicators'), t('risk_metrics')])
    
    with tab1:
        try:
            analyzer = TrendAnalyzer(df)
            result = analyzer.analyze()
            
            col1, col2, col3 = st.columns(3)
            col1.metric(t('direction'), result.direction.value)
            col2.metric(t('strength'), result.strength.value)
            col3.metric(t('duration'), f"{result.trend_days} days")
            
            st.info(result.description)
            
            if result.support_levels:
                st.markdown(f"**{t('support')}:** {', '.join([f'{s:.3f}' for s in result.support_levels[:3]])}")
            if result.resistance_levels:
                st.markdown(f"**{t('resistance')}:** {', '.join([f'{r:.3f}' for r in result.resistance_levels[:3]])}")
        except Exception as e:
            st.error(f"Analysis error: {e}")
    
    with tab2:
        indicators = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_code == stock_code
        ).order_by(TechnicalIndicator.trade_date.desc()).first()
        
        if indicators:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**MA**")
                st.write(f"MA5: {indicators.ma5:.3f}" if indicators.ma5 else "MA5: -")
                st.write(f"MA20: {indicators.ma20:.3f}" if indicators.ma20 else "MA20: -")
                st.write(f"MA60: {indicators.ma60:.3f}" if indicators.ma60 else "MA60: -")
            with col2:
                st.markdown("**MACD**")
                st.write(f"DIF: {indicators.macd_dif:.4f}" if indicators.macd_dif else "DIF: -")
                st.write(f"DEA: {indicators.macd_dea:.4f}" if indicators.macd_dea else "DEA: -")
            with col3:
                st.markdown("**RSI/KDJ**")
                st.write(f"RSI12: {indicators.rsi12:.2f}" if indicators.rsi12 else "RSI12: -")
                st.write(f"K: {indicators.k_value:.2f}" if indicators.k_value else "K: -")
                st.write(f"D: {indicators.d_value:.2f}" if indicators.d_value else "D: -")
    
    with tab3:
        try:
            returns = df['close_price'].pct_change().dropna()
            if len(returns) > 30:
                metrics = RiskMetrics(returns)
                result = metrics.calculate_all()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric(t('annual_return'), f"{result.annualized_return*100:.1f}%")
                col2.metric(t('volatility'), f"{result.annualized_volatility*100:.1f}%")
                col3.metric(t('max_dd'), f"{result.max_drawdown*100:.1f}%")
                col4.metric(t('sharpe'), f"{result.sharpe_ratio:.2f}")
        except Exception as e:
            st.error(f"Risk metrics error: {e}")

except Exception as e:
    st.error(f"Error: {e}")
finally:
    db.close()
