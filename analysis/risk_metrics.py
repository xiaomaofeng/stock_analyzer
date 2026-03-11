"""风险指标计算模块"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats
from dataclasses import dataclass


@dataclass
class RiskMetricsResult:
    """风险指标结果"""
    # 收益指标
    total_return: float
    annualized_return: float
    
    # 风险指标
    volatility: float
    annualized_volatility: float
    downside_volatility: float
    max_drawdown: float
    max_drawdown_duration: int
    
    # 风险调整收益
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    information_ratio: float
    
    # 回撤指标
    current_drawdown: float
    avg_drawdown: float
    
    # 尾部风险
    var_95: float
    var_99: float
    cvar_95: float
    skewness: float
    kurtosis: float


class RiskMetrics:
    """风险指标计算器"""
    
    def __init__(self, returns: pd.Series, risk_free_rate: float = 0.03):
        """
        初始化风险指标计算器
        
        Args:
            returns: 收益率序列 (日度)
            risk_free_rate: 无风险利率 (年化)
        """
        self.returns = returns.dropna()
        self.risk_free_rate = risk_free_rate / 252  # 转换为日度
        self.days = len(self.returns)
        self.annual_factor = 252
    
    def calculate_all(self) -> RiskMetricsResult:
        """计算所有风险指标"""
        if self.days < 30:
            return self._empty_result()
        
        return RiskMetricsResult(
            total_return=self._total_return(),
            annualized_return=self._annualized_return(),
            volatility=self._volatility(),
            annualized_volatility=self._annualized_volatility(),
            downside_volatility=self._downside_volatility(),
            max_drawdown=self._max_drawdown(),
            max_drawdown_duration=self._max_drawdown_duration(),
            sharpe_ratio=self._sharpe_ratio(),
            sortino_ratio=self._sortino_ratio(),
            calmar_ratio=self._calmar_ratio(),
            information_ratio=0.0,  # 需要基准收益
            current_drawdown=self._current_drawdown(),
            avg_drawdown=self._avg_drawdown(),
            var_95=self._var_95(),
            var_99=self._var_99(),
            cvar_95=self._cvar_95(),
            skewness=self._skewness(),
            kurtosis=self._kurtosis()
        )
    
    def _empty_result(self) -> RiskMetricsResult:
        """返回空结果"""
        return RiskMetricsResult(
            total_return=0.0,
            annualized_return=0.0,
            volatility=0.0,
            annualized_volatility=0.0,
            downside_volatility=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            information_ratio=0.0,
            current_drawdown=0.0,
            avg_drawdown=0.0,
            var_95=0.0,
            var_99=0.0,
            cvar_95=0.0,
            skewness=0.0,
            kurtosis=0.0
        )
    
    def _total_return(self) -> float:
        """总收益率"""
        return (1 + self.returns).prod() - 1
    
    def _annualized_return(self) -> float:
        """年化收益率"""
        total_return = self._total_return()
        years = self.days / self.annual_factor
        return (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
    
    def _volatility(self) -> float:
        """波动率（标准差）"""
        return self.returns.std()
    
    def _annualized_volatility(self) -> float:
        """年化波动率"""
        return self.returns.std() * np.sqrt(self.annual_factor)
    
    def _downside_volatility(self) -> float:
        """下行波动率（只计算负收益的标准差）"""
        downside_returns = self.returns[self.returns < 0]
        if len(downside_returns) < 2:
            return 0.0
        return downside_returns.std() * np.sqrt(self.annual_factor)
    
    def _max_drawdown(self) -> float:
        """最大回撤"""
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def _max_drawdown_duration(self) -> int:
        """最大回撤持续天数"""
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        
        # 找到最大回撤结束点
        max_dd_end = drawdown.idxmin()
        
        # 找到回撤开始点（之前的最高点）
        max_dd_start = cumulative.loc[:max_dd_end].idxmax()
        
        # 计算持续天数
        duration = (max_dd_end - max_dd_start).days if hasattr(max_dd_end, 'days') else \
                   (pd.to_datetime(max_dd_end) - pd.to_datetime(max_dd_start)).days
        
        return max(0, duration)
    
    def _current_drawdown(self) -> float:
        """当前回撤"""
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.iloc[-1]
    
    def _avg_drawdown(self) -> float:
        """平均回撤"""
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.mean()
    
    def _sharpe_ratio(self) -> float:
        """夏普比率"""
        excess_return = self.returns.mean() - self.risk_free_rate
        volatility = self.returns.std()
        if volatility == 0:
            return 0.0
        return excess_return / volatility * np.sqrt(self.annual_factor)
    
    def _sortino_ratio(self) -> float:
        """索提诺比率（使用下行波动率）"""
        excess_return = self.returns.mean() - self.risk_free_rate
        downside_vol = self._downside_volatility()
        if downside_vol == 0:
            return 0.0
        return excess_return * np.sqrt(self.annual_factor) / (downside_vol / np.sqrt(self.annual_factor))
    
    def _calmar_ratio(self) -> float:
        """卡尔玛比率（年化收益/最大回撤）"""
        annual_return = self._annualized_return()
        max_dd = abs(self._max_drawdown())
        if max_dd == 0:
            return 0.0
        return annual_return / max_dd
    
    def _var_95(self) -> float:
        """95%置信度的VaR"""
        return np.percentile(self.returns, 5)
    
    def _var_99(self) -> float:
        """99%置信度的VaR"""
        return np.percentile(self.returns, 1)
    
    def _cvar_95(self) -> float:
        """95%置信度的CVaR（条件VaR）"""
        var_95 = self._var_95()
        return self.returns[self.returns <= var_95].mean()
    
    def _skewness(self) -> float:
        """偏度"""
        return stats.skew(self.returns)
    
    def _kurtosis(self) -> float:
        """峰度"""
        return stats.kurtosis(self.returns)
    
    def calculate_information_ratio(
        self,
        benchmark_returns: pd.Series
    ) -> float:
        """
        计算信息比率
        
        信息比率 = 超额收益 / 跟踪误差
        """
        # 对齐数据
        aligned_stock = self.returns.reindex(benchmark_returns.index).dropna()
        aligned_benchmark = benchmark_returns.reindex(aligned_stock.index)
        
        if len(aligned_stock) < 30:
            return 0.0
        
        # 超额收益
        excess_returns = aligned_stock - aligned_benchmark
        
        # 跟踪误差
        tracking_error = excess_returns.std() * np.sqrt(self.annual_factor)
        
        # 信息比率
        if tracking_error == 0:
            return 0.0
        
        return excess_returns.mean() * self.annual_factor / tracking_error
    
    def calculate_beta(self, market_returns: pd.Series) -> float:
        """计算Beta系数"""
        aligned_stock = self.returns.reindex(market_returns.index).dropna()
        aligned_market = market_returns.reindex(aligned_stock.index)
        
        if len(aligned_stock) < 30:
            return 1.0
        
        covariance = aligned_stock.cov(aligned_market)
        market_variance = aligned_market.var()
        
        return covariance / market_variance if market_variance != 0 else 1.0
    
    def calculate_alpha(self, market_returns: pd.Series) -> float:
        """计算Alpha（年化）"""
        beta = self.calculate_beta(market_returns)
        
        stock_return = self.returns.mean() * self.annual_factor
        market_return = market_returns.mean() * self.annual_factor
        
        return stock_return - (self.risk_free_rate * self.annual_factor + beta * (market_return - self.risk_free_rate * self.annual_factor))
    
    def rolling_metrics(
        self,
        window: int = 60,
        metric: str = 'sharpe'
    ) -> pd.Series:
        """
        计算滚动指标
        
        Args:
            window: 滚动窗口
            metric: 指标类型 ('sharpe', 'volatility', 'drawdown')
        """
        if metric == 'sharpe':
            return self._rolling_sharpe(window)
        elif metric == 'volatility':
            return self.returns.rolling(window).std() * np.sqrt(self.annual_factor)
        elif metric == 'drawdown':
            return self._rolling_drawdown(window)
        else:
            raise ValueError(f"未知的指标类型: {metric}")
    
    def _rolling_sharpe(self, window: int) -> pd.Series:
        """滚动夏普比率"""
        rolling_return = self.returns.rolling(window).mean()
        rolling_std = self.returns.rolling(window).std()
        return (rolling_return - self.risk_free_rate) / rolling_std * np.sqrt(self.annual_factor)
    
    def _rolling_drawdown(self, window: int) -> pd.Series:
        """滚动回撤"""
        rolling_cum = (1 + self.returns).rolling(window).apply(lambda x: x.prod())
        rolling_max = rolling_cum.expanding().max()
        return (rolling_cum - rolling_max) / rolling_max
    
    def generate_report(self, benchmark_returns: pd.Series = None) -> Dict:
        """生成完整的风险报告"""
        metrics = self.calculate_all()
        
        report = {
            'summary': {
                'analysis_period_days': self.days,
                'analysis_period_years': round(self.days / 252, 2),
                'total_return': f"{metrics.total_return*100:.2f}%",
                'annualized_return': f"{metrics.annualized_return*100:.2f}%",
                'annualized_volatility': f"{metrics.annualized_volatility*100:.2f}%",
            },
            'risk_adjusted_returns': {
                'sharpe_ratio': round(metrics.sharpe_ratio, 2),
                'sortino_ratio': round(metrics.sortino_ratio, 2),
                'calmar_ratio': round(metrics.calmar_ratio, 2),
            },
            'drawdown_analysis': {
                'max_drawdown': f"{metrics.max_drawdown*100:.2f}%",
                'max_drawdown_duration': f"{metrics.max_drawdown_duration}天",
                'current_drawdown': f"{metrics.current_drawdown*100:.2f}%",
                'average_drawdown': f"{metrics.avg_drawdown*100:.2f}%",
            },
            'tail_risk': {
                'var_95': f"{metrics.var_95*100:.2f}%",
                'var_99': f"{metrics.var_99*100:.2f}%",
                'cvar_95': f"{metrics.cvar_95*100:.2f}%",
                'skewness': round(metrics.skewness, 2),
                'kurtosis': round(metrics.kurtosis, 2),
            }
        }
        
        # 如果有基准收益，添加对比指标
        if benchmark_returns is not None:
            report['benchmark_comparison'] = {
                'beta': round(self.calculate_beta(benchmark_returns), 2),
                'alpha': f"{self.calculate_alpha(benchmark_returns)*100:.2f}%",
                'information_ratio': round(self.calculate_information_ratio(benchmark_returns), 2),
            }
        
        return report


def analyze_portfolio_risk(
    returns_dict: Dict[str, pd.Series],
    weights: Dict[str, float] = None,
    risk_free_rate: float = 0.03
) -> Dict:
    """
    分析投资组合风险
    
    Args:
        returns_dict: {股票代码: 收益率序列}
        weights: {股票代码: 权重}，如果为None则等权重
        risk_free_rate: 无风险利率
    
    Returns:
        组合风险分析结果
    """
    # 对齐数据
    common_index = None
    for code, returns in returns_dict.items():
        if common_index is None:
            common_index = returns.index
        else:
            common_index = common_index.intersection(returns.index)
    
    aligned_returns = {}
    for code, returns in returns_dict.items():
        aligned_returns[code] = returns.loc[common_index]
    
    # 构建收益矩阵
    returns_df = pd.DataFrame(aligned_returns)
    
    # 确定权重
    if weights is None:
        n = len(returns_dict)
        weights = {code: 1/n for code in returns_dict.keys()}
    
    weight_array = np.array([weights.get(code, 0) for code in returns_df.columns])
    
    # 计算组合收益
    portfolio_returns = returns_df.dot(weight_array)
    
    # 计算风险指标
    metrics = RiskMetrics(portfolio_returns, risk_free_rate)
    result = metrics.calculate_all()
    
    # 计算组合波动率分解
    cov_matrix = returns_df.cov()
    portfolio_variance = weight_array.T @ cov_matrix.values @ weight_array
    portfolio_volatility = np.sqrt(portfolio_variance) * np.sqrt(252)
    
    return {
        'portfolio_metrics': {
            'annualized_return': f"{result.annualized_return*100:.2f}%",
            'annualized_volatility': f"{portfolio_volatility*100:.2f}%",
            'sharpe_ratio': round(result.sharpe_ratio, 2),
            'max_drawdown': f"{result.max_drawdown*100:.2f}%",
        },
        'diversification': {
            'number_of_stocks': len(returns_dict),
            'effective_diversification': len(returns_df.columns),
            'average_correlation': returns_df.corr().mean().mean(),
        },
        'weights': weights
    }
