"""技术指标计算器"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class IndicatorConfig:
    """指标配置"""
    # 均线周期
    ma_periods: List[int] = None
    # MACD参数
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    # KDJ参数
    kdj_n: int = 9
    kdj_m1: int = 3
    kdj_m2: int = 3
    # RSI周期
    rsi_periods: List[int] = None
    # 布林带参数
    boll_period: int = 20
    boll_std: int = 2
    # ATR周期
    atr_period: int = 14
    
    def __post_init__(self):
        if self.ma_periods is None:
            self.ma_periods = [5, 10, 20, 60, 120, 250]
        if self.rsi_periods is None:
            self.rsi_periods = [6, 12, 24]


class TechnicalCalculator:
    """技术指标计算器"""
    
    def __init__(self, config: IndicatorConfig = None):
        self.config = config or IndicatorConfig()
    
    @staticmethod
    def calculate_ma(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        计算移动平均线
        
        Args:
            df: 包含close_price的DataFrame
            periods: 均线周期列表
        
        Returns:
            添加了MA列的DataFrame
        """
        if periods is None:
            periods = [5, 10, 20, 60, 120, 250]
        
        df = df.copy()
        for period in periods:
            df[f'ma{period}'] = df['close_price'].rolling(window=period, min_periods=1).mean()
        
        return df
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """计算指数移动平均线"""
        if periods is None:
            periods = [5, 10, 20, 60, 120, 250]
        
        df = df.copy()
        for period in periods:
            df[f'ema{period}'] = df['close_price'].ewm(span=period, adjust=False).mean()
        
        return df
    
    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算MACD指标
        
        MACD = DIF - DEA
        DIF = EMA(close, 12) - EMA(close, 26)
        DEA = EMA(DIF, 9)
        """
        df = df.copy()
        
        fast = self.config.macd_fast
        slow = self.config.macd_slow
        signal = self.config.macd_signal
        
        # 计算EMA
        ema_fast = df['close_price'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close_price'].ewm(span=slow, adjust=False).mean()
        
        # DIF
        df['macd_dif'] = ema_fast - ema_slow
        
        # DEA
        df['macd_dea'] = df['macd_dif'].ewm(span=signal, adjust=False).mean()
        
        # MACD柱状图 (BAR)
        df['macd_bar'] = 2 * (df['macd_dif'] - df['macd_dea'])
        
        return df
    
    def calculate_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算KDJ指标
        
        RSV = (Close - Low_n) / (High_n - Low_n) * 100
        K = 2/3 * K_prev + 1/3 * RSV
        D = 2/3 * D_prev + 1/3 * K
        J = 3*K - 2*D
        """
        df = df.copy()
        n = self.config.kdj_n
        m1 = self.config.kdj_m1
        m2 = self.config.kdj_m2
        
        # 计算n日内的最高最低价
        low_list = df['low_price'].rolling(window=n, min_periods=1).min()
        high_list = df['high_price'].rolling(window=n, min_periods=1).max()
        
        # RSV
        rsv = (df['close_price'] - low_list) / (high_list - low_list) * 100
        rsv = rsv.fillna(50)  # 处理第一个值
        
        # K值
        df['k_value'] = rsv.ewm(alpha=1/m1, adjust=False).mean()
        
        # D值
        df['d_value'] = df['k_value'].ewm(alpha=1/m2, adjust=False).mean()
        
        # J值
        df['j_value'] = 3 * df['k_value'] - 2 * df['d_value']
        
        return df
    
    def calculate_rsi(self, df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        计算RSI指标
        
        RSI = 100 - (100 / (1 + RS))
        RS = 平均上涨幅度 / 平均下跌幅度
        """
        if periods is None:
            periods = self.config.rsi_periods
        
        df = df.copy()
        
        # 计算价格变化
        delta = df['close_price'].diff()
        
        for period in periods:
            # 上涨和下跌
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # 平均上涨和下跌 (使用EMA)
            avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
            
            # RS和RSI
            rs = avg_gain / avg_loss
            df[f'rsi{period}'] = 100 - (100 / (1 + rs))
        
        return df
    
    def calculate_bollinger(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算布林带指标
        
        中轨 = N日移动平均线
        上轨 = 中轨 + k * 标准差
        下轨 = 中轨 - k * 标准差
        """
        df = df.copy()
        period = self.config.boll_period
        std_dev = self.config.boll_std
        
        # 中轨 (20日均线)
        df['boll_mid'] = df['close_price'].rolling(window=period, min_periods=1).mean()
        
        # 标准差
        std = df['close_price'].rolling(window=period, min_periods=1).std()
        
        # 上轨和下轨
        df['boll_upper'] = df['boll_mid'] + (std * std_dev)
        df['boll_lower'] = df['boll_mid'] - (std * std_dev)
        
        # 布林带宽度
        df['boll_width'] = (df['boll_upper'] - df['boll_lower']) / df['boll_mid']
        
        # 当前价格在布林带的位置 (0-1)
        df['boll_position'] = (df['close_price'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'])
        
        return df
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算ATR (Average True Range) 平均真实波幅
        
        TR = max(high-low, |high-close_prev|, |low-close_prev|)
        ATR = N日TR的移动平均
        """
        df = df.copy()
        period = self.config.atr_period
        
        # 真实波幅 TR
        high_low = df['high_price'] - df['low_price']
        high_close_prev = (df['high_price'] - df['close_price'].shift(1)).abs()
        low_close_prev = (df['low_price'] - df['close_price'].shift(1)).abs()
        
        tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # ATR
        df['atr'] = tr.rolling(window=period, min_periods=1).mean()
        
        # ATR比率 (ATR / 收盘价)
        df['atr_ratio'] = df['atr'] / df['close_price'] * 100
        
        return df
    
    @staticmethod
    def calculate_volatility(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
        """
        计算历史波动率
        
        波动率 = 收益率的标准差 * sqrt(交易日数)
        """
        if windows is None:
            windows = [20, 60, 120]
        
        df = df.copy()
        
        # 计算对数收益率
        df['log_return'] = np.log(df['close_price'] / df['close_price'].shift(1))
        
        for window in windows:
            # 年化波动率 (252个交易日)
            df[f'volatility_{window}d'] = df['log_return'].rolling(window=window, min_periods=1).std() * np.sqrt(252) * 100
        
        return df
    
    @staticmethod
    def calculate_returns(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """计算多周期收益率"""
        if periods is None:
            periods = [1, 5, 10, 20, 60]
        
        df = df.copy()
        
        for period in periods:
            df[f'return_{period}d'] = df['close_price'].pct_change(period) * 100
        
        return df
    
    @staticmethod
    def calculate_max_drawdown(df: pd.DataFrame, window: int = 252) -> pd.DataFrame:
        """
        计算最大回撤
        
        最大回撤 = (历史最高点 - 当前点) / 历史最高点
        """
        df = df.copy()
        
        # 计算滚动最高点
        rolling_max = df['close_price'].rolling(window=window, min_periods=1).max()
        
        # 回撤
        df['drawdown'] = (df['close_price'] - rolling_max) / rolling_max * 100
        
        # 最大回撤 (从开始到现在)
        cummax = df['close_price'].cummax()
        df['max_drawdown'] = (df['close_price'] - cummax) / cummax * 100
        
        return df
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            df: 包含open, high, low, close, volume的DataFrame
        
        Returns:
            包含所有技术指标的DataFrame
        """
        df = df.copy()
        
        # 确保必要的列存在
        required_cols = ['open_price', 'high_price', 'low_price', 'close_price']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")
        
        # 计算各项指标
        df = self.calculate_ma(df)
        df = self.calculate_ema(df)
        df = self.calculate_macd(df)
        df = self.calculate_kdj(df)
        df = self.calculate_rsi(df)
        df = self.calculate_bollinger(df)
        df = self.calculate_atr(df)
        df = self.calculate_volatility(df)
        df = self.calculate_returns(df)
        df = self.calculate_max_drawdown(df)
        
        return df
    
    def get_latest_signals(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        获取最新信号汇总
        
        Returns:
            包含各类指标最新值的字典
        """
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        signals = {
            'price': {
                'close': latest.get('close_price'),
                'open': latest.get('open_price'),
                'high': latest.get('high_price'),
                'low': latest.get('low_price'),
            },
            'ma': {
                f'ma{p}': latest.get(f'ma{p}') for p in self.config.ma_periods
            },
            'macd': {
                'dif': latest.get('macd_dif'),
                'dea': latest.get('macd_dea'),
                'bar': latest.get('macd_bar'),
                'golden_cross': latest.get('macd_dif', 0) > latest.get('macd_dea', 0) and 
                               df.iloc[-2].get('macd_dif', 0) <= df.iloc[-2].get('macd_dea', 0),
                'dead_cross': latest.get('macd_dif', 0) < latest.get('macd_dea', 0) and 
                             df.iloc[-2].get('macd_dif', 0) >= df.iloc[-2].get('macd_dea', 0),
            },
            'kdj': {
                'k': latest.get('k_value'),
                'd': latest.get('d_value'),
                'j': latest.get('j_value'),
                'golden_cross': latest.get('k_value', 0) > latest.get('d_value', 0) and 
                               df.iloc[-2].get('k_value', 0) <= df.iloc[-2].get('d_value', 0),
            },
            'rsi': {
                f'rsi{p}': latest.get(f'rsi{p}') for p in self.config.rsi_periods
            },
            'bollinger': {
                'upper': latest.get('boll_upper'),
                'mid': latest.get('boll_mid'),
                'lower': latest.get('boll_lower'),
                'position': latest.get('boll_position'),
                'break_upper': latest.get('close_price', 0) > latest.get('boll_upper', 0),
                'break_lower': latest.get('close_price', 0) < latest.get('boll_lower', 0),
            },
            'volatility': {
                'atr': latest.get('atr'),
                'atr_ratio': latest.get('atr_ratio'),
                'volatility_20d': latest.get('volatility_20d'),
            },
            'trend': self._judge_trend(df),
        }
        
        return signals
    
    def _judge_trend(self, df: pd.DataFrame) -> Dict[str, any]:
        """判断趋势"""
        if len(df) < 60:
            return {'short': 'UNKNOWN', 'medium': 'UNKNOWN', 'long': 'UNKNOWN'}
        
        latest = df.iloc[-1]
        prev = df.iloc[-5]  # 5天前
        
        # 短期趋势 (5日线 vs 10日线)
        short_trend = 'UP' if latest.get('ma5', 0) > latest.get('ma10', 0) else 'DOWN'
        
        # 中期趋势 (20日线方向)
        ma20_slope = latest.get('ma20', 0) - prev.get('ma20', 0)
        medium_trend = 'UP' if ma20_slope > 0 else 'DOWN'
        
        # 长期趋势 (60日线方向)
        ma60_slope = latest.get('ma60', 0) - prev.get('ma60', 0)
        long_trend = 'UP' if ma60_slope > 0 else 'DOWN'
        
        return {
            'short': short_trend,
            'medium': medium_trend,
            'long': long_trend,
        }


def save_indicators_to_db(stock_code: str, df: pd.DataFrame, db_session):
    """将计算好的指标保存到数据库"""
    from database.models import TechnicalIndicator
    
    count = 0
    for _, row in df.iterrows():
        # 检查是否已存在
        existing = db_session.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_code == stock_code,
            TechnicalIndicator.trade_date == row['trade_date']
        ).first()
        
        if existing:
            # 更新现有记录
            for col in ['ma5', 'ma10', 'ma20', 'ma60', 'ma120', 'ma250',
                       'macd_dif', 'macd_dea', 'macd_bar',
                       'k_value', 'd_value', 'j_value',
                       'rsi6', 'rsi12', 'rsi24',
                       'boll_upper', 'boll_mid', 'boll_lower',
                       'volatility_20d', 'atr14']:
                if col in row:
                    setattr(existing, col, row.get(col))
        else:
            # 创建新记录
            indicator = TechnicalIndicator(
                stock_code=stock_code,
                trade_date=row['trade_date'],
                ma5=row.get('ma5'),
                ma10=row.get('ma10'),
                ma20=row.get('ma20'),
                ma60=row.get('ma60'),
                ma120=row.get('ma120'),
                ma250=row.get('ma250'),
                macd_dif=row.get('macd_dif'),
                macd_dea=row.get('macd_dea'),
                macd_bar=row.get('macd_bar'),
                k_value=row.get('k_value'),
                d_value=row.get('d_value'),
                j_value=row.get('j_value'),
                rsi6=row.get('rsi6'),
                rsi12=row.get('rsi12'),
                rsi24=row.get('rsi24'),
                boll_upper=row.get('boll_upper'),
                boll_mid=row.get('boll_mid'),
                boll_lower=row.get('boll_lower'),
                volatility_20d=row.get('volatility_20d'),
                atr14=row.get('atr'),
            )
            db_session.add(indicator)
        
        count += 1
    
    db_session.commit()
    return count
