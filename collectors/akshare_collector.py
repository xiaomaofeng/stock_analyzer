"""AKShare数据采集器实现"""
import time
import pandas as pd
from typing import Optional, List
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
import akshare as ak

from .base import DataCollector


class AKShareCollector(DataCollector):
    """AKShare免费数据采集器"""
    
    def __init__(self, request_delay: float = 0.5, max_retries: int = 3):
        super().__init__(request_delay, max_retries)
        self._cache = {}
    
    def _sleep(self):
        """请求间隔"""
        time.sleep(self.request_delay)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_stock_list(self, market: str = "A") -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: A/港股/US
        """
        try:
            if market == "A":
                # 获取A股所有股票
                df = ak.stock_zh_a_spot_em()
                # 标准化列名
                df = df.rename(columns={
                    '代码': 'stock_code',
                    '名称': 'stock_name',
                })
                # 提取交易所
                df['exchange'] = df['stock_code'].apply(self._get_exchange)
                
            elif market == "HK":
                df = ak.stock_hk_spot_em()
                df = df.rename(columns={
                    '代码': 'stock_code',
                    '名称': 'stock_name',
                })
                df['exchange'] = 'HK'
                
            elif market == "US":
                df = ak.stock_us_spot_em()
                df = df.rename(columns={
                    '代码': 'stock_code',
                    '名称': 'stock_name',
                })
                df['exchange'] = 'US'
            else:
                raise ValueError(f"不支持的市场类型: {market}")
            
            # 统一列结构
            result = pd.DataFrame({
                'stock_code': df['stock_code'],
                'stock_name': df['stock_name'],
                'exchange': df['exchange'],
                'industry': df.get('所属行业', ''),
                'list_date': None,
            })
            
            self._sleep()
            return result
            
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            raise
    
    def _get_exchange(self, code: str) -> str:
        """根据代码判断交易所"""
        if code.startswith('6'):
            return 'SH'
        elif code.startswith('0') or code.startswith('3'):
            return 'SZ'
        elif code.startswith('8') or code.startswith('4'):
            return 'BJ'
        return 'SH'
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_daily_prices(
        self, 
        stock_code: str, 
        start_date: str, 
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取日线行情数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjust: qfq-前复权, hfq-后复权, 空-不复权
        """
        try:
            # 标准化日期格式
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")
            
            # 判断市场并调用对应接口
            if stock_code.isdigit() and len(stock_code) == 6:
                # A股
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust=adjust
                )
            elif stock_code.isdigit() and len(stock_code) == 5:
                # 港股
                df = ak.stock_hk_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust=adjust
                )
            else:
                # 美股 - 需要特殊处理代码格式
                df = ak.stock_us_hist(
                    symbol=f"105.{stock_code}",  # 东方财富格式
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust=adjust
                )
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 标准化列名
            column_mapping = {
                '日期': 'trade_date',
                '开盘': 'open_price',
                '收盘': 'close_price',
                '最高': 'high_price',
                '最低': 'low_price',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '换手率': 'turnover_rate',
            }
            
            df = df.rename(columns=column_mapping)
            
            # 添加股票代码
            df['stock_code'] = stock_code
            
            # 确保日期格式正确
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            
            # 处理昨收价
            if 'pre_close' not in df.columns:
                df['pre_close'] = df['close_price'].shift(1)
            
            self._sleep()
            return df
            
        except Exception as e:
            print(f"获取{stock_code}日线数据失败: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_financial_reports(self, stock_code: str) -> pd.DataFrame:
        """
        获取财务报表数据 - 主要财务指标
        """
        try:
            # 获取主要财务指标
            df = ak.stock_financial_report_sina(stock_code, "利润表")
            
            # TODO: 需要进一步处理财务数据
            # AKShare的财务数据接口较为复杂，可能需要组合多个接口
            
            self._sleep()
            return df
            
        except Exception as e:
            print(f"获取{stock_code}财务数据失败: {e}")
            # 返回空DataFrame而不是抛出异常
            return pd.DataFrame()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_index_list(self) -> pd.DataFrame:
        """获取主要指数列表"""
        try:
            # 获取A股指数列表
            df = ak.stock_zh_index_spot_em()
            df = df.rename(columns={
                '代码': 'index_code',
                '名称': 'index_name',
            })
            df['exchange'] = df['index_code'].apply(
                lambda x: 'SH' if x.startswith('000') else 'SZ'
            )
            
            self._sleep()
            return df[['index_code', 'index_name', 'exchange']]
            
        except Exception as e:
            print(f"获取指数列表失败: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_index_prices(
        self,
        index_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取指数行情数据"""
        try:
            start = start_date.replace("-", "")
            end = end_date.replace("-", "")
            
            df = ak.stock_zh_index_hist_csindex(
                symbol=index_code,
                start_date=start,
                end_date=end
            )
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open_price',
                '收盘': 'close_price',
                '最高': 'high_price',
                '最低': 'low_price',
                '成交量': 'volume',
                '成交金额': 'amount',
                '涨跌幅': 'change_pct',
            })
            
            df['index_code'] = index_code
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            
            self._sleep()
            return df
            
        except Exception as e:
            print(f"获取{index_code}指数数据失败: {e}")
            raise
    
    def get_stock_info(self, stock_code: str) -> Optional[dict]:
        """获取个股详细信息"""
        try:
            # 使用个股信息接口
            df = ak.stock_individual_info_em(stock_code)
            
            if df is not None and not df.empty:
                info = dict(zip(df['item'], df['value']))
                return {
                    'stock_code': stock_code,
                    'stock_name': info.get('股票简称', ''),
                    'industry': info.get('行业', ''),
                    'list_date': info.get('上市时间', ''),
                    'total_shares': info.get('总股本', ''),
                    'float_shares': info.get('流通股', ''),
                }
            return None
            
        except Exception as e:
            print(f"获取{stock_code}详细信息失败: {e}")
            return None
    
    def batch_get_daily_prices(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> dict:
        """
        批量获取日线数据
        
        Returns:
            dict: {stock_code: DataFrame}
        """
        results = {}
        total = len(stock_codes)
        
        for i, code in enumerate(stock_codes, 1):
            try:
                print(f"[{i}/{total}] 正在获取 {code}...")
                df = self.get_daily_prices(code, start_date, end_date, adjust)
                results[code] = df
            except Exception as e:
                print(f"获取{code}失败: {e}")
                results[code] = pd.DataFrame()
        
        return results
