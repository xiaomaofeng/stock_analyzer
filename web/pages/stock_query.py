"""
股票查询页面 - 输入代码自动获取数据并分析
"""
import sys
from pathlib import Path
import os

# ============ 关键：确保项目根目录正确设置 ============
# 计算项目根目录（当前文件是 web/pages/stock_query.py，所以向上两级）
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# 强制切换到项目根目录，确保数据库路径正确
os.chdir(PROJECT_ROOT)

# 确保项目根目录在Python路径最前面
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ============ 关键：重新加载配置，避免缓存问题 ============
# 清除可能存在的缓存模块
modules_to_remove = [k for k in sys.modules.keys() if k.startswith('config') or k.startswith('database')]
for m in modules_to_remove:
    del sys.modules[m]

# 重新导入
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
    
    # 显示当前配置（调试用）
    with st.expander("系统信息（调试用）"):
        settings = get_settings()
        st.code(f"工作目录: {os.getcwd()}\nPROJECT_ROOT: {settings.PROJECT_ROOT}\nDATABASE_URL: {settings.DATABASE_URL}")
        # 测试数据库连接
        try:
            db = get_session_factory()()
            count = db.query(Stock).count()
            st.success(f"数据库连接正常，已有 {count} 只股票")
            db.close()
        except Exception as e:
            st.error(f"数据库连接失败: {e}")
    
    st.markdown("""
    输入股票代码，系统自动：
    1. 从AKShare获取历史数据
    2. 存入本地数据库
    3. 计算技术指标
    4. 生成分析报告
    """)
    
    # 查询输入区域
    col1, col2, col3 = st.columns([2, 1, 1])
    
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
        query_btn = st.button("🚀 查询并分析", type="primary", use_container_width=True)
    
    if query_btn and stock_code:
        try:
            with st.spinner(f"正在获取 {stock_code} 数据并分析..."):
                process_stock(stock_code, days)
        except Exception as e:
            st.error(f"❌ 处理失败: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


def process_stock(stock_code: str, days: int):
    """处理股票查询、存储和分析"""
    
    # 确保目录存在
    settings = get_settings()
    settings.ensure_directories()
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 步骤1: 检查数据库中是否已有数据
        existing_count = db.query(DailyPrice).filter(
            DailyPrice.stock_code == stock_code
        ).count()
        
        if existing_count == 0:
            # 步骤2: 从AKShare获取数据
            st.info(f"📥 数据库中没有 {stock_code}，正在从AKShare获取...")
            
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
                st.error(f"❌ 无法获取 {stock_code} 的数据，请检查代码是否正确")
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
                    amount=float(row['amount']) if pd.notna(row.get('amount')) else None,
                    change_pct=float(row['change_pct']) if pd.notna(row.get('change_pct')) else None,
                    turnover_rate=float(row['turnover_rate']) if pd.notna(row.get('turnover_rate')) else None,
                )
                db.merge(daily_price)
                progress_bar.progress(min((idx + 1) / len(df), 1.0))
            
            db.commit()
            progress_bar.empty()
            st.success(f"✅ 成功导入 {len(df)} 条历史数据")
            
            # 步骤3: 计算技术指标
            st.info("🔢 正在计算技术指标...")
            calculate_indicators_for_stock(stock_code, db)
            st.success("✅ 技术指标计算完成")
        else:
            st.info(f"📦 数据库中已有 {stock_code} 的 {existing_count} 条数据，直接分析")
        
        # 步骤4: 显示分析报告
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
    st.header(f"📊 {stock_code} 分析报告")
    
    # 获取数据
    prices = db.query(DailyPrice).filter(
        DailyPrice.stock_code == stock_code
    ).order_by(DailyPrice.trade_date.desc()).limit(days).all()
    
    if not prices:
        st.warning("无数据可显示")
        return
    
    df = pd.DataFrame([{
        'trade_date': p.trade_date,
        'open_price': p.open_price,
        'high_price': p.high_price,
        'low_price': p.low_price,
        'close_price': p.close_price,
        'volume': p.volume,
        'change_pct': p.change_pct,
    } for p in reversed(prices)])
    
    latest = df.iloc[-1]
    
    # 基本信息卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="最新价",
            value=f"¥{latest['close_price']:.3f}",
            delta=f"{latest['change_pct']:.2f}%" if latest['change_pct'] else None
        )
    
    with col2:
        prev_close = df.iloc[-2]['close_price'] if len(df) > 1 else latest['close_price']
        change = latest['close_price'] - prev_close
        st.metric(
            label="涨跌额",
            value=f"{change:+.3f}",
        )
    
    with col3:
        st.metric(
            label="成交量",
            value=f"{latest['volume']/10000:.0f}万" if latest['volume'] else "-"
        )
    
    with col4:
        high_52w = df['high_price'].max()
        low_52w = df['low_price'].min()
        st.metric(
            label="区间高低",
            value=f"{low_52w:.3f} - {high_52w:.3f}"
        )
    
    # K线图
    st.subheader("📈 K线走势")
    
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
    
    # 技术指标
    st.subheader("🔢 技术指标")
    
    # 从数据库获取指标
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
    st.subheader("🎯 趋势分析")
    
    try:
        analyzer = TrendAnalyzer(df)
        result = analyzer.analyze()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trend_color = "green" if result.direction.value == "UPTREND" else "red" if result.direction.value == "DOWNTREND" else "gray"
            st.markdown(f"**趋势方向:** :{trend_color}[{result.direction.value}]")
        
        with col2:
            st.markdown(f"**趋势强度:** {result.strength.value}")
        
        with col3:
            st.markdown(f"**持续天数:** {result.trend_days}天")
        
        st.info(result.description)
        
        # 交易信号
        signals = analyzer.get_trading_signals()
        if 'overall' in signals:
            score = signals['overall']['score']
            signal = signals['overall']['signal']
            
            if signal in ['strong_buy', 'buy']:
                st.success(f"🟢 综合评分: {score}/100 - 建议买入")
            elif signal in ['strong_sell', 'sell']:
                st.error(f"🔴 综合评分: {score}/100 - 建议卖出")
            else:
                st.info(f"🟡 综合评分: {score}/100 - 观望")
    
    except Exception as e:
        st.warning(f"趋势分析暂不可用: {e}")
    
    # 风险指标
    st.subheader("⚠️ 风险指标")
    
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
        label="📥 下载数据 (CSV)",
        data=csv,
        file_name=f"{stock_code}_data.csv",
        mime="text/csv"
    )
