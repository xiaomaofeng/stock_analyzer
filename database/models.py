"""数据库ORM模型定义"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Date, DateTime, 
    Text, Boolean, UniqueConstraint, Index, ForeignKey
)
from sqlalchemy.sql import func

from config.database import Base


class Stock(Base):
    """股票基础信息表"""
    __tablename__ = "stocks"
    
    stock_code = Column(String(20), primary_key=True, comment="股票代码")
    stock_name = Column(String(100), comment="股票名称")
    exchange = Column(String(10), comment="交易所 (SH/SZ/BJ/HK/US)")
    industry = Column(String(50), comment="所属行业")
    sector = Column(String(50), comment="所属板块")
    list_date = Column(Date, comment="上市日期")
    delist_date = Column(Date, nullable=True, comment="退市日期")
    total_shares = Column(BigInteger, comment="总股本")
    float_shares = Column(BigInteger, comment="流通股本")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联关系
    daily_prices = relationship("DailyPrice", back_populates="stock")
    financial_reports = relationship("FinancialReport", back_populates="stock")
    technical_indicators = relationship("TechnicalIndicator", back_populates="stock")


class DailyPrice(Base):
    """日线行情数据表"""
    __tablename__ = "daily_prices"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), ForeignKey("stocks.stock_code"), nullable=False, comment="股票代码")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    
    # 价格数据
    open_price = Column(Float(10, 4), comment="开盘价")
    high_price = Column(Float(10, 4), comment="最高价")
    low_price = Column(Float(10, 4), comment="最低价")
    close_price = Column(Float(10, 4), comment="收盘价")
    pre_close = Column(Float(10, 4), comment="昨收价")
    
    # 成交量额
    volume = Column(BigInteger, comment="成交量（股）")
    amount = Column(Float(20, 4), comment="成交额（元）")
    turnover_rate = Column(Float(10, 4), comment="换手率")
    amplitude = Column(Float(10, 4), comment="振幅")
    
    # 涨跌幅
    change_pct = Column(Float(10, 4), comment="涨跌幅(%)")
    change_amount = Column(Float(10, 4), comment="涨跌额")
    
    # 复权因子
    adj_factor = Column(Float(15, 8), comment="复权因子")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    # 唯一约束和索引
    __table_args__ = (
        UniqueConstraint('stock_code', 'trade_date', name='uk_stock_date'),
        Index('idx_daily_price_date', 'trade_date'),
        Index('idx_daily_price_stock', 'stock_code'),
    )
    
    # 关联关系
    stock = relationship("Stock", back_populates="daily_prices")


class FinancialReport(Base):
    """财务数据表"""
    __tablename__ = "financial_reports"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), ForeignKey("stocks.stock_code"), nullable=False, comment="股票代码")
    report_date = Column(Date, nullable=False, comment="报告期")
    report_type = Column(String(10), comment="报告类型 (Q1/Q2/Q3/Annual)")
    
    # 利润表关键指标
    revenue = Column(Float(20, 4), comment="营业收入")
    net_profit = Column(Float(20, 4), comment="净利润")
    gross_profit = Column(Float(20, 4), comment="毛利润")
    operating_profit = Column(Float(20, 4), comment="营业利润")
    
    # 资产负债表关键指标
    total_assets = Column(Float(20, 4), comment="总资产")
    total_liabilities = Column(Float(20, 4), comment="总负债")
    equity = Column(Float(20, 4), comment="股东权益")
    
    # 现金流量表关键指标
    operating_cash_flow = Column(Float(20, 4), comment="经营活动现金流")
    investing_cash_flow = Column(Float(20, 4), comment="投资活动现金流")
    financing_cash_flow = Column(Float(20, 4), comment="筹资活动现金流")
    
    # 关键财务比率
    eps = Column(Float(10, 4), comment="每股收益")
    roe = Column(Float(10, 4), comment="净资产收益率(%)")
    gross_margin = Column(Float(10, 4), comment="毛利率(%)")
    debt_ratio = Column(Float(10, 4), comment="资产负债率(%)")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        UniqueConstraint('stock_code', 'report_date', 'report_type', name='uk_stock_report'),
        Index('idx_financial_stock', 'stock_code'),
        Index('idx_financial_date', 'report_date'),
    )
    
    stock = relationship("Stock", back_populates="financial_reports")


class TechnicalIndicator(Base):
    """技术指标表"""
    __tablename__ = "technical_indicators"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), ForeignKey("stocks.stock_code"), nullable=False, comment="股票代码")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    
    # 均线系统
    ma5 = Column(Float(10, 4), comment="5日均线")
    ma10 = Column(Float(10, 4), comment="10日均线")
    ma20 = Column(Float(10, 4), comment="20日均线")
    ma60 = Column(Float(10, 4), comment="60日均线")
    ma120 = Column(Float(10, 4), comment="120日均线")
    ma250 = Column(Float(10, 4), comment="250日均线")
    
    # MACD
    macd_dif = Column(Float(10, 4), comment="MACD DIF")
    macd_dea = Column(Float(10, 4), comment="MACD DEA")
    macd_bar = Column(Float(10, 4), comment="MACD BAR")
    
    # KDJ
    k_value = Column(Float(10, 4), comment="K值")
    d_value = Column(Float(10, 4), comment="D值")
    j_value = Column(Float(10, 4), comment="J值")
    
    # RSI
    rsi6 = Column(Float(10, 4), comment="RSI6")
    rsi12 = Column(Float(10, 4), comment="RSI12")
    rsi24 = Column(Float(10, 4), comment="RSI24")
    
    # 布林带
    boll_upper = Column(Float(10, 4), comment="布林带上轨")
    boll_mid = Column(Float(10, 4), comment="布林带中轨")
    boll_lower = Column(Float(10, 4), comment="布林带下轨")
    
    # 波动率
    volatility_20d = Column(Float(10, 4), comment="20日波动率")
    atr14 = Column(Float(10, 4), comment="14日ATR")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        UniqueConstraint('stock_code', 'trade_date', name='uk_indicator_stock_date'),
        Index('idx_indicator_date', 'trade_date'),
        Index('idx_indicator_stock', 'stock_code'),
    )
    
    stock = relationship("Stock", back_populates="technical_indicators")


class IndexPrice(Base):
    """市场指数数据表"""
    __tablename__ = "index_prices"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    index_code = Column(String(20), nullable=False, comment="指数代码")
    index_name = Column(String(50), comment="指数名称")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    
    open_price = Column(Float(10, 4), comment="开盘价")
    high_price = Column(Float(10, 4), comment="最高价")
    low_price = Column(Float(10, 4), comment="最低价")
    close_price = Column(Float(10, 4), comment="收盘价")
    volume = Column(BigInteger, comment="成交量")
    amount = Column(Float(20, 4), comment="成交额")
    change_pct = Column(Float(10, 4), comment="涨跌幅(%)")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        UniqueConstraint('index_code', 'trade_date', name='uk_index_date'),
        Index('idx_index_price_date', 'trade_date'),
        Index('idx_index_code', 'index_code'),
    )


class AttributionResult(Base):
    """归因分析结果表"""
    __tablename__ = "attribution_results"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, comment="股票代码")
    analysis_date = Column(Date, nullable=False, comment="分析日期")
    analysis_period = Column(String(20), comment="分析周期 (1M/3M/6M/1Y)")
    
    # 收益归因
    total_return = Column(Float(10, 4), comment="总收益(%)")
    market_return = Column(Float(10, 4), comment="市场收益贡献(%)")
    industry_return = Column(Float(10, 4), comment="行业收益贡献(%)")
    stock_selection = Column(Float(10, 4), comment="选股收益(%)")
    
    # 风险归因
    systematic_risk = Column(Float(10, 4), comment="系统性风险")
    idiosyncratic_risk = Column(Float(10, 4), comment="特质性风险")
    
    # 因子暴露
    beta = Column(Float(10, 4), comment="市场贝塔")
    size_factor = Column(Float(10, 4), comment="市值因子")
    value_factor = Column(Float(10, 4), comment="价值因子")
    momentum_factor = Column(Float(10, 4), comment="动量因子")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        UniqueConstraint('stock_code', 'analysis_date', 'analysis_period', name='uk_stock_analysis'),
        Index('idx_attribution_date', 'analysis_date'),
        Index('idx_attribution_stock', 'stock_code'),
    )


class TradeRecord(Base):
    """交易记录表"""
    __tablename__ = "trade_records"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strategy_name = Column(String(50), comment="策略名称")
    stock_code = Column(String(20), nullable=False, comment="股票代码")
    trade_date = Column(DateTime, nullable=False, comment="交易时间")
    trade_type = Column(String(10), comment="交易类型 (BUY/SELL)")
    price = Column(Float(10, 4), comment="成交价格")
    volume = Column(Integer, comment="成交数量")
    amount = Column(Float(20, 4), comment="成交金额")
    fee = Column(Float(10, 4), comment="手续费")
    remark = Column(Text, comment="备注")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index('idx_trade_date', 'trade_date'),
        Index('idx_trade_stock', 'stock_code'),
        Index('idx_trade_strategy', 'strategy_name'),
    )


class DataUpdateLog(Base):
    """数据更新日志表"""
    __tablename__ = "data_update_log"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(String(50), comment="表名")
    update_type = Column(String(20), comment="更新类型 (FULL/INCREMENTAL)")
    start_date = Column(Date, comment="数据起始日期")
    end_date = Column(Date, comment="数据结束日期")
    record_count = Column(Integer, comment="更新记录数")
    status = Column(String(20), comment="状态 (SUCCESS/FAILED)")
    message = Column(Text, comment="消息")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index('idx_update_log_table', 'table_name'),
        Index('idx_update_log_date', 'created_at'),
    )


# 导入relationship以避免循环引用
from sqlalchemy.orm import relationship
