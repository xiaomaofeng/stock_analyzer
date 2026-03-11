"""数据采集器基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime


class DataCollector(ABC):
    """数据采集器抽象基类"""
    
    def __init__(self, request_delay: float = 0.5, max_retries: int = 3):
        """
        初始化采集器
        
        Args:
            request_delay: 请求间隔(秒)
            max_retries: 最大重试次数
        """
        self.request_delay = request_delay
        self.max_retries = max_retries
    
    @abstractmethod
    def get_stock_list(self, market: str = "A") -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: 市场类型 (A/港股/美股)
        
        Returns:
            DataFrame包含股票代码、名称等基础信息
        """
        pass
    
    @abstractmethod
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
            adjust: 复权类型 (qfq-前复权, hfq-后复权, 空-不复权)
        
        Returns:
            DataFrame包含日线行情数据
        """
        pass
    
    @abstractmethod
    def get_financial_reports(self, stock_code: str) -> pd.DataFrame:
        """
        获取财务报表数据
        
        Args:
            stock_code: 股票代码
        
        Returns:
            DataFrame包含财务报表数据
        """
        pass
    
    @abstractmethod
    def get_index_list(self) -> pd.DataFrame:
        """
        获取指数列表
        
        Returns:
            DataFrame包含指数代码、名称等信息
        """
        pass
    
    @abstractmethod
    def get_index_prices(
        self,
        index_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        获取指数行情数据
        
        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame包含指数行情数据
        """
        pass
    
    def validate_stock_code(self, stock_code: str, market: str = "A") -> bool:
        """
        验证股票代码格式
        
        Args:
            stock_code: 股票代码
            market: 市场类型
        
        Returns:
            是否有效
        """
        if not stock_code or not isinstance(stock_code, str):
            return False
        
        stock_code = stock_code.strip()
        
        if market == "A":
            # A股代码格式：6位数字
            return len(stock_code) == 6 and stock_code.isdigit()
        elif market == "HK":
            # 港股代码格式：5位数字
            return len(stock_code) == 5 and stock_code.isdigit()
        elif market == "US":
            # 美股代码格式：字母
            return stock_code.isalpha()
        
        return True
    
    def normalize_date(self, date_str: str) -> str:
        """
        标准化日期格式
        
        Args:
            date_str: 日期字符串
        
        Returns:
            YYYY-MM-DD格式
        """
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d")
        
        # 移除可能的分隔符
        date_str = date_str.replace("-", "").replace("/", "")
        
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        
        return date_str
