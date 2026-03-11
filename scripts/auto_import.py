"""
自动化数据导入脚本

部署时自动执行，导入预设股票列表的数据
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_session_factory, get_settings
from collectors import AKShareCollector
from database.models import Stock, DailyPrice, DataUpdateLog

# 从环境变量获取股票列表
DEFAULT_STOCKS = os.getenv('INIT_STOCKS', '159892,000001,000333').split(',')


def auto_import_stocks(stock_codes=None, days=365):
    """自动导入股票数据"""
    
    if stock_codes is None:
        stock_codes = DEFAULT_STOCKS
    
    logger.info(f"开始自动导入 {len(stock_codes)} 只股票的数据...")
    logger.info(f"股票列表: {', '.join(stock_codes)}")
    
    settings = get_settings()
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        collector = AKShareCollector(
            request_delay=settings.AKSHARE_REQUEST_DELAY
        )
        
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        total_records = 0
        success_count = 0
        
        for i, code in enumerate(stock_codes, 1):
            code = code.strip()
            if not code:
                continue
            
            logger.info(f"[{i}/{len(stock_codes)}] 导入 {code}...")
            
            try:
                # 获取股票信息
                stock_info = collector.get_stock_info(code)
                
                # 保存股票信息
                existing = db.query(Stock).filter(Stock.stock_code == code).first()
                if not existing:
                    stock = Stock(
                        stock_code=code,
                        stock_name=stock_info.get('stock_name', code) if stock_info else code,
                        exchange=collector._get_exchange(code),
                        industry=stock_info.get('industry', '') if stock_info else ''
                    )
                    db.add(stock)
                    db.commit()
                
                # 获取日线数据
                df = collector.get_daily_prices(
                    code,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    adjust='qfq'
                )
                
                if df.empty:
                    logger.warning(f"{code} 无数据")
                    continue
                
                # 保存数据
                records = 0
                for _, row in df.iterrows():
                    existing = db.query(DailyPrice).filter(
                        DailyPrice.stock_code == code,
                        DailyPrice.trade_date == row['trade_date']
                    ).first()
                    
                    if existing:
                        # 更新
                        existing.open_price = row['open_price']
                        existing.high_price = row['high_price']
                        existing.low_price = row['low_price']
                        existing.close_price = row['close_price']
                        existing.volume = row.get('volume')
                        existing.amount = row.get('amount')
                        existing.change_pct = row.get('change_pct')
                        existing.turnover_rate = row.get('turnover_rate')
                    else:
                        # 新增
                        daily_price = DailyPrice(
                            stock_code=code,
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
                        records += 1
                
                db.commit()
                total_records += records
                success_count += 1
                logger.success(f"{code} 导入完成，新增 {records} 条记录")
                
            except Exception as e:
                logger.error(f"{code} 导入失败: {e}")
                db.rollback()
        
        # 记录更新日志
        log = DataUpdateLog(
            table_name='daily_prices',
            update_type='AUTO_IMPORT',
            start_date=start_date.date(),
            end_date=end_date.date(),
            record_count=total_records,
            status='SUCCESS',
            message=f'Imported {success_count}/{len(stock_codes)} stocks: {",".join(stock_codes)}'
        )
        db.add(log)
        db.commit()
        
        logger.success(f"自动导入完成！成功 {success_count}/{len(stock_codes)} 只股票，共 {total_records} 条记录")
        return True
        
    except Exception as e:
        logger.error(f"自动导入失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def check_data_exists():
    """检查是否已有数据"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        count = db.query(DailyPrice).count()
        return count > 0
    finally:
        db.close()


if __name__ == "__main__":
    # 检查是否已有数据
    if check_data_exists():
        logger.info("数据库中已有数据，跳过自动导入")
        sys.exit(0)
    
    # 执行自动导入
    success = auto_import_stocks()
    sys.exit(0 if success else 1)
