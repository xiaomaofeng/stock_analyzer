"""回测引擎"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """订单"""
    stock_code: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    price: float = 0.0
    timestamp: datetime = None


@dataclass
class Trade:
    """成交记录"""
    stock_code: str
    side: OrderSide
    quantity: int
    price: float
    amount: float
    fee: float
    timestamp: datetime


@dataclass
class Position:
    """持仓"""
    stock_code: str
    quantity: int = 0
    avg_cost: float = 0.0
    market_value: float = 0.0
    
    def update(self, trade: Trade):
        """根据成交更新持仓"""
        if trade.side == OrderSide.BUY:
            total_cost = self.quantity * self.avg_cost + trade.quantity * trade.price
            self.quantity += trade.quantity
            self.avg_cost = total_cost / self.quantity if self.quantity > 0 else 0
        else:
            self.quantity -= trade.quantity
            if self.quantity == 0:
                self.avg_cost = 0
        
        self.market_value = self.quantity * trade.price


@dataclass
class Portfolio:
    """投资组合"""
    initial_capital: float = 1000000.0
    cash: float = 1000000.0
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """获取总资产价值"""
        positions_value = sum(
            pos.quantity * current_prices.get(code, 0) 
            for code, pos in self.positions.items()
        )
        return self.cash + positions_value
    
    def get_position(self, stock_code: str) -> Position:
        """获取持仓"""
        if stock_code not in self.positions:
            self.positions[stock_code] = Position(stock_code)
        return self.positions[stock_code]
    
    def execute_trade(self, trade: Trade):
        """执行交易"""
        if trade.side == OrderSide.BUY:
            self.cash -= trade.amount + trade.fee
        else:
            self.cash += trade.amount - trade.fee
        
        position = self.get_position(trade.stock_code)
        position.update(trade)
        self.trades.append(trade)


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0003
    slippage: float = 0.0001
    min_commission: float = 5.0


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.portfolio = Portfolio(
            initial_capital=self.config.initial_capital,
            cash=self.config.initial_capital
        )
        self.strategy = None
        self.data = None
        self.results = None
    
    def set_strategy(self, strategy: Callable):
        """设置交易策略"""
        self.strategy = strategy
    
    def load_data(self, data: pd.DataFrame):
        """
        加载历史数据
        
        Args:
            data: DataFrame 包含以下列:
                - trade_date: 交易日期
                - stock_code: 股票代码
                - open_price: 开盘价
                - high_price: 最高价
                - low_price: 最低价
                - close_price: 收盘价
                - volume: 成交量
        """
        self.data = data.copy()
        self.data = self.data.sort_values(['stock_code', 'trade_date'])
    
    def run(self, start_date: str = None, end_date: str = None) -> Dict:
        """
        执行回测
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
        
        Returns:
            回测结果
        """
        if self.strategy is None:
            raise ValueError("请先设置策略")
        
        if self.data is None or self.data.empty:
            raise ValueError("请先加载数据")
        
        # 过滤日期范围
        df = self.data.copy()
        if start_date:
            df = df[df['trade_date'] >= start_date]
        if end_date:
            df = df[df['trade_date'] <= end_date]
        
        # 获取所有交易日
        dates = df['trade_date'].unique()
        
        # 每日净值记录
        daily_values = []
        
        for date in dates:
            day_data = df[df['trade_date'] == date]
            
            # 构建当前价格字典
            current_prices = dict(zip(
                day_data['stock_code'],
                day_data['close_price']
            ))
            
            # 调用策略生成交易信号
            signals = self.strategy(day_data, self.portfolio)
            
            # 执行交易
            for signal in signals:
                self._execute_order(signal, current_prices, date)
            
            # 记录当日净值
            total_value = self.portfolio.get_total_value(current_prices)
            daily_values.append({
                'date': date,
                'total_value': total_value,
                'cash': self.portfolio.cash,
                'positions_value': total_value - self.portfolio.cash
            })
        
        # 计算回测结果
        self.results = self._calculate_results(daily_values)
        return self.results
    
    def _execute_order(self, order: Order, current_prices: Dict[str, float], date: datetime):
        """执行订单"""
        if order.stock_code not in current_prices:
            return
        
        price = current_prices[order.stock_code]
        
        # 考虑滑点
        if order.side == OrderSide.BUY:
            executed_price = price * (1 + self.config.slippage)
        else:
            executed_price = price * (1 - self.config.slippage)
        
        amount = executed_price * order.quantity
        
        # 计算手续费
        fee = max(amount * self.config.commission_rate, self.config.min_commission)
        
        # 创建成交记录
        trade = Trade(
            stock_code=order.stock_code,
            side=order.side,
            quantity=order.quantity,
            price=executed_price,
            amount=amount,
            fee=fee,
            timestamp=date
        )
        
        self.portfolio.execute_trade(trade)
    
    def _calculate_results(self, daily_values: List[Dict]) -> Dict:
        """计算回测结果"""
        if not daily_values:
            return {}
        
        df = pd.DataFrame(daily_values)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 计算收益率
        df['return'] = df['total_value'].pct_change()
        df['cumulative_return'] = (1 + df['return']).cumprod() - 1
        
        # 计算回撤
        df['peak'] = df['total_value'].cummax()
        df['drawdown'] = (df['total_value'] - df['peak']) / df['peak']
        
        # 统计指标
        total_return = df['cumulative_return'].iloc[-1]
        days = len(df)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        volatility = df['return'].std() * np.sqrt(252)
        max_drawdown = df['drawdown'].min()
        
        # 夏普比率 (假设无风险利率3%)
        sharpe_ratio = (annual_return - 0.03) / volatility if volatility > 0 else 0
        
        # 交易统计
        trades = self.portfolio.trades
        total_trades = len(trades)
        buy_trades = len([t for t in trades if t.side == OrderSide.BUY])
        sell_trades = len([t for t in trades if t.side == OrderSide.SELL])
        total_fees = sum(t.fee for t in trades)
        
        return {
            'total_return': total_return,
            'annualized_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'total_fees': total_fees,
            'final_value': df['total_value'].iloc[-1],
            'daily_values': df.to_dict('records'),
            'trades': [
                {
                    'stock_code': t.stock_code,
                    'side': t.side.value,
                    'quantity': t.quantity,
                    'price': t.price,
                    'amount': t.amount,
                    'fee': t.fee,
                    'timestamp': t.timestamp
                } for t in trades
            ]
        }
    
    def get_report(self) -> str:
        """获取回测报告"""
        if self.results is None:
            return "请先执行回测"
        
        r = self.results
        
        report = f"""
{'='*60}
回测报告
{'='*60}

【收益指标】
  总收益率: {r['total_return']*100:.2f}%
  年化收益率: {r['annualized_return']*100:.2f}%
  最终资产: {r['final_value']:,.2f}

【风险指标】
  年化波动率: {r['volatility']*100:.2f}%
  最大回撤: {r['max_drawdown']*100:.2f}%
  夏普比率: {r['sharpe_ratio']:.2f}

【交易统计】
  总交易次数: {r['total_trades']}
  买入次数: {r['buy_trades']}
  卖出次数: {r['sell_trades']}
  总手续费: {r['total_fees']:.2f}

{'='*60}
"""
        return report


# 示例策略
def simple_ma_strategy(day_data: pd.DataFrame, portfolio: Portfolio) -> List[Order]:
    """
    简单均线策略示例
    
    当价格上穿5日均线时买入，下穿时卖出
    """
    orders = []
    
    for _, row in day_data.iterrows():
        stock_code = row['stock_code']
        close = row['close_price']
        
        # 假设数据中有MA5
        if 'ma5' not in row:
            continue
        
        ma5 = row['ma5']
        position = portfolio.get_position(stock_code)
        
        # 买入信号：价格上穿MA5且没有持仓
        if close > ma5 and position.quantity == 0:
            # 买入100股
            orders.append(Order(
                stock_code=stock_code,
                side=OrderSide.BUY,
                quantity=100
            ))
        
        # 卖出信号：价格下穿MA5且有持仓
        elif close < ma5 and position.quantity > 0:
            # 卖出全部
            orders.append(Order(
                stock_code=stock_code,
                side=OrderSide.SELL,
                quantity=position.quantity
            ))
    
    return orders
