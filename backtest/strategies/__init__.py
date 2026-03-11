"""策略模块"""
from .strategy_base import (
    StrategyBase,
    MultiFactorStrategy,
    MeanReversionStrategy,
    TrendFollowingStrategy,
    ParameterOptimizer,
    SignalType,
    StrategySignal,
    create_strategy
)

__all__ = [
    'StrategyBase',
    'MultiFactorStrategy',
    'MeanReversionStrategy', 
    'TrendFollowingStrategy',
    'ParameterOptimizer',
    'SignalType',
    'StrategySignal',
    'create_strategy'
]
