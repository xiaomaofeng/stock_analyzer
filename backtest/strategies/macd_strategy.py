# -*- coding: utf-8 -*-
"""MACD策略 - 完整版"""
import pandas as pd
import numpy as np
from typing import List
from ..engine import Order, OrderSide


class MACDStrategy:
    """MACD金叉死叉策略 - 使用完整MACD计算"""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.name = f"MACD_{fast}_{slow}"
        self.data_history = []
        # 保存历史DIF用于计算DEA
        self.dif_history = []
    
    def __call__(self, day_data: pd.DataFrame, portfolio) -> List[Order]:
        """使策略可调用"""
        if not day_data.empty:
            self.data_history.append(day_data.iloc[0])
        return self.on_data(portfolio)
    
    def calculate_macd(self, prices: pd.Series) -> tuple:
        """
        计算完整MACD
        
        DIF = EMA(close, fast) - EMA(close, slow)
        DEA = EMA(DIF, signal)
        MACD = 2 * (DIF - DEA)
        """
        if len(prices) < self.slow:
            return 0, 0, 0
        
        # 计算EMA - 使用标准EMA公式
        ema_fast = prices.ewm(span=self.fast, adjust=False).mean().iloc[-1]
        ema_slow = prices.ewm(span=self.slow, adjust=False).mean().iloc[-1]
        
        # DIF (快线)
        dif = ema_fast - ema_slow
        
        # 保存DIF历史
        self.dif_history.append(dif)
        
        # DEA (慢线) = DIF的EMA
        if len(self.dif_history) < self.signal:
            dea = dif  # 初始阶段使用DIF本身
        else:
            # 使用历史DIF计算EMA
            dif_series = pd.Series(self.dif_history)
            dea = dif_series.ewm(span=self.signal, adjust=False).mean().iloc[-1]
        
        # MACD柱状图
        macd_bar = 2 * (dif - dea)
        
        return dif, dea, macd_bar
    
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
        
        # 计算当前MACD
        prices = df['close_price']
        current_dif, current_dea, _ = self.calculate_macd(prices)
        
        # 计算前一日MACD (需要恢复历史DIF状态)
        prev_dif_history = self.dif_history[:-1]
        prev_dif, prev_dea = 0, 0
        if len(prev_dif_history) >= 1:
            if len(prev_dif_history) < self.signal:
                prev_dif = prev_dif_history[-1]
                prev_dea = prev_dif
            else:
                dif_series = pd.Series(prev_dif_history)
                prev_dea = dif_series.ewm(span=self.signal, adjust=False).mean().iloc[-1]
                prev_dif = prev_dif_history[-1]
        
        # 获取持仓
        position = portfolio.get_position(stock_code)
        
        orders = []
        
        # 金叉买入: DIF上穿DEA
        if prev_dif <= prev_dea and current_dif > current_dea and position.quantity == 0:
            quantity = int(portfolio.cash * 0.3 / close_price / 100) * 100
            if quantity > 0:
                orders.append(Order(
                    stock_code=stock_code,
                    side=OrderSide.BUY,
                    quantity=quantity
                ))
        
        # 死叉卖出: DIF下穿DEA
        elif prev_dif >= prev_dea and current_dif < current_dea and position.quantity > 0:
            orders.append(Order(
                stock_code=stock_code,
                side=OrderSide.SELL,
                quantity=position.quantity
            ))
        
        return orders
