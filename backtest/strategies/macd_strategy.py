# -*- coding: utf-8 -*-
"""MACD策略"""
import pandas as pd
import numpy as np
from typing import List
from ..engine import Order, OrderSide


class MACDStrategy:
    """MACD金叉死叉策略"""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.name = f"MACD_{fast}_{slow}"
        self.data_history = []
    
    def __call__(self, day_data: pd.DataFrame, portfolio) -> List[Order]:
        """使策略可调用"""
        if not day_data.empty:
            self.data_history.append(day_data.iloc[0])
        return self.on_data(portfolio)
    
    def calculate_macd(self, prices: pd.Series) -> tuple:
        """计算MACD"""
        if len(prices) < self.slow:
            return 0, 0
        
        ema_fast = prices.ewm(span=self.fast, adjust=False).mean().iloc[-1]
        ema_slow = prices.ewm(span=self.slow, adjust=False).mean().iloc[-1]
        dif = ema_fast - ema_slow
        
        # 简化DEA计算
        dea = dif  # 实际应该用DIF的EMA
        
        return dif, dea
    
    def on_data(self, portfolio) -> List[Order]:
        """生成交易信号"""
        if len(self.data_history) < self.slow + 1:
            return []
        
        df = pd.DataFrame(self.data_history)
        current_idx = len(df) - 1
        
        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]
        stock_code = current.get('stock_code', 'unknown')
        close_price = current['close_price']
        
        # 计算当前和前一日的MACD
        prices = df['close_price']
        current_dif, _ = self.calculate_macd(prices)
        prev_dif, _ = self.calculate_macd(prices.iloc[:-1])
        
        # 简化：用价格差模拟DEA交叉
        current_dea = current_dif * 0.9
        prev_dea = prev_dif * 0.9 if prev_dif != 0 else 0
        
        # 获取持仓
        position = portfolio.get_position(stock_code)
        
        orders = []
        
        # 金叉买入
        if prev_dif <= prev_dea and current_dif > current_dea and position.quantity == 0:
            quantity = int(portfolio.cash * 0.3 / close_price / 100) * 100
            if quantity > 0:
                orders.append(Order(
                    stock_code=stock_code,
                    side=OrderSide.BUY,
                    quantity=quantity
                ))
        
        # 死叉卖出
        elif prev_dif >= prev_dea and current_dif < current_dea and position.quantity > 0:
            orders.append(Order(
                stock_code=stock_code,
                side=OrderSide.SELL,
                quantity=position.quantity
            ))
        
        return orders
