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
    
    def calculate_macd(self, df: pd.DataFrame, current_idx: int) -> tuple:
        """计算MACD"""
        if current_idx < self.slow:
            return 0, 0, 0
        
        prices = df['close_price'].iloc[:current_idx+1]
        
        ema_fast = prices.ewm(span=self.fast, adjust=False).mean().iloc[-1]
        ema_slow = prices.ewm(span=self.slow, adjust=False).mean().iloc[-1]
        
        dif = ema_fast - ema_slow
        
        # 计算DEA（DIF的EMA）
        if current_idx < self.slow + self.signal:
            dea = dif
        else:
            dif_series = prices.ewm(span=self.fast, adjust=False).mean() - prices.ewm(span=self.slow, adjust=False).mean()
            dea = dif_series.ewm(span=self.signal, adjust=False).mean().iloc[-1]
        
        bar = (dif - dea) * 2
        
        return dif, dea, bar
    
    def on_data(self, df: pd.DataFrame, current_idx: int, portfolio) -> List[Order]:
        """生成交易信号"""
        if current_idx < self.slow + 1:
            return []
        
        orders = []
        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]
        stock_code = current.get('stock_code', 'unknown')
        close_price = current['close_price']
        
        # 计算当前和前一日的MACD
        current_dif, current_dea, _ = self.calculate_macd(df, current_idx)
        prev_dif, prev_dea, _ = self.calculate_macd(df, current_idx - 1)
        
        # 获取持仓
        position = portfolio.get_position(stock_code)
        
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
