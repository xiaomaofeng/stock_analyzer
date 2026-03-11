# -*- coding: utf-8 -*-
"""均线策略"""
import pandas as pd
from typing import List
from ..engine import Order, OrderSide


class MAStrategy:
    """均线交叉策略"""
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        self.short_period = short_period
        self.long_period = long_period
        self.name = f"MA{short_period}_{long_period}"
        self.data_history = []  # 存储历史数据
    
    def __call__(self, day_data: pd.DataFrame, portfolio) -> List[Order]:
        """使策略可调用"""
        # 添加当前数据到历史
        if not day_data.empty:
            self.data_history.append(day_data.iloc[0])
        
        return self.on_data(portfolio)
    
    def on_data(self, portfolio) -> List[Order]:
        """根据历史数据生成交易信号"""
        if len(self.data_history) < self.long_period + 1:
            return []
        
        # 构建DataFrame
        df = pd.DataFrame(self.data_history)
        current_idx = len(df) - 1
        
        orders = []
        
        # 获取当前和前一个数据点
        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]
        
        stock_code = current.get('stock_code', 'unknown')
        close_price = current['close_price']
        
        # 计算均线
        short_ma = df['close_price'].iloc[current_idx-self.short_period+1:current_idx+1].mean()
        long_ma = df['close_price'].iloc[current_idx-self.long_period+1:current_idx+1].mean()
        
        prev_short_ma = df['close_price'].iloc[current_idx-self.short_period:current_idx].mean()
        prev_long_ma = df['close_price'].iloc[current_idx-self.long_period:current_idx].mean()
        
        # 获取持仓
        position = portfolio.get_position(stock_code)
        
        # 金叉买入
        if prev_short_ma <= prev_long_ma and short_ma > long_ma and position.quantity == 0:
            quantity = int(portfolio.cash * 0.3 / close_price / 100) * 100
            if quantity > 0:
                orders.append(Order(
                    stock_code=stock_code,
                    side=OrderSide.BUY,
                    quantity=quantity
                ))
        
        # 死叉卖出
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma and position.quantity > 0:
            orders.append(Order(
                stock_code=stock_code,
                side=OrderSide.SELL,
                quantity=position.quantity
            ))
        
        return orders
