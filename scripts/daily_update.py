"""
每日数据更新脚本

使用方法:
    python scripts/daily_update.py              # 更新所有关注股票
    python scripts/daily_update.py --code 000001 # 更新单只股票
    
可以加入系统定时任务（crontab/Windows任务计划程序）每天收盘后执行
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy.orm import Session

from config import get_settings, get_session_factory
from collectors import AKShareCollector
from database.models import Stock, DailyPrice, DataUpdateLog


class DailyUpdater:
    """每日数据更新器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.SessionLocal = get_session_factory()
        self.collector = AKShareCollector(
            request_delay=self.settings.AKSHARE_REQUEST_DELAY
        )
    
    def get_update_stocks(self, db: Session) -> list:
        """获取需要更新的股票列表"""
        # 获取数据库中所有有历史数据的股票
        stocks_with_data = db.query(DailyPrice.stock_code).distinct().all()
        return [s[0] for s in stocks_with_data]
    
    def update_stock(self, db: Session, stock_code: str) -> int:
        """更新单只股票的最新数据"""
        try:
            # 查询该股票最后更新的日期
            last_record = db.query(DailyPrice).filter(
                DailyPrice.stock_code == stock_code
            ).order_by(DailyPrice.trade_date.desc()).first()
            
            if last_record:
                # 从最后日期的第二天开始更新
                start_date = (last_record.trade_date + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                # 如果没有历史数据，获取最近30天
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            # 如果开始日期大于结束日期，说明已经是最新数据
            if start_date > end_date:
                logger.info(f"{stock_code} 已经是最新数据")
                return 0
            
            logger.info(f"更新 {stock_code} 从 {start_date} 到 {end_date}")
            
            # 获取数据
            df = self.collector.get_daily_prices(stock_code, start_date, end_date)
            
            if df.empty:
                logger.info(f"{stock_code} 无新数据")
                return 0
            
            # 保存到数据库
            count = 0
            for _, row in df.iterrows():
                # 检查是否已存在
                existing = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == stock_code,
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
            return count
            
        except Exception as e:
            logger.error(f"更新 {stock_code} 失败: {e}")
            db.rollback()
            return 0
    
    def update_all(self, stock_codes: list = None):
        """更新所有股票"""
        db = self.SessionLocal()
        
        try:
            if stock_codes is None:
                stock_codes = self.get_update_stocks(db)
            
            if not stock_codes:
                logger.warning("没有找到需要更新的股票")
                return
            
            logger.info(f"开始更新 {len(stock_codes)} 只股票...")
            
            total_count = 0
            success_count = 0
            failed_stocks = []
            
            for i, code in enumerate(stock_codes, 1):
                logger.info(f"[{i}/{len(stock_codes)}] 更新 {code}...")
                count = self.update_stock(db, code)
                if count >= 0:
                    total_count += count
                    success_count += 1
                else:
                    failed_stocks.append(code)
            
            # 记录更新日志
            log = DataUpdateLog(
                table_name='daily_prices',
                update_type='DAILY_UPDATE',
                start_date=datetime.now().strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                record_count=total_count,
                status='SUCCESS' if not failed_stocks else 'PARTIAL',
                message=f'Updated {success_count}/{len(stock_codes)} stocks, failed: {failed_stocks}'
            )
            db.add(log)
            db.commit()
            
            logger.success(f"更新完成！成功 {success_count}/{len(stock_codes)} 只股票，新增 {total_count} 条记录")
            
            if failed_stocks:
                logger.warning(f"失败的股票: {failed_stocks}")
                
        except Exception as e:
            logger.error(f"每日更新失败: {e}")
            db.rollback()
        finally:
            db.close()
    
    def update_stock_info(self):
        """更新股票基础信息（如名称变更等）"""
        db = self.SessionLocal()
        
        try:
            stocks = db.query(Stock).all()
            logger.info(f"更新 {len(stocks)} 只股票的基础信息...")
            
            for stock in stocks:
                try:
                    info = self.collector.get_stock_info(stock.stock_code)
                    if info:
                        stock.stock_name = info.get('stock_name', stock.stock_name)
                        stock.industry = info.get('industry', stock.industry)
                except Exception as e:
                    logger.warning(f"更新 {stock.stock_code} 信息失败: {e}")
            
            db.commit()
            logger.success("股票基础信息更新完成")
            
        except Exception as e:
            logger.error(f"更新股票信息失败: {e}")
            db.rollback()
        finally:
            db.close()


def main():
    parser = argparse.ArgumentParser(description='每日数据更新')
    parser.add_argument('--code', type=str, help='更新单只股票')
    parser.add_argument('--info', action='store_true', help='更新股票基础信息')
    
    args = parser.parse_args()
    
    updater = DailyUpdater()
    
    if args.code:
        # 更新单只股票
        db = updater.SessionLocal()
        try:
            count = updater.update_stock(db, args.code)
            logger.success(f"更新完成，新增/更新 {count} 条记录")
        finally:
            db.close()
    elif args.info:
        # 更新股票信息
        updater.update_stock_info()
    else:
        # 更新所有股票
        updater.update_all()


if __name__ == "__main__":
    # 配置日志
    logger.add(
        "logs/daily_update_{time}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO"
    )
    
    # 确保日志目录存在
    Path("logs").mkdir(exist_ok=True)
    
    main()
