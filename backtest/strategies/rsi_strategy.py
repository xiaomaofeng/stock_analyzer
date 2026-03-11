# -*- coding: utf-8 -*-
"""RSI策略"""
import pandas as pd
import numpy as np
from typing import List
from ..engine import Order, OrderSide


class RSIStrategy:
    """RSI超买超卖策略"""
    
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.name = f"RSI_{period}"
        self.current_idx = 0
    
    def __call__(self, day_data: pd.DataFrame, portfolio) -> List[Order]:
        """使策略可调用"""
        self.current_idx += 1
        return self.on_data(day_data, self.current_idx, portfolio)
    
    def calculate_rsi(self, prices: pd.Series) -> float:
        """计算RSI"""
        if len(prices) < self.period + 1:
            return 50.0
        
        deltas = prices.diff().dropna()
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)
        
        avg_gain = gains.tail(self.period).mean()
        avg_loss = losses.tail(self.period).mean()
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def on_data(self, df: pd.DataFrame, current_idx: int, portfolio) -> List[Order]:
        """生成交易信号"""
        if current_idx < self.period:
            return []
        
        orders = []
        current = df.iloc[current_idx]
        stock_code = current.get('stock_code', 'unknown')
        close_price = current['close_price']
        
        # 计算RSI
        prices = df['close_price'].iloc[:current_idx+1]
        rsi = self.calculate_rsi(prices)
        
        # 获取持仓
        position = portfolio.get_position(stock_code)
        
        # 超卖买入
        if rsi < self.oversold and position.quantity == 0:
            quantity = int(portfolio.cash * 0.3 / close_price / 100) * 100
            if quantity > 0:
                orders.append(Order(
                    stock_code=stock_code,
                    side=OrderSide.BUY,
                    quantity=quantity
                ))
        
        # 超买卖出
        elif rsi > self.overbought and position.quantity > 0:
            orders.append(Order(
                stock_code=stock_code,
                side=OrderSide.SELL,
                quantity=position.quantity
            ))
        
        return orders
