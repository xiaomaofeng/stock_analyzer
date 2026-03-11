# -*- coding: utf-8 -*-
"""回测页面 - 策略回测与绩效分析"""
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

from config import get_session_factory
from database.models import Stock, DailyPrice
from backtest.engine import BacktestEngine, BacktestConfig, Order, OrderSide


def show():
    """显示回测页面"""
    st.title("🔄 策略回测")
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 参数设置
        st.sidebar.header("回测参数")
        
        # 选择股票
        stocks = db.query(Stock).order_by(Stock.stock_code).all()
        stock_options = [f"{s.stock_code} - {s.stock_name}" for s in stocks]
        
        selected = st.sidebar.selectbox(
            "选择股票",
            options=stock_options,
            index=0 if stock_options else None
        )
        
        if not selected:
            st.warning("请先导入股票数据")
            return
        
        stock_code = selected.split(" - ")[0]
        
        # 时间范围
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        date_range = st.sidebar.date_input(
            "回测时间范围",
            value=(start_date, end_date),
            max_value=end_date
        )
        
        # 处理日期范围
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
        
        # 初始资金
        initial_capital = st.sidebar.number_input(
            "初始资金",
            min_value=10000,
            max_value=10000000,
            value=100000,
            step=10000
        )
        
        # 手续费
        commission = st.sidebar.slider(
            "手续费率",
            min_value=0.0001,
            max_value=0.005,
            value=0.0003,
            step=0.0001,
            format="%.4f"
        )
        
        # 策略选择
        st.sidebar.header("策略选择")
        strategy = st.sidebar.selectbox(
            "选择策略",
            options=["均线交叉", "RSI超买超卖", "MACD金叉死叉"]
        )
        
        # 加载数据
        prices = db.query(DailyPrice).filter(
            DailyPrice.stock_code == stock_code,
            DailyPrice.trade_date >= start_date,
            DailyPrice.trade_date <= end_date
        ).order_by(DailyPrice.trade_date).all()
        
        if len(prices) < 60:
            st.warning("数据不足，请扩大时间范围")
            return
        
        # 转换为DataFrame并计算指标
        df = pd.DataFrame([{
            'trade_date': p.trade_date,
            'stock_code': p.stock_code,
            'open_price': p.open_price,
            'high_price': p.high_price,
            'low_price': p.low_price,
            'close_price': p.close_price,
            'volume': p.volume,
        } for p in prices])
        
        # 计算均线
        df['ma5'] = df['close_price'].rolling(window=5).mean()
        df['ma20'] = df['close_price'].rolling(window=20).mean()
        df['ma60'] = df['close_price'].rolling(window=60).mean()
        
        # 计算MACD
        exp1 = df['close_price'].ewm(span=12).mean()
        exp2 = df['close_price'].ewm(span=26).mean()
        df['macd_dif'] = exp1 - exp2
        df['macd_dea'] = df['macd_dif'].ewm(span=9).mean()
        
        # 计算RSI
        delta = df['close_price'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 执行回测
        if st.sidebar.button("开始回测", type="primary"):
            with st.spinner("回测进行中..."):
                # 创建回测引擎
                config = BacktestConfig(
                    initial_capital=initial_capital,
                    commission_rate=commission
                )
                engine = BacktestEngine(config)
                
                # 设置策略
                if strategy == "均线交叉":
                    strategy_func = create_ma_strategy()
                elif strategy == "RSI超买超卖":
                    strategy_func = create_rsi_strategy()
                else:
                    strategy_func = create_macd_strategy()
                
                engine.set_strategy(strategy_func)
                engine.load_data(df)
                
                # 运行回测
                results = engine.run()
                
                # 显示结果
                display_backtest_results(results, engine)
        else:
            # 显示数据预览
            st.subheader("数据预览")
            st.dataframe(df.tail(10), use_container_width=True)
            
            # 显示价格走势
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['trade_date'],
                y=df['close_price'],
                mode='lines',
                name='收盘价'
            ))
            fig.add_trace(go.Scatter(
                x=df['trade_date'],
                y=df['ma5'],
                mode='lines',
                name='MA5',
                line=dict(dash='dash')
            ))
            fig.add_trace(go.Scatter(
                x=df['trade_date'],
                y=df['ma20'],
                mode='lines',
                name='MA20',
                line=dict(dash='dash')
            ))
            fig.update_layout(
                title=f"{stock_code} 价格走势",
                xaxis_title="日期",
                yaxis_title="价格",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.error(f"回测失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def create_ma_strategy():
    """创建均线策略"""
    def strategy(day_data, portfolio):
        orders = []
        for _, row in day_data.iterrows():
            if pd.isna(row['ma5']) or pd.isna(row['ma20']):
                continue
            
            stock_code = row['stock_code']
            close = row['close_price']
            ma5 = row['ma5']
            ma20 = row['ma20']
            
            position = portfolio.get_position(stock_code)
            
            # 金叉买入
            if close > ma5 > ma20 and position.quantity == 0:
                quantity = int(portfolio.cash * 0.3 / close / 100) * 100
                if quantity > 0:
                    orders.append(Order(
                        stock_code=stock_code,
                        side=OrderSide.BUY,
                        quantity=quantity
                    ))
            
            # 死叉卖出
            elif close < ma5 < ma20 and position.quantity > 0:
                orders.append(Order(
                    stock_code=stock_code,
                    side=OrderSide.SELL,
                    quantity=position.quantity
                ))
        
        return orders
    
    return strategy


def create_rsi_strategy():
    """创建RSI策略"""
    def strategy(day_data, portfolio):
        orders = []
        for _, row in day_data.iterrows():
            if pd.isna(row['rsi']):
                continue
            
            stock_code = row['stock_code']
            close = row['close_price']
            rsi = row['rsi']
            
            position = portfolio.get_position(stock_code)
            
            # RSI < 30 超卖买入
            if rsi < 30 and position.quantity == 0:
                quantity = int(portfolio.cash * 0.3 / close / 100) * 100
                if quantity > 0:
                    orders.append(Order(
                        stock_code=stock_code,
                        side=OrderSide.BUY,
                        quantity=quantity
                    ))
            
            # RSI > 70 超买卖出
            elif rsi > 70 and position.quantity > 0:
                orders.append(Order(
                    stock_code=stock_code,
                    side=OrderSide.SELL,
                    quantity=position.quantity
                ))
        
        return orders
    
    return strategy


def create_macd_strategy():
    """创建MACD策略"""
    def strategy(day_data, portfolio):
        orders = []
        for _, row in day_data.iterrows():
            if pd.isna(row['macd_dif']) or pd.isna(row['macd_dea']):
                continue
            
            stock_code = row['stock_code']
            close = row['close_price']
            dif = row['macd_dif']
            dea = row['macd_dea']
            
            position = portfolio.get_position(stock_code)
            
            # MACD金叉买入
            if dif > dea and position.quantity == 0:
                quantity = int(portfolio.cash * 0.3 / close / 100) * 100
                if quantity > 0:
                    orders.append(Order(
                        stock_code=stock_code,
                        side=OrderSide.BUY,
                        quantity=quantity
                    ))
            
            # MACD死叉卖出
            elif dif < dea and position.quantity > 0:
                orders.append(Order(
                    stock_code=stock_code,
                    side=OrderSide.SELL,
                    quantity=position.quantity
                ))
        
        return orders
    
    return strategy


def display_backtest_results(results: dict, engine):
    """显示回测结果"""
    if not results:
        st.error("回测失败，无结果")
        return
    
    st.success("回测完成！")
    
    # 指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "总收益率",
            f"{results['total_return']*100:.2f}%"
        )
    
    with col2:
        st.metric(
            "年化收益率",
            f"{results['annualized_return']*100:.2f}%"
        )
    
    with col3:
        st.metric(
            "最大回撤",
            f"{results['max_drawdown']*100:.2f}%"
        )
    
    with col4:
        st.metric(
            "夏普比率",
            f"{results['sharpe_ratio']:.2f}"
        )
    
    # 净值曲线
    st.subheader("净值曲线")
    
    daily_values = pd.DataFrame(results['daily_values'])
    daily_values['date'] = pd.to_datetime(daily_values['date'])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_values['date'],
        y=daily_values['total_value'],
        mode='lines',
        name='总资产'
    ))
    fig.update_layout(
        xaxis_title="日期",
        yaxis_title="资产价值",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 回撤曲线
    st.subheader("回撤曲线")
    
    daily_values['peak'] = daily_values['total_value'].cummax()
    daily_values['drawdown'] = (daily_values['total_value'] - daily_values['peak']) / daily_values['peak'] * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_values['date'],
        y=daily_values['drawdown'],
        mode='lines',
        fill='tozeroy',
        name='回撤',
        line=dict(color='red')
    ))
    fig.update_layout(
        xaxis_title="日期",
        yaxis_title="回撤 (%)",
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 交易记录
    st.subheader("交易记录")
    
    if results['trades']:
        trades_df = pd.DataFrame(results['trades'])
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        trades_df = trades_df.sort_values('timestamp')
        st.dataframe(trades_df, use_container_width=True)
    else:
        st.info("无交易记录")
    
    # 详细报告
    st.subheader("详细报告")
    st.text(engine.get_report())


# 执行页面
show()
