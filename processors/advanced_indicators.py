"""
高级技术指标库

包含更多专业指标：OBV, CCI, 威廉指标, DMI, PSY, SAR, ROC, MTM等
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


class AdvancedIndicators:
    """高级技术指标计算器"""
    
    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
        """
        OBV (On Balance Volume) 能量潮
        
        原理：成交量累积，价格上涨时累加成交量，下跌时累减
        用途：判断资金流向，确认趋势
        """
        df = df.copy()
        
        # 计算价格变化方向
        price_change = df['close_price'].diff()
        
        # OBV计算
        obv = [0]
        for i in range(1, len(df)):
            if price_change.iloc[i] > 0:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif price_change.iloc[i] < 0:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        df['obv'] = obv
        df['obv_ma'] = df['obv'].rolling(window=20).mean()
        
        # OBV趋势
        df['obv_trend'] = np.where(
            df['obv'] > df['obv'].shift(1), 1,
            np.where(df['obv'] < df['obv'].shift(1), -1, 0)
        )
        
        return df
    
    @staticmethod
    def calculate_cci(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        CCI (Commodity Channel Index) 商品通道指标
        
        原理：测量价格与移动平均的偏离程度
        用途：判断超买超卖，识别趋势反转
        """
        df = df.copy()
        
        # 典型价格 (Typical Price)
        tp = (df['high_price'] + df['low_price'] + df['close_price']) / 3
        
        # TP的简单移动平均
        tp_ma = tp.rolling(window=period).mean()
        
        # 平均绝对偏差
        mean_deviation = tp.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )
        
        # CCI计算
        df['cci'] = (tp - tp_ma) / (0.015 * mean_deviation)
        
        # CCI信号
        df['cci_signal'] = np.where(
            df['cci'] > 100, 'overbought',
            np.where(df['cci'] < -100, 'oversold', 'neutral')
        )
        
        return df
    
    @staticmethod
    def calculate_williams_r(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        威廉指标 (Williams %R)
        
        原理：测量收盘价在高低点区间内的位置
        用途：判断超买超卖，与KDJ类似但计算方式不同
        """
        df = df.copy()
        
        highest_high = df['high_price'].rolling(window=period).max()
        lowest_low = df['low_price'].rolling(window=period).min()
        
        df['williams_r'] = (highest_high - df['close_price']) / (highest_high - lowest_low) * -100
        
        # 信号
        df['williams_r_signal'] = np.where(
            df['williams_r'] > -20, 'overbought',
            np.where(df['williams_r'] < -80, 'oversold', 'neutral')
        )
        
        return df
    
    @staticmethod
    def calculate_dmi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        DMI (Directional Movement Index) 趋向指标
        
        包含：+DI, -DI, ADX
        用途：判断趋势方向和强度
        """
        df = df.copy()
        
        # 真实波幅 TR
        df['tr'] = np.maximum(
            df['high_price'] - df['low_price'],
            np.maximum(
                abs(df['high_price'] - df['close_price'].shift(1)),
                abs(df['low_price'] - df['close_price'].shift(1))
            )
        )
        
        # +DM 和 -DM
        df['+dm'] = np.where(
            (df['high_price'] - df['high_price'].shift(1)) > (df['low_price'].shift(1) - df['low_price']),
            np.maximum(df['high_price'] - df['high_price'].shift(1), 0),
            0
        )
        df['-dm'] = np.where(
            (df['low_price'].shift(1) - df['low_price']) > (df['high_price'] - df['high_price'].shift(1)),
            np.maximum(df['low_price'].shift(1) - df['low_price'], 0),
            0
        )
        
        # 平滑
        tr_smooth = df['tr'].rolling(window=period).sum()
        plus_dm_smooth = df['+dm'].rolling(window=period).sum()
        minus_dm_smooth = df['-dm'].rolling(window=period).sum()
        
        # +DI 和 -DI
        df['+di'] = plus_dm_smooth / tr_smooth * 100
        df['-di'] = minus_dm_smooth / tr_smooth * 100
        
        # DX 和 ADX
        df['dx'] = abs(df['+di'] - df['-di']) / (df['+di'] + df['-di']) * 100
        df['adx'] = df['dx'].rolling(window=period).mean()
        
        # ADXR
        df['adxr'] = (df['adx'] + df['adx'].shift(period)) / 2
        
        # 信号
        df['dmi_signal'] = np.where(
            (df['+di'] > df['-di']) & (df['adx'] > 25), 'strong_uptrend',
            np.where(
                (df['+di'] < df['-di']) & (df['adx'] > 25), 'strong_downtrend',
                np.where(df['adx'] < 20, 'no_trend', 'weak_trend')
            )
        )
        
        # 清理临时列
        df = df.drop(['tr', '+dm', '-dm', 'dx'], axis=1, errors='ignore')
        
        return df
    
    @staticmethod
    def calculate_psy(df: pd.DataFrame, period: int = 12) -> pd.DataFrame:
        """
        PSY (Psychological Line) 心理线
        
        原理：统计上涨天数占比
        用途：判断市场情绪，超买超卖
        """
        df = df.copy()
        
        # 计算上涨天数
        up_days = (df['close_price'] > df['close_price'].shift(1)).astype(int)
        
        # PSY = 上涨天数 / 总天数 * 100
        df['psy'] = up_days.rolling(window=period).sum() / period * 100
        
        # PSY移动平均
        df['psy_ma'] = df['psy'].rolling(window=6).mean()
        
        # 信号
        df['psy_signal'] = np.where(
            df['psy'] > 75, 'overbought',
            np.where(df['psy'] < 25, 'oversold', 'neutral')
        )
        
        return df
    
    @staticmethod
    def calculate_sar(df: pd.DataFrame, af: float = 0.02, max_af: float = 0.2) -> pd.DataFrame:
        """
        SAR (Stop and Reverse) 抛物线转向指标
        
        原理：跟踪止损点，趋势反转时发出信号
        用途：设置止损点，判断趋势反转
        """
        df = df.copy()
        
        sar = [df['close_price'].iloc[0]]
        ep = df['high_price'].iloc[0]  # 极值点
        trend = 1  # 1为上涨，-1为下跌
        af_current = af
        
        for i in range(1, len(df)):
            prev_sar = sar[-1]
            
            # 计算SAR
            current_sar = prev_sar + af_current * (ep - prev_sar)
            
            # 判断趋势反转
            if trend == 1:  # 上涨趋势
                if df['low_price'].iloc[i] < current_sar:  # 反转下跌
                    trend = -1
                    current_sar = ep
                    ep = df['low_price'].iloc[i]
                    af_current = af
                else:
                    ep = max(ep, df['high_price'].iloc[i])
                    if ep != prev_sar:
                        af_current = min(af_current + af, max_af)
            else:  # 下跌趋势
                if df['high_price'].iloc[i] > current_sar:  # 反转上涨
                    trend = 1
                    current_sar = ep
                    ep = df['high_price'].iloc[i]
                    af_current = af
                else:
                    ep = min(ep, df['low_price'].iloc[i])
                    if ep != prev_sar:
                        af_current = min(af_current + af, max_af)
            
            # 限制SAR在高低点之间
            if trend == 1:
                current_sar = min(current_sar, df['low_price'].iloc[i-1], df['low_price'].iloc[i-2] if i > 1 else current_sar)
            else:
                current_sar = max(current_sar, df['high_price'].iloc[i-1], df['high_price'].iloc[i-2] if i > 1 else current_sar)
            
            sar.append(current_sar)
        
        df['sar'] = sar
        df['sar_trend'] = trend
        
        # 信号
        df['sar_signal'] = np.where(
            (df['close_price'] > df['sar']) & (df['close_price'].shift(1) <= df['sar'].shift(1)), 'buy',
            np.where(
                (df['close_price'] < df['sar']) & (df['close_price'].shift(1) >= df['sar'].shift(1)), 'sell', 'hold'
            )
        )
        
        return df
    
    @staticmethod
    def calculate_roc(df: pd.DataFrame, period: int = 12) -> pd.DataFrame:
        """
        ROC (Rate of Change) 变动率指标
        
        原理：计算价格变化率
        用途：判断趋势动量
        """
        df = df.copy()
        
        df['roc'] = (df['close_price'] - df['close_price'].shift(period)) / df['close_price'].shift(period) * 100
        df['roc_ma'] = df['roc'].rolling(window=6).mean()
        
        # 信号
        df['roc_signal'] = np.where(
            (df['roc'] > 0) & (df['roc'].shift(1) <= 0), 'golden',
            np.where((df['roc'] < 0) & (df['roc'].shift(1) >= 0), 'dead', 'neutral')
        )
        
        return df
    
    @staticmethod
    def calculate_mtm(df: pd.DataFrame, period: int = 12) -> pd.DataFrame:
        """
        MTM (Momentum) 动量指标
        
        原理：计算价格差值
        用途：判断价格动量
        """
        df = df.copy()
        
        df['mtm'] = df['close_price'] - df['close_price'].shift(period)
        df['mtm_ma'] = df['mtm'].rolling(window=6).mean()
        
        # 信号
        df['mtm_signal'] = np.where(
            (df['mtm'] > df['mtm_ma']) & (df['mtm'].shift(1) <= df['mtm_ma'].shift(1)), 'buy',
            np.where((df['mtm'] < df['mtm_ma']) & (df['mtm'].shift(1) >= df['mtm_ma'].shift(1)), 'sell', 'neutral')
        )
        
        return df
    
    @staticmethod
    def calculate_cmf(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        CMF (Chaikin Money Flow) 蔡金资金流量
        
        原理：结合价格和成交量的资金流向指标
        用途：判断资金流入流出
        """
        df = df.copy()
        
        # 资金流量乘数
        mfm = ((df['close_price'] - df['low_price']) - (df['high_price'] - df['close_price'])) / (df['high_price'] - df['low_price'])
        mfm = mfm.replace([np.inf, -np.inf], 0)
        
        # 资金流量体积
        mfv = mfm * df['volume']
        
        # CMF
        df['cmf'] = mfv.rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
        
        # 信号
        df['cmf_signal'] = np.where(
            df['cmf'] > 0.05, 'accumulation',
            np.where(df['cmf'] < -0.05, 'distribution', 'neutral')
        )
        
        return df
    
    @staticmethod
    def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        MFI (Money Flow Index) 资金流量指标
        
        原理：RSI的成交量加权版本
        用途：判断超买超卖，结合成交量
        """
        df = df.copy()
        
        # 典型价格
        tp = (df['high_price'] + df['low_price'] + df['close_price']) / 3
        
        # 原始资金流量
        rmf = tp * df['volume']
        
        # 判断上涨下跌
        tp_diff = tp.diff()
        
        # 正资金流量和负资金流量
        pmf = np.where(tp_diff > 0, rmf, 0)
        nmf = np.where(tp_diff < 0, rmf, 0)
        
        # 滚动求和
        pmf_sum = pd.Series(pmf).rolling(window=period).sum()
        nmf_sum = pd.Series(nmf).rolling(window=period).sum()
        
        # MFI
        money_ratio = pmf_sum / nmf_sum
        df['mfi'] = 100 - (100 / (1 + money_ratio))
        
        # 信号
        df['mfi_signal'] = np.where(
            df['mfi'] > 80, 'overbought',
            np.where(df['mfi'] < 20, 'oversold', 'neutral')
        )
        
        return df
    
    @staticmethod
    def calculate_trix(df: pd.DataFrame, period: int = 15) -> pd.DataFrame:
        """
        TRIX (Triple Exponential Average) 三重指数平滑移动平均
        
        原理：价格的三重指数平滑变化率
        用途：过滤价格噪音，识别趋势
        """
        df = df.copy()
        
        # 三重指数平滑
        ema1 = df['close_price'].ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        ema3 = ema2.ewm(span=period).mean()
        
        # TRIX
        df['trix'] = (ema3 - ema3.shift(1)) / ema3.shift(1) * 100
        df['trix_signal'] = df['trix'].ewm(span=9).mean()
        
        return df
    
    @staticmethod
    def calculate_all_advanced(df: pd.DataFrame) -> pd.DataFrame:
        """计算所有高级指标"""
        df = df.copy()
        
        df = AdvancedIndicators.calculate_obv(df)
        df = AdvancedIndicators.calculate_cci(df)
        df = AdvancedIndicators.calculate_williams_r(df)
        df = AdvancedIndicators.calculate_dmi(df)
        df = AdvancedIndicators.calculate_psy(df)
        df = AdvancedIndicators.calculate_sar(df)
        df = AdvancedIndicators.calculate_roc(df)
        df = AdvancedIndicators.calculate_mtm(df)
        df = AdvancedIndicators.calculate_cmf(df)
        df = AdvancedIndicators.calculate_mfi(df)
        df = AdvancedIndicators.calculate_trix(df)
        
        return df
    
    @staticmethod
    def get_indicator_signals(df: pd.DataFrame) -> Dict[str, Dict]:
        """获取所有指标的信号汇总"""
        latest = df.iloc[-1]
        
        signals = {
            'obv': {
                'value': latest.get('obv'),
                'trend': 'up' if latest.get('obv_trend') == 1 else 'down' if latest.get('obv_trend') == -1 else 'flat',
                'divergence': None  # 可在调用方计算背离
            },
            'cci': {
                'value': latest.get('cci'),
                'signal': latest.get('cci_signal')
            },
            'williams_r': {
                'value': latest.get('williams_r'),
                'signal': latest.get('williams_r_signal')
            },
            'dmi': {
                '+di': latest.get('+di'),
                '-di': latest.get('-di'),
                'adx': latest.get('adx'),
                'signal': latest.get('dmi_signal')
            },
            'psy': {
                'value': latest.get('psy'),
                'signal': latest.get('psy_signal')
            },
            'sar': {
                'value': latest.get('sar'),
                'trend': latest.get('sar_trend'),
                'signal': latest.get('sar_signal')
            },
            'roc': {
                'value': latest.get('roc'),
                'signal': latest.get('roc_signal')
            },
            'cmf': {
                'value': latest.get('cmf'),
                'signal': latest.get('cmf_signal')
            },
            'mfi': {
                'value': latest.get('mfi'),
                'signal': latest.get('mfi_signal')
            },
            'trix': {
                'value': latest.get('trix'),
                'signal': latest.get('trix_signal')
            }
        }
        
        return signals
