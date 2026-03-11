"""归因分析模块"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy import stats
from datetime import datetime, timedelta


@dataclass
class AttributionResult:
    """归因分析结果"""
    # 收益归因
    total_return: float
    market_return: float
    industry_return: float
    stock_selection: float
    residual: float
    
    # 风险归因
    systematic_risk: float
    idiosyncratic_risk: float
    total_risk: float
    
    # 因子暴露
    beta: float
    alpha: float
    r_squared: float
    
    # 时间范围
    start_date: datetime
    end_date: datetime
    period_days: int


class ReturnAttribution:
    """收益归因分析器"""
    
    def __init__(
        self,
        stock_returns: pd.Series,
        market_returns: pd.Series,
        industry_returns: pd.Series = None,
        risk_free_rate: float = 0.03
    ):
        """
        初始化归因分析器
        
        Args:
            stock_returns: 股票收益率序列 (日度)
            market_returns: 市场收益率序列 (日度)
            industry_returns: 行业收益率序列 (日度)
            risk_free_rate: 无风险利率 (年化)
        """
        self.stock_returns = stock_returns.dropna()
        self.market_returns = market_returns.reindex(stock_returns.index).dropna()
        self.industry_returns = industry_returns.reindex(stock_returns.index).dropna() if industry_returns is not None else None
        self.risk_free_rate = risk_free_rate / 252  # 转换为日度
    
    def capm_analysis(self) -> Dict[str, float]:
        """
        CAPM模型分析
        
        Returns:
            {
                'beta': 市场贝塔,
                'alpha': 年化阿尔法,
                'r_squared': 决定系数,
                'expected_return': 预期收益,
                'total_return': 实际总收益,
                'systematic_risk': 系统性风险,
                'idiosyncratic_risk': 特质性风险
            }
        """
        if len(self.stock_returns) < 30 or len(self.market_returns) < 30:
            return {
                'beta': 0.0,
                'alpha': 0.0,
                'r_squared': 0.0,
                'expected_return': 0.0,
                'total_return': 0.0,
                'systematic_risk': 0.0,
                'idiosyncratic_risk': 0.0
            }
        
        # 计算超额收益
        excess_stock = self.stock_returns - self.risk_free_rate
        excess_market = self.market_returns - self.risk_free_rate
        
        # 线性回归计算Beta和Alpha
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            excess_market.values,
            excess_stock.values
        )
        
        # 年化计算
        days = len(self.stock_returns)
        total_return = (1 + self.stock_returns).prod() - 1
        market_total_return = (1 + self.market_returns).prod() - 1
        
        # 年化
        annual_factor = 252 / days
        alpha = intercept * 252
        beta = slope
        r_squared = r_value ** 2
        
        # 风险分解
        stock_volatility = self.stock_returns.std() * np.sqrt(252)
        market_volatility = self.market_returns.std() * np.sqrt(252)
        systematic_risk = beta * market_volatility
        idiosyncratic_risk = stock_volatility * np.sqrt(1 - r_squared)
        
        # CAPM预期收益
        expected_return = self.risk_free_rate * 252 + beta * (market_total_return * annual_factor - self.risk_free_rate * 252)
        
        return {
            'beta': beta,
            'alpha': alpha,
            'r_squared': r_squared,
            'expected_return': expected_return,
            'total_return': total_return * annual_factor,
            'market_return': market_total_return * annual_factor,
            'systematic_risk': systematic_risk,
            'idiosyncratic_risk': idiosyncratic_risk,
            'total_risk': stock_volatility,
            'sharpe_ratio': (self.stock_returns.mean() - self.risk_free_rate) / self.stock_returns.std() * np.sqrt(252) if self.stock_returns.std() > 0 else 0,
            'treynor_ratio': (self.stock_returns.mean() - self.risk_free_rate) / beta * 252 if beta != 0 else 0,
        }
    
    def factor_analysis(self, factors: pd.DataFrame) -> Dict[str, any]:
        """
        多因子归因分析
        
        Args:
            factors: DataFrame包含各类因子收益率
                    如: 市值因子、价值因子、动量因子等
        
        Returns:
            因子暴露和贡献
        """
        from sklearn.linear_model import LinearRegression
        
        # 对齐数据
        factors = factors.reindex(self.stock_returns.index).dropna()
        returns = self.stock_returns.loc[factors.index]
        
        if len(returns) < 30:
            return {
                'factor_exposures': {},
                'factor_contributions': {},
                'r_squared': 0.0,
                'residual': 0.0
            }
        
        # 回归分析
        model = LinearRegression()
        model.fit(factors.values, returns.values)
        
        # 计算因子贡献
        factor_contributions = {}
        for i, factor_name in enumerate(factors.columns):
            exposure = model.coef_[i]
            factor_mean = factors[factor_name].mean() * 252
            contribution = exposure * factor_mean
            factor_contributions[factor_name] = {
                'exposure': exposure,
                'contribution': contribution
            }
        
        return {
            'factor_exposures': dict(zip(factors.columns, model.coef_)),
            'factor_contributions': factor_contributions,
            'r_squared': model.score(factors.values, returns.values),
            'residual': model.intercept_ * 252,
            'alpha': model.intercept_ * 252
        }
    
    def brinson_attribution(
        self,
        portfolio_weights: pd.Series,
        benchmark_weights: pd.Series,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> Dict[str, float]:
        """
        Brinson归因模型
        
        用于分析配置效应和选股效应
        
        Args:
            portfolio_weights: 组合权重
            benchmark_weights: 基准权重
            portfolio_returns: 组合收益
            benchmark_returns: 基准收益
        
        Returns:
            {
                'allocation_effect': 配置效应,
                'selection_effect': 选股效应,
                'interaction_effect': 交互效应,
                'total_excess_return': 总超额收益
            }
        """
        # 确保索引对齐
        common_index = portfolio_weights.index.intersection(benchmark_weights.index)
        portfolio_weights = portfolio_weights.loc[common_index]
        benchmark_weights = benchmark_weights.loc[common_index]
        
        portfolio_returns = portfolio_returns.loc[common_index]
        benchmark_returns = benchmark_returns.loc[common_index]
        
        # 配置效应 (Allocation Effect)
        allocation_effect = ((portfolio_weights - benchmark_weights) * 
                            (benchmark_returns - benchmark_returns.sum())).sum()
        
        # 选股效应 (Selection Effect)
        selection_effect = (benchmark_weights * 
                           (portfolio_returns - benchmark_returns)).sum()
        
        # 交互效应 (Interaction Effect)
        interaction_effect = ((portfolio_weights - benchmark_weights) * 
                             (portfolio_returns - benchmark_returns)).sum()
        
        # 总超额收益
        total_excess = (portfolio_weights * portfolio_returns).sum() - \
                       (benchmark_weights * benchmark_returns).sum()
        
        return {
            'allocation_effect': allocation_effect,
            'selection_effect': selection_effect,
            'interaction_effect': interaction_effect,
            'total_excess_return': total_excess,
            'verification': abs(allocation_effect + selection_effect + interaction_effect - total_excess) < 1e-10
        }
    
    def time_series_analysis(self) -> Dict[str, any]:
        """时间序列归因分析"""
        # 计算滚动收益
        periods = [20, 60, 120]
        rolling_returns = {}
        
        for period in periods:
            if len(self.stock_returns) >= period:
                stock_cum = (1 + self.stock_returns).rolling(period).apply(lambda x: x.prod() - 1)
                market_cum = (1 + self.market_returns).rolling(period).apply(lambda x: x.prod() - 1)
                
                rolling_returns[f'{period}d'] = {
                    'stock': stock_cum.iloc[-1] if not stock_cum.empty else 0,
                    'market': market_cum.iloc[-1] if not market_cum.empty else 0,
                    'excess': (stock_cum.iloc[-1] - market_cum.iloc[-1]) if not stock_cum.empty else 0
                }
        
        # 月度归因
        monthly_returns = self._calculate_monthly_returns()
        
        return {
            'rolling_returns': rolling_returns,
            'monthly_returns': monthly_returns,
            'win_rate': (self.stock_returns > self.market_returns).mean(),
            'up_capture': self._calculate_up_capture(),
            'down_capture': self._calculate_down_capture(),
        }
    
    def _calculate_monthly_returns(self) -> Dict:
        """计算月度收益归因"""
        stock_monthly = self.stock_returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        market_monthly = self.market_returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        
        result = {}
        for date in stock_monthly.index:
            result[date.strftime('%Y-%m')] = {
                'stock': stock_monthly.loc[date],
                'market': market_monthly.loc[date] if date in market_monthly.index else 0,
                'excess': stock_monthly.loc[date] - market_monthly.loc[date] if date in market_monthly.index else stock_monthly.loc[date]
            }
        
        return result
    
    def _calculate_up_capture(self) -> float:
        """计算上涨捕获率"""
        up_market = self.market_returns > 0
        if up_market.sum() == 0:
            return 0.0
        
        stock_up_mean = self.stock_returns[up_market].mean()
        market_up_mean = self.market_returns[up_market].mean()
        
        return (stock_up_mean / market_up_mean) if market_up_mean != 0 else 0
    
    def _calculate_down_capture(self) -> float:
        """计算下跌捕获率"""
        down_market = self.market_returns < 0
        if down_market.sum() == 0:
            return 0.0
        
        stock_down_mean = self.stock_returns[down_market].mean()
        market_down_mean = self.market_returns[down_market].mean()
        
        return (stock_down_mean / market_down_mean) if market_down_mean != 0 else 0
    
    def generate_report(self) -> Dict[str, any]:
        """生成完整的归因分析报告"""
        capm = self.capm_analysis()
        time_series = self.time_series_analysis()
        
        return {
            'summary': {
                'analysis_period': f"{self.stock_returns.index[0].strftime('%Y-%m-%d')} to {self.stock_returns.index[-1].strftime('%Y-%m-%d')}",
                'total_days': len(self.stock_returns),
                'total_return': capm['total_return'],
                'market_return': capm['market_return'],
                'excess_return': capm['total_return'] - capm['market_return'],
            },
            'capm': capm,
            'time_series': time_series,
            'conclusion': self._generate_conclusion(capm)
        }
    
    def _generate_conclusion(self, capm: Dict) -> str:
        """生成分析结论"""
        conclusions = []
        
        # Alpha分析
        if capm['alpha'] > 0.05:
            conclusions.append(f"股票创造了 {capm['alpha']*100:.2f}% 的超额收益 (Alpha)")
        elif capm['alpha'] < -0.05:
            conclusions.append(f"股票跑输基准 {abs(capm['alpha'])*100:.2f}%")
        else:
            conclusions.append("股票表现与市场基准相当")
        
        # Beta分析
        if capm['beta'] > 1.2:
            conclusions.append(f"Beta为 {capm['beta']:.2f}，股票波动大于市场，属于激进型")
        elif capm['beta'] < 0.8:
            conclusions.append(f"Beta为 {capm['beta']:.2f}，股票波动小于市场，属于防御型")
        else:
            conclusions.append(f"Beta为 {capm['beta']:.2f}，股票波动与市场相当")
        
        # R-squared分析
        if capm['r_squared'] > 0.7:
            conclusions.append(f"R²为 {capm['r_squared']:.2f}，股票走势与市场高度相关")
        elif capm['r_squared'] < 0.3:
            conclusions.append(f"R²为 {capm['r_squared']:.2f}，股票走势相对独立")
        
        return "\n".join(conclusions)


def analyze_stock_attribution(
    db_session,
    stock_code: str,
    start_date: str,
    end_date: str,
    benchmark_code: str = '000001'
) -> Dict:
    """
    分析单只股票的归因
    
    Args:
        db_session: 数据库会话
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        benchmark_code: 基准指数代码
    
    Returns:
        归因分析报告
    """
    from database.models import DailyPrice, IndexPrice
    
    # 查询股票数据
    stock_data = db_session.query(DailyPrice).filter(
        DailyPrice.stock_code == stock_code,
        DailyPrice.trade_date >= start_date,
        DailyPrice.trade_date <= end_date
    ).order_by(DailyPrice.trade_date).all()
    
    # 查询基准数据
    benchmark_data = db_session.query(IndexPrice).filter(
        IndexPrice.index_code == benchmark_code,
        IndexPrice.trade_date >= start_date,
        IndexPrice.trade_date <= end_date
    ).order_by(IndexPrice.trade_date).all()
    
    if not stock_data or not benchmark_data:
        return {'error': '数据不足'}
    
    # 计算收益率
    stock_df = pd.DataFrame([{
        'date': d.trade_date,
        'close': d.close_price
    } for d in stock_data]).set_index('date')
    
    benchmark_df = pd.DataFrame([{
        'date': d.trade_date,
        'close': d.close_price
    } for d in benchmark_data]).set_index('date')
    
    stock_returns = stock_df['close'].pct_change().dropna()
    benchmark_returns = benchmark_df['close'].pct_change().dropna()
    
    # 执行归因分析
    analyzer = ReturnAttribution(stock_returns, benchmark_returns)
    report = analyzer.generate_report()
    
    return report
