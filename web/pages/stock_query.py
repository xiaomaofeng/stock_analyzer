# -*- coding: utf-8 -*-
"""股票查询页面 - 多语言版"""
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
from datetime import datetime, timedelta

from config import get_session_factory, get_settings
from database.models import Stock, DailyPrice, TechnicalIndicator
from collectors import AKShareCollector
from processors import TechnicalCalculator
from processors.calculators import save_indicators_to_db
from analysis import TrendAnalyzer
from analysis.risk_metrics import RiskMetrics

st.set_page_config(page_title="Stock Query | 股票查询", layout="wide")

I18N = {
    'zh': {
        'title': '🔍 股票查询与分析',
        'desc': '输入股票代码，系统自动：获取数据 → 存入数据库 → 计算指标 → 生成报告',
        'stock_code': '股票代码',
        'days': '数据范围',
        'query': '查询并分析',
        'fetching': '正在获取 {} 数据...',
        'from_network': '从网络获取数据...',
        'calculating': '计算技术指标...',
        'success_import': '成功导入 {} 条数据',
        'use_local': '使用本地 {} 条数据',
        'analysis': '{} 分析报告',
        'latest_price': '最新价',
        'change': '涨跌额',
        'volume': '成交量',
        'range': '区间高低',
        'kline': 'K线走势',
        'indicators': '技术指标',
        'trend': '趋势分析',
        'risk': '风险指标',
        'direction': '趋势方向',
        'strength': '趋势强度',
        'duration': '持续天数',
        'support': '支撑位',
        'resistance': '阻力位',
        'annual_return': '年化收益',
        'volatility': '波动率',
        'max_dd': '最大回撤',
        'sharpe': '夏普比率',
        'download': '下载CSV',
        'ma': '均线',
        'macd': 'MACD',
        'rsi_kdj': 'RSI/KDJ',
    },
    'en': {
        'title': '🔍 Stock Query & Analysis',
        'desc': 'Enter stock code to: fetch data → save to DB → calculate indicators → generate report',
        'stock_code': 'Stock Code',
        'days': 'Data Range',
        'query': 'Query & Analyze',
        'fetching': 'Fetching {} data...',
        'from_network': 'Fetching from network...',
        'calculating': 'Calculating indicators...',
        'success_import': 'Successfully imported {} records',
        'use_local': 'Using local {} records',
        'analysis': '{} Analysis Report',
        'latest_price': 'Latest Price',
        'change': 'Change',
        'volume': 'Volume',
        'range': 'Range',
        'kline': 'Candlestick Chart',
        'indicators': 'Technical Indicators',
        'trend': 'Trend Analysis',
        'risk': 'Risk Metrics',
        'direction': 'Direction',
        'strength': 'Strength',
        'duration': 'Duration',
        'support': 'Support',
        'resistance': 'Resistance',
        'annual_return': 'Annual Return',
        'volatility': 'Volatility',
        'max_dd': 'Max Drawdown',
        'sharpe': 'Sharpe Ratio',
        'download': 'Download CSV',
        'ma': 'Moving Average',
        'macd': 'MACD',
        'rsi_kdj': 'RSI/KDJ',
    }
}

lang = st.session_state.get('lang', 'zh')
t = lambda k: I18N[lang].get(k, k)

st.title(t('title'))
st.markdown(t('desc'))

col1, col2, col3 = st.columns([3, 2, 2])
with col1:
    stock_code = st.text_input(t('stock_code'), value="159892", placeholder="159892, 000001, 600519").strip()
with col2:
    days = st.selectbox(t('days'), options=[60, 120, 252, 500, 1000], index=2, format_func=lambda x: f"{x} days" if lang == 'en' else f"近{x}天")
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    query_btn = st.button(t('query'), type="primary", use_container_width=True)

if query_btn and stock_code:
    with st.spinner(t('fetching').format(stock_code)):
        settings = get_settings()
        settings.ensure_directories()
        
        SessionLocal = get_session_factory()
        db = SessionLocal()
        
        try:
            existing = db.query(DailyPrice).filter(DailyPrice.stock_code == stock_code).count()
            
            if existing == 0:
                st.info(t('from_network'))
                collector = AKShareCollector(request_delay=0.5)
                stock_info = collector.get_stock_info(stock_code)
                
                stock = Stock(
                    stock_code=stock_code,
                    stock_name=stock_info.get('stock_name', stock_code) if stock_info else stock_code,
                    exchange=collector._get_exchange(stock_code),
                )
                db.merge(stock)
                db.commit()
                
                end = datetime.now()
                start = end - timedelta(days=days * 2)
                df = collector.get_daily_prices(stock_code, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
                
                if df.empty:
                    st.error("No data available" if lang == 'en' else "无法获取数据")
                    st.stop()
                
                for _, row in df.iterrows():
                    dp = DailyPrice(
                        stock_code=stock_code,
                        trade_date=row['trade_date'],
                        open_price=float(row['open_price']) if pd.notna(row['open_price']) else None,
                        high_price=float(row['high_price']) if pd.notna(row['high_price']) else None,
                        low_price=float(row['low_price']) if pd.notna(row['low_price']) else None,
                        close_price=float(row['close_price']) if pd.notna(row['close_price']) else None,
                        volume=int(row['volume']) if pd.notna(row['volume']) else None,
                    )
                    db.merge(dp)
                db.commit()
                
                calculator = TechnicalCalculator()
                df_calc = calculator.calculate_all(df)
                save_indicators_to_db(stock_code, df_calc, db)
                st.success(t('success_import').format(len(df)))
            else:
                st.info(t('use_local').format(existing))
            
            prices = db.query(DailyPrice).filter(DailyPrice.stock_code == stock_code).order_by(DailyPrice.trade_date.desc()).limit(days).all()
            indicators = db.query(TechnicalIndicator).filter(TechnicalIndicator.stock_code == stock_code).order_by(TechnicalIndicator.trade_date.desc()).first()
            
            df = pd.DataFrame([{
                'trade_date': p.trade_date,
                'open_price': float(p.open_price) if p.open_price else 0,
                'high_price': float(p.high_price) if p.high_price else 0,
                'low_price': float(p.low_price) if p.low_price else 0,
                'close_price': float(p.close_price) if p.close_price else 0,
                'volume': p.volume or 0,
                'change_pct': float(p.change_pct) if p.change_pct else 0,
            } for p in reversed(prices)])
            
            if not df.empty:
                latest = df.iloc[-1]
                
                st.divider()
                st.header(t('analysis').format(stock_code))
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t('latest_price'), f"{latest['close_price']:.3f}", f"{latest['change_pct']:.2f}%")
                c2.metric(t('change'), f"{(latest['close_price'] - (df.iloc[-2]['close_price'] if len(df) > 1 else latest['close_price'])):+.3f}")
                c3.metric(t('volume'), f"{latest['volume']/10000:.0f}万")
                c4.metric(t('range'), f"{df['low_price'].min():.3f} - {df['high_price'].max():.3f}")
                
                st.subheader(t('kline'))
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df['trade_date'], open=df['open_price'], high=df['high_price'], low=df['low_price'], close=df['close_price']), row=1, col=1)
                colors = ['red' if df.iloc[i]['close_price'] >= df.iloc[i]['open_price'] else 'green' for i in range(len(df))]
                fig.add_trace(go.Bar(x=df['trade_date'], y=df['volume'], marker_color=colors), row=2, col=1)
                fig.update_layout(height=500, showlegend=False, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander(t('indicators'), expanded=True):
                    if indicators:
                        ic1, ic2, ic3 = st.columns(3)
                        with ic1:
                            st.markdown(f"**{t('ma')}**")
                            st.write(f"MA5: {indicators.ma5:.2f}" if indicators.ma5 else "MA5: -")
                            st.write(f"MA20: {indicators.ma20:.2f}" if indicators.ma20 else "MA20: -")
                            st.write(f"MA60: {indicators.ma60:.2f}" if indicators.ma60 else "MA60: -")
                        with ic2:
                            st.markdown(f"**{t('macd')}**")
                            st.write(f"DIF: {indicators.macd_dif:.4f}" if indicators.macd_dif else "DIF: -")
                            st.write(f"DEA: {indicators.macd_dea:.4f}" if indicators.macd_dea else "DEA: -")
                        with ic3:
                            st.markdown(f"**{t('rsi_kdj')}**")
                            st.write(f"RSI12: {indicators.rsi12:.1f}" if indicators.rsi12 else "RSI12: -")
                            st.write(f"K: {indicators.k_value:.1f}" if indicators.k_value else "K: -")
                            st.write(f"D: {indicators.d_value:.1f}" if indicators.d_value else "D: -")
                
                with st.expander(t('trend'), expanded=True):
                    try:
                        analyzer = TrendAnalyzer(df)
                        result = analyzer.analyze()
                        tc1, tc2, tc3 = st.columns(3)
                        tc1.metric(t('direction'), result.direction.value)
                        tc2.metric(t('strength'), result.strength.value)
                        tc3.metric(t('duration'), f"{result.trend_days} days" if lang == 'en' else f"{result.trend_days}天")
                        st.info(result.description)
                        if result.support_levels:
                            st.markdown(f"**{t('support')}:** {', '.join([f'{s:.3f}' for s in result.support_levels[:3]])}")
                        if result.resistance_levels:
                            st.markdown(f"**{t('resistance')}:** {', '.join([f'{r:.3f}' for r in result.resistance_levels[:3]])}")
                    except Exception as e:
                        st.warning(f"Trend analysis error: {e}")
                
                with st.expander(t('risk'), expanded=True):
                    try:
                        returns = df['close_price'].pct_change().dropna()
                        if len(returns) > 30:
                            metrics = RiskMetrics(returns)
                            result = metrics.calculate_all()
                            rc1, rc2, rc3, rc4 = st.columns(4)
                            rc1.metric(t('annual_return'), f"{result.annualized_return*100:.1f}%")
                            rc2.metric(t('volatility'), f"{result.annualized_volatility*100:.1f}%")
                            rc3.metric(t('max_dd'), f"{result.max_drawdown*100:.1f}%")
                            rc4.metric(t('sharpe'), f"{result.sharpe_ratio:.2f}")
                    except Exception as e:
                        st.warning(f"Risk metrics error: {e}")
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(t('download'), csv, f"{stock_code}_data.csv", "text/csv")
                
        finally:
            db.close()
