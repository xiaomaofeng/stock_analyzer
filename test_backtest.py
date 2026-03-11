# -*- coding: utf-8 -*-
"""Backtest test"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_session_factory
from database.models import DailyPrice
from processors import TechnicalCalculator
from backtest.engine import BacktestEngine, BacktestConfig
from backtest.strategies import MAStrategy
import pandas as pd

print("Testing backtest...")

SessionLocal = get_session_factory()
db = SessionLocal()

try:
    prices = db.query(DailyPrice).filter(DailyPrice.stock_code == "159892").order_by(DailyPrice.trade_date).all()
    print(f"Data count: {len(prices)}")
    
    if len(prices) < 60:
        print("Not enough data")
        sys.exit(1)
    
    df = pd.DataFrame([{
        "stock_code": p.stock_code,
        "trade_date": p.trade_date,
        "open_price": float(p.open_price) if p.open_price else 0,
        "high_price": float(p.high_price) if p.high_price else 0,
        "low_price": float(p.low_price) if p.low_price else 0,
        "close_price": float(p.close_price) if p.close_price else 0,
        "volume": p.volume or 0,
    } for p in prices])
    
    calc = TechnicalCalculator()
    df = calc.calculate_all(df)
    
    config = BacktestConfig(initial_capital=100000, commission_rate=0.0003)
    engine = BacktestEngine(config)
    strategy = MAStrategy(5, 20)
    
    engine.set_strategy(strategy)
    engine.load_data(df)
    
    print("Running backtest...")
    results = engine.run()
    
    print(f"Total return: {results['total_return']*100:.2f}%")
    print(f"Annual return: {results['annualized_return']*100:.2f}%")
    print(f"Max drawdown: {results['max_drawdown']*100:.2f}%")
    print(f"Sharpe ratio: {results['sharpe_ratio']:.2f}")
    print(f"Trades: {len(results['trades'])}")
    print("Backtest OK!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
