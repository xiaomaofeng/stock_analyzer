"""个股分析页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator
from analysis import TrendAnalyzer
from analysis.risk_metrics import RiskMetrics


def show():
    """显示个股分析页面"""
    st.title("📈 个股分析")
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 股票选择
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 获取所有股票
            stocks = db.query(Stock).order_by(Stock.stock_code).all()
            stock_options = [f"{s.stock_code} - {s.stock_name}" for s in stocks]
            
            selected = st.selectbox(
                "选择股票",
                options=stock_options,
                index=0 if stock_options else None
            )
            
            if selected:
                stock_code = selected.split(" - ")[0]
                stock_name = selected.split(" - ")[1]
            else:
                st.warning("请先导入股票数据")
                return
        
        with col2:
            days = st.selectbox(
                "时间范围",
                options=[60, 120, 252, 500],
                format_func=lambda x: f"{x}天"
            )
        
        # 加载数据
        prices = db.query(DailyPrice).filter(
            DailyPrice.stock_code == stock_code
        ).order_by(DailyPrice.trade_date.desc()).limit(days).all()
        
        if not prices:
            st.warning(f"未找到 {stock_code} 的数据")
            return
        
        # 转换为DataFrame
        df = pd.DataFrame([{
            'trade_date': p.trade_date,
            'open_price': p.open_price,
            'high_price': p.high_price,
            'low_price': p.low_price,
            'close_price': p.close_price,
            'volume': p.volume,
            'turnover_rate': p.turnover_rate,
            'change_pct': p.change_pct,
        } for p in reversed(prices)])
        
        # 显示基本信息
        st.subheader(f"{stock_name} ({stock_code})")
        
        # 最新数据
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        cols = st.columns(6)
        with cols[0]:
            st.metric("最新价", f"{latest['close_price']:.2f}", 
                     f"{latest['change_pct']:.2f}%")
        with cols[1]:
            st.metric("涨跌幅", f"{latest['change_pct']:+.2f}%")
        with cols[2]:
            st.metric("成交量", f"{latest['volume']/10000:.0f}万")
        with cols[3]:
            st.metric("换手率", f"{latest['turnover_rate']:.2f}%")
        with cols[4]:
            high_52w = df['high_price'].max()
            st.metric("52周最高", f"{high_52w:.2f}")
        with cols[5]:
            low_52w = df['low_price'].min()
            st.metric("52周最低", f"{low_52w:.2f}")
        
        # K线图
        st.subheader("K线图")
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3]
        )
        
        # 蜡烛图
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
        
        # 成交量
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
        
        fig.update_layout(
            height=600,
            showlegend=False,
            xaxis_rangeslider_visible=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 分析标签页
        tab1, tab2, tab3 = st.tabs(["趋势分析", "技术指标", "风险指标"])
        
        with tab1:
            show_trend_analysis(df)
        
        with tab2:
            show_technical_indicators(df, stock_code, db)
        
        with tab3:
            show_risk_metrics(df)
            
    except Exception as e:
        st.error(f"加载数据失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def show_trend_analysis(df: pd.DataFrame):
    """显示趋势分析"""
    try:
        analyzer = TrendAnalyzer(df)
        result = analyzer.analyze()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trend_color = "green" if result.direction.value == "UPTREND" else "red" if result.direction.value == "DOWNTREND" else "gray"
            st.markdown(f"**趋势方向:** :{trend_color}[{result.direction.value}]")
        
        with col2:
            strength_color = "green" if result.strength.value == "STRONG" else "orange" if result.strength.value == "MODERATE" else "gray"
            st.markdown(f"**趋势强度:** :{strength_color}[{result.strength.value}]")
        
        with col3:
            st.markdown(f"**持续天数:** {result.trend_days}天")
        
        st.info(result.description)
        
        # 支撑阻力
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**支撑位**")
            for i, level in enumerate(result.support_levels[:3], 1):
                st.markdown(f"{i}. {level:.2f}")
        
        with col2:
            st.markdown("**阻力位**")
            for i, level in enumerate(result.resistance_levels[:3], 1):
                st.markdown(f"{i}. {level:.2f}")
        
        # 形态检测
        patterns = analyzer.detect_patterns()
        if patterns:
            st.markdown("**形态检测**")
            for p in patterns:
                icon = "📈" if p['signal'] == 'bullish' else "📉" if p['signal'] == 'bearish' else "➖"
                st.markdown(f"{icon} **{p['name']}**: {p['description']}")
        
        # 交易信号
        signals = analyzer.get_trading_signals()
        if 'overall' in signals:
            st.markdown("**交易信号**")
            score = signals['overall']['score']
            signal = signals['overall']['signal']
            
            if signal in ['strong_buy', 'buy']:
                st.success(f"综合评分: {score}/100 - 建议买入")
            elif signal in ['strong_sell', 'sell']:
                st.error(f"综合评分: {score}/100 - 建议卖出")
            else:
                st.info(f"综合评分: {score}/100 - 观望")
                
    except Exception as e:
        st.error(f"趋势分析失败: {e}")


def show_technical_indicators(df: pd.DataFrame, stock_code: str, db):
    """显示技术指标"""
    try:
        # 从数据库查询已计算的指标
        from sqlalchemy import desc
        indicators = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_code == stock_code
        ).order_by(desc(TechnicalIndicator.trade_date)).limit(1).first()
        
        if indicators:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**均线系统**")
                st.markdown(f"MA5: {indicators.ma5:.2f}")
                st.markdown(f"MA10: {indicators.ma10:.2f}")
                st.markdown(f"MA20: {indicators.ma20:.2f}")
                st.markdown(f"MA60: {indicators.ma60:.2f}")
            
            with col2:
                st.markdown("**MACD**")
                st.markdown(f"DIF: {indicators.macd_dif:.4f}")
                st.markdown(f"DEA: {indicators.macd_dea:.4f}")
                st.markdown(f"BAR: {indicators.macd_bar:.4f}")
                
                st.markdown("**KDJ**")
                st.markdown(f"K: {indicators.k_value:.2f}")
                st.markdown(f"D: {indicators.d_value:.2f}")
            
            with col3:
                st.markdown("**RSI**")
                st.markdown(f"RSI6: {indicators.rsi6:.2f}")
                st.markdown(f"RSI12: {indicators.rsi12:.2f}")
                st.markdown(f"RSI24: {indicators.rsi24:.2f}")
                
                st.markdown("**布林带**")
                st.markdown(f"上轨: {indicators.boll_upper:.2f}")
                st.markdown(f"中轨: {indicators.boll_mid:.2f}")
                st.markdown(f"下轨: {indicators.boll_lower:.2f}")
        else:
            st.info("暂无技术指标数据，请先运行指标计算脚本")
            
    except Exception as e:
        st.error(f"技术指标显示失败: {e}")


def show_risk_metrics(df: pd.DataFrame):
    """显示风险指标"""
    try:
        returns = df['close_price'].pct_change().dropna()
        
        if len(returns) < 30:
            st.warning("数据不足，无法计算风险指标")
            return
        
        metrics = RiskMetrics(returns)
        result = metrics.calculate_all()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**收益指标**")
            st.markdown(f"总收益率: {result.total_return*100:.2f}%")
            st.markdown(f"年化收益率: {result.annualized_return*100:.2f}%")
        
        with col2:
            st.markdown("**风险指标**")
            st.markdown(f"年化波动率: {result.annualized_volatility*100:.2f}%")
            st.markdown(f"最大回撤: {result.max_drawdown*100:.2f}%")
            st.markdown(f"当前回撤: {result.current_drawdown*100:.2f}%")
        
        with col3:
            st.markdown("**风险调整收益**")
            st.markdown(f"夏普比率: {result.sharpe_ratio:.2f}")
            st.markdown(f"索提诺比率: {result.sortino_ratio:.2f}")
            st.markdown(f"卡尔玛比率: {result.calmar_ratio:.2f}")
        
        st.markdown("**尾部风险**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"VaR (95%): {result.var_95*100:.2f}%")
        with col2:
            st.markdown(f"VaR (99%): {result.var_99*100:.2f}%")
        with col3:
            st.markdown(f"CVaR (95%): {result.cvar_95*100:.2f}%")
        with col4:
            st.markdown(f"偏度: {result.skewness:.2f}")
            
    except Exception as e:
        st.error(f"风险指标计算失败: {e}")
