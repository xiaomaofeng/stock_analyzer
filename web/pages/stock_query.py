# -*- coding: utf-8 -*-
"""股票查询页面"""
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

st.set_page_config(page_title="股票查询", layout="wide")

st.title("🔍 股票查询与分析")

# 输入区域
col1, col2, col3 = st.columns([3, 2, 2])
with col1:
    stock_code = st.text_input("股票代码", value="159892", placeholder="如: 159892, 000001").strip()
with col2:
    days = st.selectbox("数据范围", options=[60, 120, 252, 500], index=2, format_func=lambda x: f"近{x}天")
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    query_btn = st.button("查询并分析", type="primary", use_container_width=True)

if query_btn and stock_code:
    with st.spinner(f"获取 {stock_code} 数据中..."):
        settings = get_settings()
        settings.ensure_directories()
        
        SessionLocal = get_session_factory()
        db = SessionLocal()
        
        try:
            # 检查本地数据
            existing = db.query(DailyPrice).filter(DailyPrice.stock_code == stock_code).count()
            
            if existing == 0:
                st.info("从网络获取数据...")
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
                    st.error("无法获取数据")
                    st.stop()
                
                # 保存数据
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
                
                # 计算指标
                calculator = TechnicalCalculator()
                df_calc = calculator.calculate_all(df)
                save_indicators_to_db(stock_code, df_calc, db)
                st.success(f"导入 {len(df)} 条数据")
            else:
                st.info(f"使用本地 {existing} 条数据")
            
            # 读取数据
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
                
                # 指标卡片
                st.subheader("基本信息")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("最新价", f"{latest['close_price']:.3f}", f"{latest['change_pct']:.2f}%")
                c2.metric("成交量", f"{latest['volume']/10000:.0f}万")
                c3.metric("最高", f"{df['high_price'].max():.3f}")
                c4.metric("最低", f"{df['low_price'].min():.3f}")
                
                # K线图
                st.subheader("K线走势")
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df['trade_date'], open=df['open_price'], high=df['high_price'], low=df['low_price'], close=df['close_price']), row=1, col=1)
                colors = ['red' if df.iloc[i]['close_price'] >= df.iloc[i]['open_price'] else 'green' for i in range(len(df))]
                fig.add_trace(go.Bar(x=df['trade_date'], y=df['volume'], marker_color=colors), row=2, col=1)
                fig.update_layout(height=500, showlegend=False, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
                # 技术指标
                if indicators:
                    st.subheader("技术指标")
                    ic1, ic2, ic3 = st.columns(3)
                    with ic1:
                        st.markdown(f"**均线**  \nMA5: {indicators.ma5:.2f}  \nMA20: {indicators.ma20:.2f}  \nMA60: {indicators.ma60:.2f}")
                    with ic2:
                        st.markdown(f"**MACD**  \nDIF: {indicators.macd_dif:.4f}  \nDEA: {indicators.macd_dea:.4f}")
                    with ic3:
                        st.markdown(f"**RSI/KDJ**  \nRSI12: {indicators.rsi12:.1f}  \nK: {indicators.k_value:.1f}  \nD: {indicators.d_value:.1f}")
                
                # 趋势分析
                try:
                    analyzer = TrendAnalyzer(df)
                    result = analyzer.analyze()
                    st.subheader("趋势分析")
                    tc1, tc2, tc3 = st.columns(3)
                    tc1.metric("趋势方向", result.direction.value)
                    tc2.metric("趋势强度", result.strength.value)
                    tc3.metric("持续天数", f"{result.trend_days}天")
                    st.info(result.description)
                except:
                    pass
                
                # 数据导出
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("下载CSV", csv, f"{stock_code}.csv", "text/csv")
                
        finally:
            db.close()
