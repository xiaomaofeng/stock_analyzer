"""
策略基类和增强策略库

支持多因子组合策略、参数优化、信号评分
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """信号类型"""
    STRONG_BUY = 2
    BUY = 1
    HOLD = 0
    SELL = -1
    STRONG_SELL = -2


@dataclass
class StrategySignal:
    """策略信号"""
    stock_code: str
    signal: SignalType
    score: float  # 0-100
    confidence: float  # 置信度 0-1
    indicators: Dict[str, Any]  # 触发信号的指标详情
    reason: str  # 信号原因
    timestamp: Any


class StrategyBase(ABC):
    """策略基类"""
    
    def __init__(self, name: str, params: Dict = None):
        self.name = name
        self.params = params or {}
        self.signals_history = []
    
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """分析并生成信号"""
        pass
    
    @abstractmethod
    def calculate_score(self, df: pd.DataFrame) -> float:
        """计算信号评分 0-100"""
        pass
    
    def get_params_grid(self) -> Dict[str, List]:
        """获取参数优化网格"""
        return {}
    
    def set_params(self, params: Dict):
        """设置参数"""
        self.params.update(params)


class MultiFactorStrategy(StrategyBase):
    """
    多因子组合策略
    
    综合多个技术指标生成加权信号
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            # 指标权重
            'weight_trend': 0.25,      # 趋势指标权重
            'weight_momentum': 0.25,   # 动量指标权重
            'weight_volume': 0.25,     # 成交量指标权重
            'weight_sentiment': 0.25,  # 情绪指标权重
            # 阈值
            'buy_threshold': 60,
            'sell_threshold': 40,
            # 最小置信度
            'min_confidence': 0.6
        }
        if params:
            default_params.update(params)
        super().__init__("多因子策略", default_params)
    
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """分析并生成信号"""
        stock_code = df['stock_code'].iloc[-1] if 'stock_code' in df.columns else 'unknown'
        timestamp = df.index[-1] if isinstance(df.index, pd.DatetimeIndex) else df.iloc[-1].get('trade_date')
        
        # 计算各维度评分
        trend_score = self._calculate_trend_score(df)
        momentum_score = self._calculate_momentum_score(df)
        volume_score = self._calculate_volume_score(df)
        sentiment_score = self._calculate_sentiment_score(df)
        
        # 加权总分
        total_score = (
            trend_score * self.params['weight_trend'] +
            momentum_score * self.params['weight_momentum'] +
            volume_score * self.params['weight_volume'] +
            sentiment_score * self.params['weight_sentiment']
        )
        
        # 计算置信度（各维度一致性）
        scores = [trend_score, momentum_score, volume_score, sentiment_score]
        confidence = 1 - (np.std(scores) / 50)  # 标准差越小置信度越高
        confidence = max(0, min(1, confidence))
        
        # 生成信号
        if total_score >= self.params['buy_threshold'] and confidence >= self.params['min_confidence']:
            signal = SignalType.STRONG_BUY if total_score >= 80 else SignalType.BUY
        elif total_score <= self.params['sell_threshold'] and confidence >= self.params['min_confidence']:
            signal = SignalType.STRONG_SELL if total_score <= 20 else SignalType.SELL
        else:
            signal = SignalType.HOLD
        
        # 构建原因
        reasons = []
        if trend_score > 60:
            reasons.append(f"趋势向好({trend_score:.0f})")
        elif trend_score < 40:
            reasons.append(f"趋势走弱({trend_score:.0f})")
        
        if momentum_score > 60:
            reasons.append(f"动量强劲({momentum_score:.0f})")
        elif momentum_score < 40:
            reasons.append(f"动量不足({momentum_score:.0f})")
        
        if volume_score > 60:
            reasons.append(f"量能配合({volume_score:.0f})")
        
        if sentiment_score > 60:
            reasons.append(f"情绪乐观({sentiment_score:.0f})")
        elif sentiment_score < 40:
            reasons.append(f"情绪悲观({sentiment_score:.0f})")
        
        return StrategySignal(
            stock_code=stock_code,
            signal=signal,
            score=total_score,
            confidence=confidence,
            indicators={
                'trend': trend_score,
                'momentum': momentum_score,
                'volume': volume_score,
                'sentiment': sentiment_score
            },
            reason="; ".join(reasons) if reasons else "无明显信号",
            timestamp=timestamp
        )
    
    def calculate_score(self, df: pd.DataFrame) -> float:
        """计算总分"""
        signal = self.analyze(df)
        return signal.score
    
    def _calculate_trend_score(self, df: pd.DataFrame) -> float:
        """计算趋势维度评分 0-100"""
        score = 50
        latest = df.iloc[-1]
        
        # 均线系统
        if 'ma5' in df.columns and 'ma20' in df.columns:
            if latest['ma5'] > latest['ma20']:
                score += 15
                if 'ma60' in df.columns and latest['ma20'] > latest['ma60']:
                    score += 10
            else:
                score -= 15
        
        # MACD
        if 'macd_dif' in df.columns and 'macd_dea' in df.columns:
            if latest['macd_dif'] > latest['macd_dea']:
                score += 10
                if latest['macd_bar'] > 0:
                    score += 5
            else:
                score -= 10
        
        # DMI
        if '+di' in df.columns and '-di' in df.columns and 'adx' in df.columns:
            if latest['+di'] > latest['-di'] and latest['adx'] > 25:
                score += 10
            elif latest['-di'] > latest['+di'] and latest['adx'] > 25:
                score -= 10
        
        # SAR
        if 'sar' in df.columns:
            if latest['close_price'] > latest['sar']:
                score += 5
            else:
                score -= 5
        
        return max(0, min(100, score))
    
    def _calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """计算动量维度评分 0-100"""
        score = 50
        latest = df.iloc[-1]
        
        # RSI
        if 'rsi12' in df.columns:
            rsi = latest['rsi12']
            if rsi > 50:
                score += (rsi - 50) * 0.5
            else:
                score -= (50 - rsi) * 0.5
            # 避免极端值
            if rsi > 80:
                score -= 10  # 超买
            elif rsi < 20:
                score += 10  # 超卖
        
        # KDJ
        if 'j_value' in df.columns:
            j = latest['j_value']
            if j > 50:
                score += min(15, (j - 50) * 0.3)
            else:
                score -= min(15, (50 - j) * 0.3)
        
        # ROC
        if 'roc' in df.columns:
            roc = latest['roc']
            score += min(20, max(-20, roc))
        
        # MTM
        if 'mtm' in df.columns:
            mtm = latest['mtm']
            if mtm > 0:
                score += 10
            else:
                score -= 10
        
        # CCI
        if 'cci' in df.columns:
            cci = latest['cci']
            if cci > 100:
                score += 5
            elif cci < -100:
                score -= 5
        
        return max(0, min(100, score))
    
    def _calculate_volume_score(self, df: pd.DataFrame) -> float:
        """计算成交量维度评分 0-100"""
        score = 50
        
        # 成交量趋势
        if 'volume' in df.columns:
            vol_ma = df['volume'].rolling(20).mean()
            if len(vol_ma) > 0 and vol_ma.iloc[-1] > 0:
                vol_ratio = df['volume'].iloc[-1] / vol_ma.iloc[-1]
                if vol_ratio > 1.5:
                    score += 20  # 明显放量
                elif vol_ratio > 1.2:
                    score += 10
                elif vol_ratio < 0.8:
                    score -= 10  # 缩量
        
        # OBV
        if 'obv' in df.columns and 'obv_ma' in df.columns:
            if df['obv'].iloc[-1] > df['obv_ma'].iloc[-1]:
                score += 10
            else:
                score -= 10
        
        # CMF
        if 'cmf' in df.columns:
            cmf = df['cmf'].iloc[-1]
            if cmf > 0.05:
                score += 10
            elif cmf < -0.05:
                score -= 10
        
        # MFI
        if 'mfi' in df.columns:
            mfi = df['mfi'].iloc[-1]
            if 20 < mfi < 80:
                score += 5  # 正常区间
        
        return max(0, min(100, score))
    
    def _calculate_sentiment_score(self, df: pd.DataFrame) -> float:
        """计算情绪维度评分 0-100"""
        score = 50
        latest = df.iloc[-1]
        
        # PSY
        if 'psy' in df.columns:
            psy = latest['psy']
            if psy > 50:
                score += (psy - 50) * 0.4
            else:
                score -= (50 - psy) * 0.4
        
        # Williams %R
        if 'williams_r' in df.columns:
            wr = latest['williams_r']
            if wr > -20:  # 超买
                score -= 10
            elif wr < -80:  # 超卖
                score += 10
        
        # 涨跌幅
        if 'change_pct' in df.columns:
            changes = df['change_pct'].tail(5)
            if changes.mean() > 2:
                score -= 10  # 短期涨幅过大
            elif changes.mean() < -2:
                score += 10  # 短期跌幅过大
        
        return max(0, min(100, score))
    
    def get_params_grid(self) -> Dict[str, List]:
        """参数优化网格"""
        return {
            'weight_trend': [0.2, 0.25, 0.3, 0.35],
            'weight_momentum': [0.2, 0.25, 0.3, 0.35],
            'weight_volume': [0.2, 0.25, 0.3],
            'weight_sentiment': [0.2, 0.25, 0.3],
            'buy_threshold': [55, 60, 65, 70],
            'sell_threshold': [30, 35, 40, 45]
        }


class MeanReversionStrategy(StrategyBase):
    """均值回归策略"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'boll_period': 20,
            'boll_std': 2,
            'mean_period': 20
        }
        if params:
            default_params.update(params)
        super().__init__("均值回归策略", default_params)
    
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """分析均值回归信号"""
        stock_code = df['stock_code'].iloc[-1] if 'stock_code' in df.columns else 'unknown'
        latest = df.iloc[-1]
        
        score = 50
        reasons = []
        
        # RSI超买超卖
        if 'rsi12' in df.columns:
            rsi = latest['rsi12']
            if rsi < self.params['rsi_oversold']:
                score += 30
                reasons.append(f"RSI超卖({rsi:.1f})")
            elif rsi > self.params['rsi_overbought']:
                score -= 30
                reasons.append(f"RSI超买({rsi:.1f})")
        
        # 布林带
        if 'boll_position' in df.columns:
            pos = latest['boll_position']
            if pos < 0.1:
                score += 20
                reasons.append("接近布林带下轨")
            elif pos > 0.9:
                score -= 20
                reasons.append("接近布林带上轨")
        
        # 偏离均线程度
        if 'close_price' in df.columns:
            mean_price = df['close_price'].tail(self.params['mean_period']).mean()
            deviation = (latest['close_price'] - mean_price) / mean_price * 100
            
            if deviation < -5:
                score += 15
                reasons.append(f"低于均值{abs(deviation):.1f}%")
            elif deviation > 5:
                score -= 15
                reasons.append(f"高于均值{deviation:.1f}%")
        
        # 确定信号
        if score >= 70:
            signal = SignalType.BUY
        elif score <= 30:
            signal = SignalType.SELL
        else:
            signal = SignalType.HOLD
        
        return StrategySignal(
            stock_code=stock_code,
            signal=signal,
            score=score,
            confidence=abs(score - 50) / 50,
            indicators={'deviation': deviation if 'deviation' in dir() else 0},
            reason="; ".join(reasons) if reasons else "均值附近",
            timestamp=df.index[-1] if isinstance(df.index, pd.DatetimeIndex) else df.iloc[-1].get('trade_date')
        )
    
    def calculate_score(self, df: pd.DataFrame) -> float:
        signal = self.analyze(df)
        return signal.score


class TrendFollowingStrategy(StrategyBase):
    """趋势跟踪策略"""
    
    def __init__(self, params: Dict = None):
        default_params = {
            'short_ma': 5,
            'medium_ma': 20,
            'long_ma': 60,
            'adx_threshold': 25
        }
        if params:
            default_params.update(params)
        super().__init__("趋势跟踪策略", default_params)
    
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """分析趋势跟踪信号"""
        stock_code = df['stock_code'].iloc[-1] if 'stock_code' in df.columns else 'unknown'
        latest = df.iloc[-1]
        
        score = 50
        reasons = []
        
        # 均线多头排列
        ma_short = f"ma{self.params['short_ma']}"
        ma_medium = f"ma{self.params['medium_ma']}"
        ma_long = f"ma{self.params['long_ma']}"
        
        if all(m in df.columns for m in [ma_short, ma_medium, ma_long]):
            if latest[ma_short] > latest[ma_medium] > latest[ma_long]:
                score += 30
                reasons.append("均线多头排列")
            elif latest[ma_short] < latest[ma_medium] < latest[ma_long]:
                score -= 30
                reasons.append("均线空头排列")
        
        # ADX趋势强度
        if 'adx' in df.columns:
            adx = latest['adx']
            if adx > self.params['adx_threshold']:
                if '+di' in df.columns and '-di' in df.columns:
                    if latest['+di'] > latest['-di']:
                        score += 15
                        reasons.append(f"强上涨趋势(ADX={adx:.1f})")
                    else:
                        score -= 15
                        reasons.append(f"强下跌趋势(ADX={adx:.1f})")
            else:
                reasons.append(f"趋势不明(ADX={adx:.1f})")
        
        # MACD
        if 'macd_dif' in df.columns and 'macd_dea' in df.columns:
            if latest['macd_dif'] > latest['macd_dea']:
                score += 10
            else:
                score -= 10
        
        # SAR
        if 'sar' in df.columns:
            if latest['close_price'] > latest['sar']:
                score += 5
                reasons.append("SAR多头")
            else:
                score -= 5
                reasons.append("SAR空头")
        
        # 确定信号
        if score >= 70:
            signal = SignalType.STRONG_BUY
        elif score >= 55:
            signal = SignalType.BUY
        elif score <= 30:
            signal = SignalType.STRONG_SELL
        elif score <= 45:
            signal = SignalType.SELL
        else:
            signal = SignalType.HOLD
        
        return StrategySignal(
            stock_code=stock_code,
            signal=signal,
            score=score,
            confidence=abs(score - 50) / 50,
            indicators={'adx': latest.get('adx')},
            reason="; ".join(reasons) if reasons else "趋势中性",
            timestamp=df.index[-1] if isinstance(df.index, pd.DatetimeIndex) else df.iloc[-1].get('trade_date')
        )
    
    def calculate_score(self, df: pd.DataFrame) -> float:
        signal = self.analyze(df)
        return signal.score


class ParameterOptimizer:
    """策略参数优化器"""
    
    def __init__(self, strategy: StrategyBase, df: pd.DataFrame):
        self.strategy = strategy
        self.df = df
    
    def grid_search(self, metric: str = 'sharpe') -> Tuple[Dict, float]:
        """
        网格搜索最优参数
        
        Args:
            metric: 优化目标 ('sharpe', 'return', 'win_rate')
        
        Returns:
            (最优参数, 最优得分)
        """
        from itertools import product
        
        param_grid = self.strategy.get_params_grid()
        if not param_grid:
            return {}, 0
        
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        best_params = {}
        best_score = -np.inf
        
        # 遍历所有参数组合
        for values in product(*param_values):
            params = dict(zip(param_names, values))
            self.strategy.set_params(params)
            
            # 模拟回测计算得分
            score = self._evaluate_params(metric)
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
        
        return best_params, best_score
    
    def _evaluate_params(self, metric: str) -> float:
        """评估参数表现"""
        # 简化评估：使用信号准确率
        signals = []
        for i in range(50, len(self.df)):
            window = self.df.iloc[:i]
            signal = self.strategy.analyze(window)
            signals.append(signal)
        
        if not signals:
            return 0
        
        # 计算得分
        if metric == 'sharpe':
            returns = [s.score - 50 for s in signals]
            if np.std(returns) == 0:
                return 0
            return np.mean(returns) / np.std(returns)
        elif metric == 'return':
            return np.mean([s.score for s in signals])
        else:
            return np.mean([s.confidence for s in signals])


def create_strategy(strategy_type: str, params: Dict = None) -> StrategyBase:
    """策略工厂函数"""
    if strategy_type == 'multi_factor':
        return MultiFactorStrategy(params)
    elif strategy_type == 'mean_reversion':
        return MeanReversionStrategy(params)
    elif strategy_type == 'trend_following':
        return TrendFollowingStrategy(params)
    else:
        raise ValueError(f"未知策略类型: {strategy_type}")
