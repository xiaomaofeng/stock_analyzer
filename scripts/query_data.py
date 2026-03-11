"""
数据查询工具脚本

使用方法:
    python scripts/query_data.py --code 000001 --limit 20
    python scripts/query_data.py --list
    python scripts/query_data.py --stats
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import func

from config import get_session_factory
from database.models import Stock, DailyPrice, DataUpdateLog


def list_stocks():
    """列出所有股票"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        stocks = db.query(Stock).all()
        print(f"\n共 {len(stocks)} 只股票:\n")
        print(f"{'代码':<10} {'名称':<15} {'交易所':<8} {'行业':<20}")
        print("-" * 60)
        for s in stocks[:50]:  # 只显示前50只
            print(f"{s.stock_code:<10} {s.stock_name:<15} {s.exchange:<8} {s.industry or '-':<20}")
        
        if len(stocks) > 50:
            print(f"\n... 还有 {len(stocks) - 50} 只股票未显示")
            
    finally:
        db.close()


def query_stock_data(stock_code: str, limit: int = 20):
    """查询股票日线数据"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 查询股票信息
        stock = db.query(Stock).filter(Stock.stock_code == stock_code).first()
        if not stock:
            print(f"未找到股票 {stock_code}")
            return
        
        print(f"\n股票: {stock.stock_name} ({stock_code})")
        print(f"行业: {stock.industry or '未知'}")
        print()
        
        # 查询日线数据
        prices = db.query(DailyPrice).filter(
            DailyPrice.stock_code == stock_code
        ).order_by(DailyPrice.trade_date.desc()).limit(limit).all()
        
        if not prices:
            print("无历史数据")
            return
        
        print(f"{'日期':<12} {'开盘':<10} {'收盘':<10} {'最高':<10} {'最低':<10} {'涨幅':<10} {'成交量':<15}")
        print("-" * 90)
        
        for p in prices:
            change_str = f"{p.change_pct:+.2f}%" if p.change_pct else "-"
            volume_str = f"{p.volume/10000:.2f}万" if p.volume else "-"
            print(f"{p.trade_date:<12} {p.open_price:<10.2f} {p.close_price:<10.2f} "
                  f"{p.high_price:<10.2f} {p.low_price:<10.2f} {change_str:<10} {volume_str:<15}")
        
        print(f"\n共 {len(prices)} 条记录")
        
    finally:
        db.close()


def show_stats():
    """显示数据库统计信息"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        print("\n=== 数据库统计 ===\n")
        
        # 股票数量
        stock_count = db.query(Stock).count()
        print(f"股票总数: {stock_count}")
        
        # 日线数据数量
        price_count = db.query(DailyPrice).count()
        print(f"日线数据: {price_count} 条")
        
        # 各交易所分布
        print("\n交易所分布:")
        exchange_stats = db.query(Stock.exchange, func.count(Stock.stock_code)).group_by(Stock.exchange).all()
        for ex, count in exchange_stats:
            print(f"  {ex}: {count} 只")
        
        # 数据更新统计
        print("\n最近更新:")
        recent_logs = db.query(DataUpdateLog).order_by(
            DataUpdateLog.created_at.desc()
        ).limit(5).all()
        
        for log in recent_logs:
            print(f"  {log.created_at.strftime('%Y-%m-%d %H:%M')} | {log.table_name} | "
                  f"{log.update_type} | {log.record_count}条 | {log.status}")
        
        # 数据日期范围
        print("\n数据日期范围:")
        date_range = db.query(
            func.min(DailyPrice.trade_date),
            func.max(DailyPrice.trade_date)
        ).first()
        
        if date_range[0]:
            print(f"  从 {date_range[0]} 到 {date_range[1]}")
        
    finally:
        db.close()


def export_to_csv(stock_code: str, output: str = None):
    """导出数据到CSV"""
    import pandas as pd
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 查询数据
        prices = db.query(DailyPrice).filter(
            DailyPrice.stock_code == stock_code
        ).order_by(DailyPrice.trade_date).all()
        
        if not prices:
            print(f"无数据可导出")
            return
        
        # 转换为DataFrame
        data = [{
            'trade_date': p.trade_date,
            'open': p.open_price,
            'high': p.high_price,
            'low': p.low_price,
            'close': p.close_price,
            'volume': p.volume,
            'amount': p.amount,
            'change_pct': p.change_pct,
            'turnover_rate': p.turnover_rate,
        } for p in prices]
        
        df = pd.DataFrame(data)
        
        # 确定输出文件名
        if not output:
            output = f"{stock_code}_data.csv"
        
        df.to_csv(output, index=False, encoding='utf-8-sig')
        print(f"数据已导出到: {output}")
        print(f"共 {len(df)} 条记录")
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='数据查询工具')
    parser.add_argument('--list', action='store_true', help='列出所有股票')
    parser.add_argument('--code', type=str, help='股票代码')
    parser.add_argument('--limit', type=int, default=20, help='显示记录数')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--export', type=str, help='导出到CSV文件')
    
    args = parser.parse_args()
    
    if args.list:
        list_stocks()
    elif args.stats:
        show_stats()
    elif args.code and args.export:
        export_to_csv(args.code, args.export)
    elif args.code:
        query_stock_data(args.code, args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
