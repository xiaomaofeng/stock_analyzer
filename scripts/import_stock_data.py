"""
股票数据导入脚本

使用方法:
    python scripts/import_stock_data.py --code 000001 --start 2023-01-01 --end 2024-01-01
    python scripts/import_stock_data.py --all --start 2023-01-01
    python scripts/import_stock_data.py --batch --file stock_list.txt
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy.orm import Session

from config import get_settings, get_session_factory
from collectors import AKShareCollector
from database.models import Stock, DailyPrice, DataUpdateLog


def save_stock_list(db: Session, collector: AKShareCollector, market: str = "A"):
    """保存股票列表到数据库"""
    logger.info(f"正在获取{market}股股票列表...")
    
    df = collector.get_stock_list(market)
    
    if df.empty:
        logger.warning("未获取到股票列表")
        return 0
    
    count = 0
    for _, row in df.iterrows():
        # 检查是否已存在
        existing = db.query(Stock).filter(Stock.stock_code == row['stock_code']).first()
        if existing:
            continue
        
        stock = Stock(
            stock_code=row['stock_code'],
            stock_name=row['stock_name'],
            exchange=row.get('exchange', 'SH'),
            industry=row.get('industry', ''),
        )
        db.add(stock)
        count += 1
    
    db.commit()
    logger.success(f"成功导入 {count} 只股票")
    return count


def save_daily_prices(
    db: Session,
    collector: AKShareCollector,
    stock_code: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq"
) -> int:
    """
    保存日线数据到数据库
    
    Returns:
        导入的记录数
    """
    logger.info(f"正在获取 {stock_code} 从 {start_date} 到 {end_date} 的数据...")
    
    try:
        df = collector.get_daily_prices(stock_code, start_date, end_date, adjust)
        
        if df.empty:
            logger.warning(f"{stock_code} 无数据")
            return 0
        
        count = 0
        for _, row in df.iterrows():
            # 检查是否已存在
            existing = db.query(DailyPrice).filter(
                DailyPrice.stock_code == stock_code,
                DailyPrice.trade_date == row['trade_date']
            ).first()
            
            if existing:
                # 更新现有数据
                existing.open_price = row['open_price']
                existing.high_price = row['high_price']
                existing.low_price = row['low_price']
                existing.close_price = row['close_price']
                existing.volume = row.get('volume')
                existing.amount = row.get('amount')
                existing.change_pct = row.get('change_pct')
                existing.turnover_rate = row.get('turnover_rate')
            else:
                # 创建新记录
                daily_price = DailyPrice(
                    stock_code=stock_code,
                    trade_date=row['trade_date'],
                    open_price=row['open_price'],
                    high_price=row['high_price'],
                    low_price=row['low_price'],
                    close_price=row['close_price'],
                    pre_close=row.get('pre_close'),
                    volume=row.get('volume'),
                    amount=row.get('amount'),
                    turnover_rate=row.get('turnover_rate'),
                    amplitude=row.get('amplitude'),
                    change_pct=row.get('change_pct'),
                    change_amount=row.get('change_amount'),
                )
                db.add(daily_price)
            
            count += 1
        
        db.commit()
        logger.success(f"{stock_code} 成功导入 {count} 条记录")
        return count
        
    except Exception as e:
        logger.error(f"{stock_code} 导入失败: {e}")
        db.rollback()
        return 0


def import_single_stock(
    stock_code: str,
    start_date: str = None,
    end_date: str = None,
    adjust: str = "qfq"
):
    """导入单只股票数据"""
    settings = get_settings()
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        collector = AKShareCollector(
            request_delay=settings.AKSHARE_REQUEST_DELAY
        )
        
        # 先保存股票信息
        stock_info = collector.get_stock_info(stock_code)
        if stock_info:
            existing = db.query(Stock).filter(Stock.stock_code == stock_code).first()
            if not existing:
                stock = Stock(
                    stock_code=stock_code,
                    stock_name=stock_info.get('stock_name', ''),
                    exchange=collector._get_exchange(stock_code),
                    industry=stock_info.get('industry', ''),
                )
                db.add(stock)
                db.commit()
        
        # 设置默认日期
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d")
        
        # 导入日线数据
        count = save_daily_prices(db, collector, stock_code, start_date, end_date, adjust)
        
        # 记录更新日志
        log = DataUpdateLog(
            table_name='daily_prices',
            update_type='INCREMENTAL',
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date),
            record_count=count,
            status='SUCCESS',
            message=f'Stock: {stock_code}'
        )
        db.add(log)
        db.commit()
        
        logger.success(f"导入完成！共 {count} 条记录")
        
    except Exception as e:
        logger.error(f"导入失败: {e}")
        db.rollback()
    finally:
        db.close()


def import_batch_stocks(
    stock_codes: List[str],
    start_date: str = None,
    end_date: str = None
):
    """批量导入股票数据"""
    settings = get_settings()
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        collector = AKShareCollector(
            request_delay=settings.AKSHARE_REQUEST_DELAY
        )
        
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        total_count = 0
        success_count = 0
        
        for i, code in enumerate(stock_codes, 1):
            logger.info(f"[{i}/{len(stock_codes)}] 处理 {code}...")
            count = save_daily_prices(db, collector, code, start_date, end_date)
            if count > 0:
                success_count += 1
                total_count += count
        
        # 记录更新日志
        log = DataUpdateLog(
            table_name='daily_prices',
            update_type='BATCH',
            start_date=start_date,
            end_date=end_date,
            record_count=total_count,
            status='SUCCESS',
            message=f'Batch import: {success_count}/{len(stock_codes)} stocks'
        )
        db.add(log)
        db.commit()
        
        logger.success(f"批量导入完成！成功 {success_count}/{len(stock_codes)} 只股票，共 {total_count} 条记录")
        
    except Exception as e:
        logger.error(f"批量导入失败: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='股票数据导入工具')
    parser.add_argument('--code', type=str, help='股票代码')
    parser.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--adjust', type=str, default='qfq', help='复权类型 (qfq/hfq/空)')
    parser.add_argument('--batch', action='store_true', help='批量模式')
    parser.add_argument('--file', type=str, help='股票代码列表文件')
    parser.add_argument('--all', action='store_true', help='导入所有股票（慎用）')
    
    args = parser.parse_args()
    
    if args.code:
        # 单只股票
        import_single_stock(args.code, args.start, args.end, args.adjust)
    elif args.batch and args.file:
        # 从文件批量导入
        with open(args.file, 'r') as f:
            codes = [line.strip() for line in f if line.strip()]
        import_batch_stocks(codes, args.start, args.end)
    elif args.all:
        logger.warning("导入所有股票数据量很大，请确保有足够的存储空间和时间")
        confirm = input("确认继续? (yes/no): ")
        if confirm.lower() == 'yes':
            # 这里可以添加获取所有股票列表的逻辑
            logger.info("请使用 --batch --file 指定股票列表文件进行批量导入")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
