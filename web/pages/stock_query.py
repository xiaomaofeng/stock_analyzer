# -*- coding: utf-8 -*-
"""股票查询页面 - 多语言版 + 指标学习"""
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

# 多语言配置
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
        'learn_indicators': '📚 指标学习',
        'select_indicator': '选择指标学习',
        'hide': '不显示',
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
        'learn_indicators': '📚 Indicator Guide',
        'select_indicator': 'Select indicator to learn',
        'hide': 'Hide',
    }
}

# 指标学习内容
LEARN_CONTENT = {
    'zh': {
        '均线系统': """
        ### 📈 均线系统 (Moving Average)
        
        **什么是均线？**
        均线是某段时间内收盘价的平均值，用于平滑价格波动，显示趋势方向。
        
        **常用均线：**
        - **MA5** (5日均线): 短期趋势，反映近期价格动向
        - **MA20** (20日均线): 中期趋势，月线级别
        - **MA60** (60日均线): 长期趋势，季线级别
        
        **使用技巧：**
        - 🟢 **多头排列**: MA5 > MA20 > MA60，上升趋势，买入信号
        - 🔴 **空头排列**: MA5 < MA20 < MA60，下降趋势，卖出信号
        - 🟡 **金叉**: 短期均线上穿长期均线，买入信号
        - 🟡 **死叉**: 短期均线下穿长期均线，卖出信号
        
        **注意事项：**
        - 均线滞后于价格，适合判断趋势而非捕捉拐点
        - 震荡行情中均线频繁交叉，容易发出假信号
        """,
        'MACD': """
        ### 📊 MACD (指数平滑异同平均线)
        
        **构成要素：**
        - **DIF线** (快线): 12日EMA - 26日EMA
        - **DEA线** (慢线): DIF的9日EMA
        - **MACD柱** (BAR): (DIF - DEA) × 2
        
        **核心用法：**
        
        **1. 金叉死叉信号**
        - 🟢 **MACD金叉**: DIF上穿DEA，买入信号
        - 🔴 **MACD死叉**: DIF下穿DEA，卖出信号
        
        **2. 背离信号（更可靠）**
        - 🟢 **底背离**: 价格创新低，MACD未创新低，强烈买入信号
        - 🔴 **顶背离**: 价格创新高，MACD未创新高，强烈卖出信号
        
        **3. 零轴判断**
        - 零轴上方: 多头市场
        - 零轴下方: 空头市场
        
        **实战技巧：**
        - 零轴附近金叉更可靠
        - MACD柱状线缩小时，趋势可能反转
        - 结合成交量确认信号强度
        """,
        'RSI/KDJ': """
        ### 🌡️ RSI (相对强弱指标)
        
        **RSI是什么？**
        RSI衡量价格上涨和下跌的相对强度，取值范围0-100。
        
        **关键阈值：**
        - **RSI > 80**: 超买区域，可能回调
        - **RSI < 20**: 超卖区域，可能反弹
        - **RSI 50**: 多空分界线
        
        **使用技巧：**
        - RSI在50以上，强势市场，逢低买入
        - RSI在50以下，弱势市场，逢高卖出
        - 背离信号比超买超卖更可靠
        
        ---
        
        ### 🎲 KDJ (随机指标)
        
        **构成要素：**
        - **K线** (快线): 反映最新价格位置
        - **D线** (慢线): K线的平滑，信号线
        - **J线**: 3K - 2D，敏感度最高
        
        **关键阈值：**
        - **K,D > 80**: 超买，考虑卖出
        - **K,D < 20**: 超卖，考虑买入
        
        **核心用法：**
        - 🟢 **金叉**: K上穿D，买入信号（20以下更可靠）
        - 🔴 **死叉**: K下穿D，卖出信号（80以上更可靠）
        
        **注意事项：**
        - KDJ在极端行情会钝化（长期超买/超卖）
        - 适合震荡行情，趋势行情容易失效
        - 结合MACD使用效果更好
        """,
        '布林带': """
        ### 🎯 布林带 (Bollinger Bands)
        
        **构成要素：**
        - **中轨** (MID): 20日均线
        - **上轨** (UPPER): 中轨 + 2倍标准差
        - **下轨** (LOWER): 中轨 - 2倍标准差
        
        **核心原理：**
        价格大多数时间在布林带内运行（约95%概率）
        
        **使用技巧：**
        
        **1. 轨道突破**
        - 🟢 突破上轨: 强势，但可能回调
        - 🔴 跌破下轨: 弱势，但可能反弹
        
        **2. 轨道收窄/扩张**
        - 收口（收窄）: 即将变盘，大行情要来
        - 开口（扩张）: 趋势延续，顺势操作
        
        **3. 中轨作用**
        - 上升趋势: 中轨是支撑位
        - 下降趋势: 中轨是阻力位
        
        **实战口诀：**
        - "三轨向上，看多做多"
        - "三轨向下，看空做空"
        - "收口观望，开口跟进"
        """,
        '成交量': """
        ### 📊 成交量 (Volume)
        
        **为什么重要？**
        成交量是价格变动的"能量"，验证趋势真实性。
        
        **量价关系法则：**
        
        **1. 量价同步（健康）**
        - 🟢 **价涨量增**: 上涨有支撑，趋势延续
        - 🔴 **价跌量缩**: 抛压减轻，可能见底
        
        **2. 量价背离（警惕）**
        - 🟡 **价涨量缩**: 上涨无力，可能见顶
        - 🟡 **价跌量增**: 恐慌抛售，可能加速下跌
        
        **特殊形态：**
        - **天量**: 成交量突然放大2倍以上，关键转折点
        - **地量**: 成交量极度萎缩，变盘前兆
        
        **使用技巧：**
        - 突破关键位置必须放量才有效
        - 盘整期放量突破，跟进买入
        - 上涨末期放天量，考虑离场
        """,
        '风险指标': """
        ### ⚠️ 风险指标解读
        
        **收益指标：**
        - **年化收益率**: 投资一年获得的收益率
        - **总收益率**: 整个持有期的累计收益
        
        **风险指标：**
        - **年化波动率**: 收益率的标准差，衡量价格波动大小
          - < 15%: 低波动，稳健
          - 15%-30%: 中等波动
          - > 30%: 高波动，高风险
        
        - **最大回撤**: 从高点到低点的最大亏损幅度
          - < 10%: 优秀
          - 10%-20%: 良好
          - > 30%: 风险较高
        
        **风险调整收益：**
        - **夏普比率**: 每承担一单位风险获得的超额收益
          - > 2.0: 优秀
          - 1.0-2.0: 良好
          - < 1.0: 一般
          - < 0: 不如存银行
        
        - **索提诺比率**: 只考虑下行风险的夏普比率
        - **卡尔玛比率**: 年化收益/最大回撤，越高越好
        
        **尾部风险：**
        - **VaR (风险价值)**: 95%置信度下的最大亏损
        - **CVaR**: 超过VaR时的平均亏损
        - **偏度**: 收益分布不对称性
        - **峰度**: 极端收益的概率
        """
    },
    'en': {
        'MA': """
        ### 📈 Moving Average (MA)
        
        **What is MA?**
        Moving Average is the average price over a specific period, used to smooth price fluctuations.
        
        **Common MAs:**
        - **MA5**: Short-term trend (5 days)
        - **MA20**: Medium-term trend (20 days)
        - **MA60**: Long-term trend (60 days)
        
        **Signals:**
        - 🟢 **Golden Cross**: Short MA crosses above Long MA (Buy)
        - 🔴 **Death Cross**: Short MA crosses below Long MA (Sell)
        - 🟢 **Bullish**: MA5 > MA20 > MA60 (Uptrend)
        - 🔴 **Bearish**: MA5 < MA20 < MA60 (Downtrend)
        """,
        'MACD': """
        ### 📊 MACD (Moving Average Convergence Divergence)
        
        **Components:**
        - **DIF**: 12-day EMA - 26-day EMA
        - **DEA**: 9-day EMA of DIF
        - **MACD Bar**: (DIF - DEA) × 2
        
        **Signals:**
        - 🟢 **Golden Cross**: DIF crosses above DEA (Buy)
        - 🔴 **Death Cross**: DIF crosses below DEA (Sell)
        - 🟢 **Bullish Divergence**: Price makes lower low, MACD makes higher low
        - 🔴 **Bearish Divergence**: Price makes higher high, MACD makes lower high
        """,
        'RSI/KDJ': """
        ### 🌡️ RSI (Relative Strength Index)
        
        **RSI Levels:**
        - **> 80**: Overbought (Possible sell)
        - **< 20**: Oversold (Possible buy)
        - **50**: Neutral
        
        ### 🎲 KDJ (Stochastic Oscillator)
        
        **Levels:**
        - **> 80**: Overbought
        - **< 20**: Oversold
        
        **Signals:**
        - 🟢 **Golden Cross**: K crosses above D (Buy)
        - 🔴 **Death Cross**: K crosses below D (Sell)
        """,
        'Bollinger': """
        ### 🎯 Bollinger Bands
        
        **Components:**
        - **Middle Band**: 20-day MA
        - **Upper Band**: Middle + 2×StdDev
        - **Lower Band**: Middle - 2×StdDev
        
        **Usage:**
        - Price touches Upper: Overbought
        - Price touches Lower: Oversold
        - Bands squeeze: Volatility expansion coming
        """,
        'Volume': """
        ### 📊 Volume Analysis
        
        **Price-Volume Relationship:**
        - 🟢 **Rising price + Rising volume**: Healthy uptrend
        - 🔴 **Falling price + Falling volume**: Selling pressure easing
        - 🟡 **Rising price + Falling volume**: Weak rally (Caution)
        - 🟡 **Falling price + Rising volume**: Panic selling
        """,
        'Risk': """
        ### ⚠️ Risk Metrics
        
        **Return:**
        - **Annualized Return**: Return over one year
        
        **Risk:**
        - **Volatility**: Standard deviation of returns
          - < 15%: Low risk
          - 15-30%: Medium risk
          - > 30%: High risk
        
        - **Max Drawdown**: Peak to trough decline
          - < 10%: Excellent
          - 10-20%: Good
          - > 30%: High risk
        
        **Risk-Adjusted:**
        - **Sharpe Ratio**: Return per unit of risk
          - > 2.0: Excellent
          - 1.0-2.0: Good
          - < 1.0: Poor
        """
    }
}

lang = st.session_state.get('lang', 'zh')
t = lambda k: I18N[lang].get(k, k)

# ===== 侧边栏：指标学习 =====
with st.sidebar:
    st.header(t('learn_indicators'))
    
    guide_options = {
        'zh': ['不显示', '均线系统', 'MACD', 'RSI/KDJ', '布林带', '成交量', '风险指标'],
        'en': ['Hide', 'MA', 'MACD', 'RSI/KDJ', 'Bollinger', 'Volume', 'Risk']
    }
    
    indicator_guide = st.selectbox(
        t('select_indicator'),
        options=guide_options[lang]
    )
    
    if indicator_guide != t('hide'):
        # 映射选择到内容键
        content_map = {
            'zh': {
                '均线系统': '均线系统',
                'MACD': 'MACD',
                'RSI/KDJ': 'RSI/KDJ',
                '布林带': '布林带',
                '成交量': '成交量',
                '风险指标': '风险指标'
            },
            'en': {
                'MA': 'MA',
                'MACD': 'MACD',
                'RSI/KDJ': 'RSI/KDJ',
                'Bollinger': 'Bollinger',
                'Volume': 'Volume',
                'Risk': 'Risk'
            }
        }
        
        content_key = content_map[lang].get(indicator_guide, indicator_guide)
        if content_key in LEARN_CONTENT[lang]:
            st.markdown(LEARN_CONTENT[lang][content_key])

# ===== 主界面 =====
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
