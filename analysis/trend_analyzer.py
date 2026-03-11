"""趋势分析模块"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class TrendDirection(Enum):
    """趋势方向"""
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    SIDEWAYS = "SIDEWAYS"
    UNKNOWN = "UNKNOWN"


class TrendStrength(Enum):
    """趋势强度"""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"


@dataclass
class TrendResult:
    """趋势分析结果"""
    direction: TrendDirection
    strength: TrendStrength
    support_levels: List[float]
    resistance_levels: List[float]
    trend_days: int
    adx: float
    description: str


class TrendAnalyzer:
    """趋势分析器"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化趋势分析器
        
        Args:
            df: 包含OHLC数据的DataFrame
        """
        self.df = df.copy()
        self._validate_data()
    
    def _validate_data(self):
        """验证数据有效性"""
        required_cols = ['close_price', 'high_price', 'low_price']
        for col in required_cols:
            if col not in self.df.columns:
                raise ValueError(f"缺少必要列: {col}")
    
    def analyze(self, short_period: int = 20, long_period: int = 60) -> TrendResult:
        """
        执行完整的趋势分析
        
        Returns:
            TrendResult: 趋势分析结果
        """
        # 计算均线
        self.df['ma_short'] = self.df['close_price'].rolling(window=short_period, min_periods=1).mean()
        self.df['ma_long'] = self.df['close_price'].rolling(window=long_period, min_periods=1).mean()
        
        # 计算ADX
        adx = self._calculate_adx()
        
        # 判断趋势方向
        direction = self._detect_trend_direction(short_period, long_period)
        
        # 判断趋势强度
        strength = self._detect_trend_strength(adx)
        
        # 计算支撑阻力位
        support_levels, resistance_levels = self._calculate_support_resistance()
        
        # 计算趋势持续天数
        trend_days = self._calculate_trend_days(direction, short_period)
        
        # 生成描述
        description = self._generate_description(direction, strength, trend_days, adx)
        
        return TrendResult(
            direction=direction,
            strength=strength,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            trend_days=trend_days,
            adx=adx,
            description=description
        )
    
    def _detect_trend_direction(self, short_period: int, long_period: int) -> TrendDirection:
        """检测趋势方向"""
        if len(self.df) < long_period:
            return TrendDirection.UNKNOWN
        
        latest = self.df.iloc[-1]
        prev_short = self.df.iloc[-short_period]
        prev_long = self.df.iloc[-long_period]
        
        # 短期趋势
        short_up = latest['ma_short'] > latest['ma_long']
        short_was_up = prev_short['ma_short'] > prev_short['ma_long']
        
        # 长期趋势
        long_up = latest['close_price'] > latest['ma_long']
        long_was_up = prev_long['close_price'] > prev_long['ma_long']
        
        # 判断
        if short_up and long_up:
            return TrendDirection.UPTREND
        elif not short_up and not long_up:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.SIDEWAYS
    
    def _detect_trend_strength(self, adx: float) -> TrendStrength:
        """根据ADX判断趋势强度"""
        if adx > 40:
            return TrendStrength.STRONG
        elif adx > 25:
            return TrendStrength.MODERATE
        elif adx > 0:
            return TrendStrength.WEAK
        else:
            return TrendStrength.UNKNOWN
    
    def _calculate_adx(self, period: int = 14) -> float:
        """
        计算ADX (Average Directional Index)
        
        ADX用于衡量趋势强度，不考虑趋势方向
        """
        if len(self.df) < period + 1:
            return 0.0
        
        df = self.df.copy()
        
        # 计算 +DM 和 -DM
        df['+dm'] = df['high_price'].diff()
        df['-dm'] = -df['low_price'].diff()
        
        df['+dm'] = np.where(
            (df['+dm'] > df['-dm']) & (df['+dm'] > 0),
            df['+dm'],
            0
        )
        df['-dm'] = np.where(
            (df['-dm'] > df['+dm']) & (df['-dm'] > 0),
            df['-dm'],
            0
        )
        
        # 计算真实波幅 TR
        df['tr1'] = df['high_price'] - df['low_price']
        df['tr2'] = (df['high_price'] - df['close_price'].shift(1)).abs()
        df['tr3'] = (df['low_price'] - df['close_price'].shift(1)).abs()
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # 计算平滑平均值
        df['+di'] = 100 * df['+dm'].rolling(window=period).mean() / df['tr'].rolling(window=period).mean()
        df['-di'] = 100 * df['-dm'].rolling(window=period).mean() / df['tr'].rolling(window=period).mean()
        
        # 计算DX和ADX
        df['dx'] = 100 * (df['+di'] - df['-di']).abs() / (df['+di'] + df['-di'])
        df['adx'] = df['dx'].rolling(window=period).mean()
        
        return df['adx'].iloc[-1] if not pd.isna(df['adx'].iloc[-1]) else 0.0
    
    def _calculate_support_resistance(
        self, 
        window: int = 20,
        method: str = 'pivot'
    ) -> Tuple[List[float], List[float]]:
        """
        计算支撑阻力位
        
        Args:
            window: 观察窗口
            method: 计算方法 ('pivot', 'fibonacci', 'recent')
        """
        if len(self.df) < window:
            return [], []
        
        recent = self.df.tail(window)
        
        if method == 'pivot':
            # 基于近期高低点
            highs = recent['high_price'].nlargest(3).tolist()
            lows = recent['low_price'].nsmallest(3).tolist()
            return lows, highs
        
        elif method == 'fibonacci':
            # 斐波那契回撤位
            high = recent['high_price'].max()
            low = recent['low_price'].min()
            diff = high - low
            
            supports = [
                low + diff * 0.236,
                low + diff * 0.382,
                low + diff * 0.5,
                low + diff * 0.618,
            ]
            resistances = [
                high - diff * 0.236,
                high - diff * 0.382,
                high - diff * 0.5,
            ]
            return supports, resistances
        
        else:  # recent
            # 使用最近的高低点
            recent_high = recent['high_price'].tail(5).max()
            recent_low = recent['low_price'].tail(5).min()
            current = self.df.iloc[-1]['close_price']
            
            return [recent_low, current * 0.95], [recent_high, current * 1.05]
    
    def _calculate_trend_days(self, direction: TrendDirection, min_period: int) -> int:
        """计算趋势持续天数"""
        if direction == TrendDirection.UNKNOWN or len(self.df) < min_period:
            return 0
        
        # 从后往前数，直到趋势改变
        days = 0
        for i in range(len(self.df) - 1, -1, -1):
            if i < min_period:
                break
            
            current = self.df.iloc[i]
            prev = self.df.iloc[i-1]
            
            # 判断当前点是否符合趋势
            if direction == TrendDirection.UPTREND:
                if current['close_price'] < prev['ma_short']:
                    break
            elif direction == TrendDirection.DOWNTREND:
                if current['close_price'] > prev['ma_short']:
                    break
            
            days += 1
        
        return days
    
    def _generate_description(
        self, 
        direction: TrendDirection, 
        strength: TrendStrength,
        days: int,
        adx: float
    ) -> str:
        """生成趋势描述"""
        direction_desc = {
            TrendDirection.UPTREND: "上涨",
            TrendDirection.DOWNTREND: "下跌",
            TrendDirection.SIDEWAYS: "震荡",
            TrendDirection.UNKNOWN: "未知"
        }
        
        strength_desc = {
            TrendStrength.STRONG: "强势",
            TrendStrength.MODERATE: "中等",
            TrendStrength.WEAK: "弱势",
            TrendStrength.UNKNOWN: "不明"
        }
        
        desc = f"当前处于{strength_desc[strength]}{direction_desc[direction]}趋势"
        
        if days > 0:
            desc += f"，已持续{days}天"
        
        if adx > 0:
            desc += f"，ADX={adx:.2f}"
        
        return desc
    
    def detect_patterns(self) -> List[Dict]:
        """检测常见K线形态"""
        patterns = []
        
        if len(self.df) < 3:
            return patterns
        
        latest = self.df.iloc[-1]
        prev1 = self.df.iloc[-2]
        prev2 = self.df.iloc[-3]
        
        # 锤子线
        body = abs(latest['close_price'] - latest['open_price'])
        lower_shadow = latest['open_price'] - latest['low_price'] if latest['close_price'] > latest['open_price'] else latest['close_price'] - latest['low_price']
        upper_shadow = latest['high_price'] - latest['close_price'] if latest['close_price'] > latest['open_price'] else latest['high_price'] - latest['open_price']
        
        if lower_shadow > 2 * body and upper_shadow < body:
            patterns.append({
                'name': '锤子线',
                'type': 'reversal',
                'signal': 'bullish',
                'description': '可能的底部反转信号'
            })
        
        # 十字星
        if body / (latest['high_price'] - latest['low_price']) < 0.1:
            patterns.append({
                'name': '十字星',
                'type': 'indecision',
                'signal': 'neutral',
                'description': '多空力量均衡，可能变盘'
            })
        
        # 吞没形态
        prev_body = abs(prev1['close_price'] - prev1['open_price'])
        curr_body = abs(latest['close_price'] - latest['open_price'])
        
        if curr_body > prev_body:
            if (latest['close_price'] > latest['open_price'] and 
                prev1['close_price'] < prev1['open_price'] and
                latest['open_price'] < prev1['close_price'] and
                latest['close_price'] > prev1['open_price']):
                patterns.append({
                    'name': '阳吞没',
                    'type': 'reversal',
                    'signal': 'bullish',
                    'description': '看涨反转信号'
                })
            elif (latest['close_price'] < latest['open_price'] and 
                  prev1['close_price'] > prev1['open_price'] and
                  latest['open_price'] > prev1['close_price'] and
                  latest['close_price'] < prev1['open_price']):
                patterns.append({
                    'name': '阴吞没',
                    'type': 'reversal',
                    'signal': 'bearish',
                    'description': '看跌反转信号'
                })
        
        return patterns
    
    def get_trading_signals(self) -> Dict:
        """获取交易信号汇总"""
        if len(self.df) < 60:
            return {'error': '数据不足'}
        
        signals = {
            'ma_signal': self._ma_signal(),
            'macd_signal': self._macd_signal(),
            'rsi_signal': self._rsi_signal(),
            'bollinger_signal': self._bollinger_signal(),
        }
        
        # 综合评分
        bullish_count = sum(1 for s in signals.values() if s.get('signal') == 'buy')
        bearish_count = sum(1 for s in signals.values() if s.get('signal') == 'sell')
        
        if bullish_count >= 3:
            signals['overall'] = {'signal': 'strong_buy', 'score': 80 + bullish_count * 5}
        elif bullish_count >= 2:
            signals['overall'] = {'signal': 'buy', 'score': 60 + bullish_count * 10}
        elif bearish_count >= 3:
            signals['overall'] = {'signal': 'strong_sell', 'score': 20 - bearish_count * 5}
        elif bearish_count >= 2:
            signals['overall'] = {'signal': 'sell', 'score': 40 - bearish_count * 10}
        else:
            signals['overall'] = {'signal': 'neutral', 'score': 50}
        
        return signals
    
    def _ma_signal(self) -> Dict:
        """均线信号"""
        if len(self.df) < 60:
            return {'signal': 'neutral'}
        
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        # 金叉/死叉检测
        golden_cross = (latest['close_price'] > latest['ma_short'] > latest['ma_long'] and
                       not (prev['close_price'] > prev['ma_short'] > prev['ma_long']))
        dead_cross = (latest['close_price'] < latest['ma_short'] < latest['ma_long'] and
                     not (prev['close_price'] < prev['ma_short'] < prev['ma_long']))
        
        if golden_cross:
            return {'signal': 'buy', 'reason': '均线金叉'}
        elif dead_cross:
            return {'signal': 'sell', 'reason': '均线死叉'}
        elif latest['close_price'] > latest['ma_short'] > latest['ma_long']:
            return {'signal': 'buy', 'reason': '均线多头排列'}
        elif latest['close_price'] < latest['ma_short'] < latest['ma_long']:
            return {'signal': 'sell', 'reason': '均线空头排列'}
        
        return {'signal': 'neutral'}
    
    def _macd_signal(self) -> Dict:
        """MACD信号"""
        if 'macd_dif' not in self.df.columns:
            return {'signal': 'neutral'}
        
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        # 金叉/死叉
        golden_cross = latest['macd_dif'] > latest['macd_dea'] and prev['macd_dif'] <= prev['macd_dea']
        dead_cross = latest['macd_dif'] < latest['macd_dea'] and prev['macd_dif'] >= prev['macd_dea']
        
        if golden_cross:
            return {'signal': 'buy', 'reason': 'MACD金叉'}
        elif dead_cross:
            return {'signal': 'sell', 'reason': 'MACD死叉'}
        elif latest['macd_dif'] > latest['macd_dea'] and latest['macd_bar'] > 0:
            return {'signal': 'buy', 'reason': 'MACD多头'}
        elif latest['macd_dif'] < latest['macd_dea'] and latest['macd_bar'] < 0:
            return {'signal': 'sell', 'reason': 'MACD空头'}
        
        return {'signal': 'neutral'}
    
    def _rsi_signal(self) -> Dict:
        """RSI信号"""
        if 'rsi12' not in self.df.columns:
            return {'signal': 'neutral'}
        
        latest = self.df.iloc[-1]
        rsi = latest.get('rsi12', 50)
        
        if rsi < 30:
            return {'signal': 'buy', 'reason': f'RSI超卖 ({rsi:.1f})'}
        elif rsi > 70:
            return {'signal': 'sell', 'reason': f'RSI超买 ({rsi:.1f})'}
        
        return {'signal': 'neutral', 'reason': f'RSI正常 ({rsi:.1f})'}
    
    def _bollinger_signal(self) -> Dict:
        """布林带信号"""
        if 'boll_upper' not in self.df.columns:
            return {'signal': 'neutral'}
        
        latest = self.df.iloc[-1]
        
        if latest['close_price'] > latest['boll_upper']:
            return {'signal': 'sell', 'reason': '突破布林带上轨'}
        elif latest['close_price'] < latest['boll_lower']:
            return {'signal': 'buy', 'reason': '跌破布林带下轨'}
        elif latest['close_price'] > latest['boll_mid']:
            return {'signal': 'buy', 'reason': '位于布林带中上轨'}
        else:
            return {'signal': 'sell', 'reason': '位于布林带中下轨'}
