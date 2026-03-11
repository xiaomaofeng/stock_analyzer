"""数据采集模块"""
from .base import DataCollector
from .akshare_collector import AKShareCollector

__all__ = ['DataCollector', 'AKShareCollector']
