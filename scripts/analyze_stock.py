"""
股票分析脚本

使用方法:
    python scripts/analyze_stock.py --code 000001 --trend     # 趋势分析
    python scripts/analyze_stock.py --code 000001 --risk      # 风险分析
    python scripts/analyze_stock.py --code 000001 --attr      # 归因分析
    python scripts/analyze_stock.py --code 000001 --all       # 全部分析
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
import pandas as pd

from config import get_session_factory
from database.models import DailyPrice, IndexPrice
from analysis import TrendAnalyzer, ReturnAttribution, RiskMetrics


def load_stock_data(db, stock_code: str, days: int = 252):
    """加载股票数据"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    prices = db.query(DailyPrice).filter(
        DailyPrice.stock_code == stock_code,
        DailyPrice.trade_date >= start_date,
        DailyPrice.trade_date <= end_date
    ).order_by(DailyPrice.trade_date).all()
    
    if not prices:
        return None
    
    df = pd.DataFrame([{
        'trade_date': p.trade_date,
        'open_price': p.open_price,
        'high_price': p.high_price,
        'low_price': p.low_price,
        'close_price': p.close_price,
        'volume': p.volume,
        'turnover_rate': p.turnover_rate,
    } for p in prices])
    
    return df


def load_benchmark_data(db, index_code: str = '000001', days: int = 252):
    """加载基准数据"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    prices = db.query(IndexPrice).filter(
        IndexPrice.index_code == index_code,
        IndexPrice.trade_date >= start_date,
        IndexPrice.trade_date <= end_date
    ).order_by(IndexPrice.trade_date).all()
    
    if not prices:
        return None
    
    df = pd.DataFrame([{
        'trade_date': p.trade_date,
        'close_price': p.close_price,
    } for p in prices])
    
    return df


def analyze_trend(stock_code: str, df: pd.DataFrame):
    """执行趋势分析"""
    print(f"\n{'='*60}")
    print(f"趋势分析报告 - {stock_code}")
    print(f"{'='*60}")
    
    analyzer = TrendAnalyzer(df)
    result = analyzer.analyze()
    
    print(f"\n【趋势方向】{result.direction.value}")
    print(f"【趋势强度】{result.strength.value}")
    print(f"【持续天数】{result.trend_days}天")
    print(f"【ADX指标】{result.adx:.2f}")
    
    print(f"\n【描述】")
    print(f"  {result.description}")
    
    print(f"\n【支撑位】")
    for i, level in enumerate(result.support_levels[:3], 1):
        print(f"  {i}. {level:.2f}")
    
    print(f"\n【阻力位】")
    for i, level in enumerate(result.resistance_levels[:3], 1):
        print(f"  {i}. {level:.2f}")
    
    # 形态检测
    patterns = analyzer.detect_patterns()
    if patterns:
        print(f"\n【形态检测】")
        for p in patterns:
            icon = "📈" if p['signal'] == 'bullish' else "📉" if p['signal'] == 'bearish' else "➖"
            print(f"  {icon} {p['name']}: {p['description']}")
    
    # 交易信号
    signals = analyzer.get_trading_signals()
    if 'overall' in signals:
        print(f"\n【交易信号】")
        print(f"  综合评分: {signals['overall']['score']}/100")
        print(f"  信号: {signals['overall']['signal']}")
    
    print(f"\n{'='*60}")


def analyze_risk(stock_code: str, df: pd.DataFrame):
    """执行风险分析"""
    print(f"\n{'='*60}")
    print(f"风险分析报告 - {stock_code}")
    print(f"{'='*60}")
    
    # 计算收益率
    returns = df['close_price'].pct_change().dropna()
    
    # 计算风险指标
    metrics = RiskMetrics(returns)
    result = metrics.calculate_all()
    
    print(f"\n【收益指标】")
    print(f"  总收益率: {result.total_return*100:.2f}%")
    print(f"  年化收益率: {result.annualized_return*100:.2f}%")
    
    print(f"\n【风险指标】")
    print(f"  年化波动率: {result.annualized_volatility*100:.2f}%")
    print(f"  下行波动率: {result.downside_volatility*100:.2f}%")
    print(f"  最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"  最大回撤持续: {result.max_drawdown_duration}天")
    print(f"  当前回撤: {result.current_drawdown*100:.2f}%")
    
    print(f"\n【风险调整收益】")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  索提诺比率: {result.sortino_ratio:.2f}")
    print(f"  卡尔玛比率: {result.calmar_ratio:.2f}")
    
    print(f"\n【尾部风险】")
    print(f"  VaR (95%): {result.var_95*100:.2f}%")
    print(f"  VaR (99%): {result.var_99*100:.2f}%")
    print(f"  CVaR (95%): {result.cvar_95*100:.2f}%")
    print(f"  偏度: {result.skewness:.2f}")
    print(f"  峰度: {result.kurtosis:.2f}")
    
    print(f"\n{'='*60}")


def analyze_attribution(stock_code: str, df: pd.DataFrame, benchmark_df: pd.DataFrame):
    """执行归因分析"""
    print(f"\n{'='*60}")
    print(f"归因分析报告 - {stock_code}")
    print(f"{'='*60}")
    
    # 计算收益率
    stock_returns = df['close_price'].pct_change().dropna()
    benchmark_returns = benchmark_df['close_price'].pct_change().dropna()
    
    # 执行归因分析
    analyzer = ReturnAttribution(stock_returns, benchmark_returns)
    capm = analyzer.capm_analysis()
    
    print(f"\n【CAPM分析】")
    print(f"  Beta: {capm['beta']:.2f}")
    print(f"  Alpha (年化): {capm['alpha']*100:.2f}%")
    print(f"  R²: {capm['r_squared']:.2f}")
    print(f"  预期收益: {capm['expected_return']*100:.2f}%")
    print(f"  实际收益: {capm['total_return']*100:.2f}%")
    
    print(f"\n【风险分解】")
    print(f"  系统性风险: {capm['systematic_risk']*100:.2f}%")
    print(f"  特质性风险: {capm['idiosyncratic_risk']*100:.2f}%")
    print(f"  总风险: {capm['total_risk']*100:.2f}%")
    
    print(f"\n【绩效指标】")
    print(f"  夏普比率: {capm['sharpe_ratio']:.2f}")
    print(f"  特雷诺比率: {capm['treynor_ratio']:.2f}")
    
    # 时间序列分析
    ts = analyzer.time_series_analysis()
    
    print(f"\n【胜率分析】")
    print(f"  战胜市场概率: {ts['win_rate']*100:.1f}%")
    print(f"  上涨捕获率: {ts['up_capture']*100:.1f}%")
    print(f"  下跌捕获率: {ts['down_capture']*100:.1f}%")
    
    print(f"\n【滚动收益】")
    for period, data in ts['rolling_returns'].items():
        print(f"  {period}: 股票 {data['stock']*100:.2f}%, 基准 {data['market']*100:.2f}%, 超额 {data['excess']*100:.2f}%")
    
    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='股票分析工具')
    parser.add_argument('--code', type=str, required=True, help='股票代码')
    parser.add_argument('--trend', action='store_true', help='趋势分析')
    parser.add_argument('--risk', action='store_true', help='风险分析')
    parser.add_argument('--attr', action='store_true', help='归因分析')
    parser.add_argument('--all', action='store_true', help='全部分析')
    parser.add_argument('--days', type=int, default=252, help='分析天数')
    
    args = parser.parse_args()
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 加载数据
        df = load_stock_data(db, args.code, args.days)
        if df is None:
            print(f"未找到 {args.code} 的数据")
            return
        
        benchmark_df = load_benchmark_data(db, '000001', args.days)
        
        # 执行分析
        if args.all or args.trend:
            analyze_trend(args.code, df)
        
        if args.all or args.risk:
            analyze_risk(args.code, df)
        
        if args.all or args.attr:
            if benchmark_df is not None:
                analyze_attribution(args.code, df, benchmark_df)
            else:
                print("基准数据不足，跳过归因分析")
        
        if not any([args.trend, args.risk, args.attr, args.all]):
            parser.print_help()
            
    except Exception as e:
        logger.error(f"分析失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
