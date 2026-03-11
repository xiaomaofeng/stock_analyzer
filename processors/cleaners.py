"""数据清洗模块"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta


class DataCleaner:
    """数据清洗器"""
    
    @staticmethod
    def clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗价格数据
        
        处理内容:
        1. 去除重复数据
        2. 处理缺失值
        3. 处理异常值
        4. 标准化列名
        """
        df = df.copy()
        
        # 1. 去除重复数据
        if 'trade_date' in df.columns:
            df = df.drop_duplicates(subset=['trade_date'], keep='first')
        
        # 2. 排序
        if 'trade_date' in df.columns:
            df = df.sort_values('trade_date').reset_index(drop=True)
        
        # 3. 处理缺失值
        price_cols = ['open_price', 'high_price', 'low_price', 'close_price']
        for col in price_cols:
            if col in df.columns:
                # 价格缺失用前后值填充
                df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
        
        # 4. 处理异常价格
        df = DataCleaner._fix_price_anomalies(df)
        
        # 5. 确保价格逻辑正确 (low <= open, close <= high)
        df = DataCleaner._fix_price_logic(df)
        
        return df
    
    @staticmethod
    def _fix_price_anomalies(df: pd.DataFrame, threshold: float = 0.2) -> pd.DataFrame:
        """
        修正价格异常值
        
        处理涨跌幅超过阈值的情况 (默认20%)
        """
        df = df.copy()
        
        if 'close_price' not in df.columns or len(df) < 2:
            return df
        
        # 计算涨跌幅
        df['price_change'] = df['close_price'].pct_change()
        
        # 标记异常值
        anomalies = df[df['price_change'].abs() > threshold].index
        
        for idx in anomalies:
            if idx == 0:
                continue
            
            # 用前后平均值替代
            prev_price = df.loc[idx - 1, 'close_price']
            if idx + 1 < len(df):
                next_price = df.loc[idx + 1, 'close_price']
                avg_price = (prev_price + next_price) / 2
            else:
                avg_price = prev_price
            
            # 按比例调整所有价格
            ratio = avg_price / df.loc[idx, 'close_price']
            for col in ['open_price', 'high_price', 'low_price', 'close_price']:
                if col in df.columns:
                    df.loc[idx, col] *= ratio
        
        df = df.drop(columns=['price_change'], errors='ignore')
        return df
    
    @staticmethod
    def _fix_price_logic(df: pd.DataFrame) -> pd.DataFrame:
        """修正价格逻辑关系"""
        df = df.copy()
        
        if not all(col in df.columns for col in ['open_price', 'high_price', 'low_price', 'close_price']):
            return df
        
        # 确保 low <= open, close <= high
        df['low_price'] = df[['low_price', 'open_price', 'close_price']].min(axis=1)
        df['high_price'] = df[['high_price', 'open_price', 'close_price']].max(axis=1)
        
        return df
    
    @staticmethod
    def handle_missing_dates(df: pd.DataFrame, stock_code: str = '') -> pd.DataFrame:
        """
        处理缺失的交易日
        
        识别并标记停牌日期
        """
        if df.empty or 'trade_date' not in df.columns:
            return df
        
        df = df.copy()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # 生成完整的交易日序列
        date_range = pd.date_range(
            start=df['trade_date'].min(),
            end=df['trade_date'].max(),
            freq='B'  # 工作日
        )
        
        # 找出缺失的日期
        existing_dates = set(df['trade_date'])
        missing_dates = [d for d in date_range if d not in existing_dates]
        
        # 标记是否停牌
        df['is_trading'] = True
        
        # 添加停牌记录
        if missing_dates:
            # 获取最后一个有效价格
            last_valid = df.iloc[-1] if not df.empty else None
            
            for date in missing_dates:
                # 检查是否是周末
                if date.weekday() >= 5:
                    continue
                    
                # 简单标记，实际应该检查是否是节假日
                # 这里只是示例
                pass
        
        return df
    
    @staticmethod
    def detect_suspension(df: pd.DataFrame, max_gap_days: int = 5) -> List[datetime]:
        """
        检测可能的停牌日期
        
        如果交易间隔超过max_gap_days天，认为是停牌
        """
        if df.empty or 'trade_date' not in df.columns:
            return []
        
        df = df.copy()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.sort_values('trade_date')
        
        suspensions = []
        for i in range(1, len(df)):
            gap = (df.iloc[i]['trade_date'] - df.iloc[i-1]['trade_date']).days
            if gap > max_gap_days:
                suspensions.append(df.iloc[i-1]['trade_date'])
        
        return suspensions
    
    @staticmethod
    def adjust_volume(df: pd.DataFrame) -> pd.DataFrame:
        """
        调整成交量数据
        
        处理成交量为0或异常的情况
        """
        df = df.copy()
        
        if 'volume' not in df.columns:
            return df
        
        # 成交量为0的情况用平均值填充
        zero_volume = df['volume'] == 0
        if zero_volume.any():
            avg_volume = df[df['volume'] > 0]['volume'].median()
            df.loc[zero_volume, 'volume'] = avg_volume
        
        # 处理异常大的成交量 (超过10倍中位数)
        median_volume = df['volume'].median()
        extreme_volume = df['volume'] > median_volume * 10
        if extreme_volume.any():
            df.loc[extreme_volume, 'volume'] = median_volume * 10
        
        return df
    
    @staticmethod
    def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            # 日期
            '日期': 'trade_date',
            'date': 'trade_date',
            'time': 'trade_date',
            # 开盘价
            '开盘': 'open_price',
            'open': 'open_price',
            '开盘价': 'open_price',
            # 收盘价
            '收盘': 'close_price',
            'close': 'close_price',
            '收盘价': 'close_price',
            # 最高价
            '最高': 'high_price',
            'high': 'high_price',
            '最高价': 'high_price',
            # 最低价
            '最低': 'low_price',
            'low': 'low_price',
            '最低价': 'low_price',
            # 成交量
            '成交量': 'volume',
            'volume': 'volume',
            'vol': 'volume',
            # 成交额
            '成交额': 'amount',
            'amount': 'amount',
            # 涨跌幅
            '涨跌幅': 'change_pct',
            'change': 'change_pct',
            'pct_change': 'change_pct',
            # 涨跌额
            '涨跌额': 'change_amount',
            'change_amount': 'change_amount',
            # 换手率
            '换手率': 'turnover_rate',
            'turnover': 'turnover_rate',
            # 振幅
            '振幅': 'amplitude',
            'amplitude': 'amplitude',
        }
        
        df = df.rename(columns=column_mapping)
        return df
    
    @staticmethod
    def validate_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        验证数据完整性
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        if df.empty:
            errors.append("数据为空")
            return False, errors
        
        # 检查必要列
        required_cols = ['trade_date', 'open_price', 'high_price', 'low_price', 'close_price']
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"缺少必要列: {col}")
        
        # 检查价格有效性
        if 'close_price' in df.columns:
            if (df['close_price'] <= 0).any():
                errors.append("存在收盘价小于等于0的记录")
            
            if df['close_price'].isna().any():
                errors.append("存在收盘价缺失的记录")
        
        # 检查价格逻辑
        if all(col in df.columns for col in ['low_price', 'high_price']):
            invalid = df[df['low_price'] > df['high_price']]
            if not invalid.empty:
                errors.append(f"存在{len(invalid)}条最低价高于最高价的记录")
        
        # 检查日期连续性
        if 'trade_date' in df.columns:
            df_sorted = df.sort_values('trade_date')
            duplicates = df_sorted['trade_date'].duplicated().sum()
            if duplicates > 0:
                errors.append(f"存在{duplicates}条重复日期记录")
        
        return len(errors) == 0, errors
    
    def clean_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行完整的数据清洗流程"""
        df = self.standardize_columns(df)
        df = self.clean_price_data(df)
        df = self.adjust_volume(df)
        df = self.handle_missing_dates(df)
        return df
