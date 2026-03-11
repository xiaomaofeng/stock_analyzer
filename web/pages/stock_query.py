# -*- coding: utf-8 -*-
"""股票查询页面 - 输入代码自动获取数据并分析"""
import sys
from pathlib import Path
import os

# 设置项目根目录
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


def show():
    """显示股票查询页面"""
    st.title("🔍 股票查询与分析")
    
    # 指标学习模块侧边栏
    with st.sidebar:
        st.header("📚 指标学习")
        indicator_guide = st.selectbox(
            "选择指标学习",
            ["不显示", "均线系统", "MACD", "RSI/KDJ", "布林带", "成交量", "风险指标解释"]
        )
        
        if indicator_guide != "不显示":
            show_indicator_guide(indicator_guide)
    
    st.markdown("""
    输入股票代码，系统自动：
    1. 从AKShare获取历史数据
    2. 存入本地数据库
    3. 计算技术指标
    4. 生成分析报告
    """)
    
    # 查询输入区域 - 使用更合理的列宽
    col1, col2, col3 = st.columns([3, 2, 2])
    
    with col1:
        stock_code = st.text_input(
            "股票代码",
            value="159892",
            placeholder="输入股票代码，如：159892, 000001, 600519"
        ).strip()
    
    with col2:
        days = st.selectbox(
            "数据范围",
            options=[60, 120, 252, 500, 1000],
            index=2,
            format_func=lambda x: f"近{x}天"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        query_btn = st.button("查询并分析", type="primary", use_container_width=True)
    
    if query_btn and stock_code:
        try:
            with st.spinner(f"正在获取 {stock_code} 数据并分析..."):
                process_stock(stock_code, days)
        except Exception as e:
            st.error(f"处理失败: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


def show_indicator_guide(guide_type: str):
    """显示指标学习指南"""
    if guide_type == "均线系统":
        st.markdown("""
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
        """)
        
    elif guide_type == "MACD":
        st.markdown("""
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
        """)
        
    elif guide_type == "RSI/KDJ":
        st.markdown("""
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
        """)
        
    elif guide_type == "布林带":
        st.markdown("""
        ### 🎯 布林带 (BOLL)
        
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
        """)
        
    elif guide_type == "成交量":
        st.markdown("""
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
        """)
        
    elif guide_type == "风险指标解释":
        st.markdown("""
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
        """)


def process_stock(stock_code: str, days: int):
    """处理股票查询、存储和分析"""
    
    settings = get_settings()
    settings.ensure_directories()
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 检查数据库中是否已有数据
        existing_count = db.query(DailyPrice).filter(
            DailyPrice.stock_code == stock_code
        ).count()
        
        if existing_count == 0:
            # 从AKShare获取数据
            st.info(f"数据库中没有 {stock_code}，正在从AKShare获取...")
            
            collector = AKShareCollector(request_delay=0.5)
            
            # 获取股票信息
            stock_info = collector.get_stock_info(stock_code)
            
            # 保存股票信息
            stock = Stock(
                stock_code=stock_code,
                stock_name=stock_info.get('stock_name', stock_code) if stock_info else stock_code,
                exchange=collector._get_exchange(stock_code),
                industry=stock_info.get('industry', '') if stock_info else ''
            )
            db.merge(stock)
            db.commit()
            
            # 获取历史数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)
            
            df = collector.get_daily_prices(
                stock_code,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                adjust='qfq'
            )
            
            if df.empty:
                st.error(f"无法获取 {stock_code} 的数据，请检查代码是否正确")
                return
            
            # 保存到数据库
            progress_bar = st.progress(0)
            for idx, row in df.iterrows():
                daily_price = DailyPrice(
                    stock_code=stock_code,
                    trade_date=row['trade_date'],
                    open_price=float(row['open_price']) if pd.notna(row['open_price']) else None,
                    high_price=float(row['high_price']) if pd.notna(row['high_price']) else None,
                    low_price=float(row['low_price']) if pd.notna(row['low_price']) else None,
                    close_price=float(row['close_price']) if pd.notna(row['close_price']) else None,
                    volume=int(row['volume']) if pd.notna(row['volume']) else None,
                )
                db.merge(daily_price)
                progress_bar.progress(min((idx + 1) / len(df), 1.0))
            
            db.commit()
            progress_bar.empty()
            st.success(f"成功导入 {len(df)} 条历史数据")
            
            # 计算技术指标
            st.info("正在计算技术指标...")
            calculate_indicators_for_stock(stock_code, db)
            st.success("技术指标计算完成")
        else:
            st.info(f"数据库中已有 {stock_code} 的 {existing_count} 条数据，直接分析")
        
        # 显示分析报告
        display_analysis(stock_code, days, db)
        
    finally:
        db.close()


def calculate_indicators_for_stock(stock_code: str, db):
    """计算股票的技术指标"""
    
    prices = db.query(DailyPrice).filter(
        DailyPrice.stock_code == stock_code
    ).order_by(DailyPrice.trade_date).all()
    
    if len(prices) < 20:
        return
    
    df = pd.DataFrame([{
        'trade_date': p.trade_date,
        'open_price': float(p.open_price) if p.open_price else None,
        'high_price': float(p.high_price) if p.high_price else None,
        'low_price': float(p.low_price) if p.low_price else None,
        'close_price': float(p.close_price) if p.close_price else None,
        'volume': p.volume,
    } for p in prices])
    
    calculator = TechnicalCalculator()
    df = calculator.calculate_all(df)
    
    # 保存指标
    save_indicators_to_db(stock_code, df, db)


def display_analysis(stock_code: str, days: int, db):
    """显示分析报告"""
    
    st.divider()
    st.header(f"{stock_code} 分析报告")
    
    # 获取数据
    prices = db.query(DailyPrice).filter(
        DailyPrice.stock_code == stock_code
    ).order_by(DailyPrice.trade_date.desc()).limit(days).all()
    
    if not prices:
        st.warning("无数据可显示")
        return
    
    df = pd.DataFrame([{
        'trade_date': p.trade_date,
        'open_price': float(p.open_price) if p.open_price else None,
        'high_price': float(p.high_price) if p.high_price else None,
        'low_price': float(p.low_price) if p.low_price else None,
        'close_price': float(p.close_price) if p.close_price else None,
        'volume': p.volume,
        'change_pct': float(p.change_pct) if p.change_pct else None,
    } for p in reversed(prices)])
    
    latest = df.iloc[-1]
    
    # 基本信息卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="最新价",
            value=f"{latest['close_price']:.3f}",
            delta=f"{latest['change_pct']:.2f}%" if latest['change_pct'] else None
        )
    
    with col2:
        prev_close = df.iloc[-2]['close_price'] if len(df) > 1 else latest['close_price']
        change = latest['close_price'] - prev_close
        st.metric(label="涨跌额", value=f"{change:+.3f}")
    
    with col3:
        st.metric(
            label="成交量",
            value=f"{latest['volume']/10000:.0f}万" if latest['volume'] else "-"
        )
    
    with col4:
        high_52w = df['high_price'].max()
        low_52w = df['low_price'].min()
        st.metric(label="区间高低", value=f"{low_52w:.3f} - {high_52w:.3f}")
    
    # K线图
    st.subheader("K线走势")
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )
    
    fig.add_trace(
        go.Candlestick(
            x=df['trade_date'],
            open=df['open_price'],
            high=df['high_price'],
            low=df['low_price'],
            close=df['close_price'],
            name='K线'
        ),
        row=1, col=1
    )
    
    colors = ['red' if df.iloc[i]['close_price'] >= df.iloc[i]['open_price'] 
              else 'green' for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(
            x=df['trade_date'],
            y=df['volume'],
            marker_color=colors,
            name='成交量'
        ),
        row=2, col=1
    )
    
    fig.update_layout(height=500, showlegend=False, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # 技术指标 - 使用expander节省空间
    with st.expander("🔢 技术指标详情", expanded=True):
        indicators = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_code == stock_code
        ).order_by(TechnicalIndicator.trade_date.desc()).first()
        
        if indicators:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**均线系统**")
                st.markdown(f"MA5: {indicators.ma5:.3f}" if indicators.ma5 else "MA5: -")
                st.markdown(f"MA20: {indicators.ma20:.3f}" if indicators.ma20 else "MA20: -")
                st.markdown(f"MA60: {indicators.ma60:.3f}" if indicators.ma60 else "MA60: -")
            
            with col2:
                st.markdown("**MACD**")
                st.markdown(f"DIF: {indicators.macd_dif:.4f}" if indicators.macd_dif else "DIF: -")
                st.markdown(f"DEA: {indicators.macd_dea:.4f}" if indicators.macd_dea else "DEA: -")
            
            with col3:
                st.markdown("**RSI/KDJ**")
                st.markdown(f"RSI12: {indicators.rsi12:.2f}" if indicators.rsi12 else "RSI12: -")
                st.markdown(f"K: {indicators.k_value:.2f}" if indicators.k_value else "K: -")
                st.markdown(f"D: {indicators.d_value:.2f}" if indicators.d_value else "D: -")
    
    # 趋势分析
    with st.expander("🎯 趋势分析", expanded=True):
        try:
            analyzer = TrendAnalyzer(df)
            result = analyzer.analyze()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                trend_emoji = "🟢" if result.direction.value == "UPTREND" else "🔴" if result.direction.value == "DOWNTREND" else "⚪"
                st.markdown(f"**趋势方向:** {trend_emoji} {result.direction.value}")
            
            with col2:
                strength_emoji = "💪" if result.strength.value == "STRONG" else "👍" if result.strength.value == "MODERATE" else "👋"
                st.markdown(f"**趋势强度:** {strength_emoji} {result.strength.value}")
            
            with col3:
                st.markdown(f"**持续天数:** {result.trend_days}天")
            
            st.info(result.description)
            
            # 支撑阻力
            if result.support_levels and result.resistance_levels:
                cols = st.columns(2)
                with cols[0]:
                    st.markdown("**支撑位:** " + ", ".join([f"{s:.3f}" for s in result.support_levels[:3]]))
                with cols[1]:
                    st.markdown("**阻力位:** " + ", ".join([f"{r:.3f}" for r in result.resistance_levels[:3]]))
            
        except Exception as e:
            st.warning(f"趋势分析暂不可用: {e}")
    
    # 风险指标
    with st.expander("⚠️ 风险指标", expanded=True):
        try:
            returns = df['close_price'].pct_change().dropna()
            if len(returns) > 30:
                metrics = RiskMetrics(returns)
                result = metrics.calculate_all()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("年化收益率", f"{result.annualized_return*100:.1f}%")
                with col2:
                    st.metric("年化波动率", f"{result.annualized_volatility*100:.1f}%")
                with col3:
                    st.metric("最大回撤", f"{result.max_drawdown*100:.1f}%")
                with col4:
                    st.metric("夏普比率", f"{result.sharpe_ratio:.2f}")
        except Exception as e:
            st.warning(f"风险指标暂不可用: {e}")
    
    # 数据下载
    st.divider()
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="下载数据 (CSV)",
        data=csv,
        file_name=f"{stock_code}_data.csv",
        mime="text/csv"
    )


# 执行页面
show()
