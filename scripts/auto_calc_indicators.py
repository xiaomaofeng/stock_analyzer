"""
自动化指标计算脚本

部署时自动执行，计算所有股票的技术指标
"""
import sys
from pathlib import Path
from loguru import logger
from sqlalchemy import distinct

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_session_factory
from database.models import DailyPrice, TechnicalIndicator
from processors import TechnicalCalculator
from processors.calculators import save_indicators_to_db


def auto_calc_indicators():
    """自动计算所有股票的技术指标"""
    
    logger.info("开始自动计算技术指标...")
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 获取所有有数据的股票
        stock_codes = [code[0] for code in db.query(distinct(DailyPrice.stock_code)).all()]
        
        if not stock_codes:
            logger.warning("没有找到股票数据")
            return False
        
        logger.info(f"开始计算 {len(stock_codes)} 只股票的技术指标...")
        
        calculator = TechnicalCalculator()
        total_count = 0
        success_count = 0
        
        for i, code in enumerate(stock_codes, 1):
            try:
                logger.info(f"[{i}/{len(stock_codes)}] 计算 {code} 的指标...")
                
                # 查询日线数据
                prices = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == code
                ).order_by(DailyPrice.trade_date).all()
                
                if not prices:
                    continue
                
                if len(prices) < 20:
                    logger.warning(f"{code} 数据量不足，跳过")
                    continue
                
                # 转换为DataFrame
                import pandas as pd
                df = pd.DataFrame([{
                    'trade_date': p.trade_date,
                    'open_price': p.open_price,
                    'high_price': p.high_price,
                    'low_price': p.low_price,
                    'close_price': p.close_price,
                    'volume': p.volume,
                } for p in prices])
                
                # 计算指标
                df = calculator.calculate_all(df)
                
                # 保存到数据库
                count = save_indicators_to_db(code, df, db)
                
                total_count += count
                success_count += 1
                logger.success(f"{code} 完成，{count} 条指标记录")
                
            except Exception as e:
                logger.error(f"{code} 计算失败: {e}")
                db.rollback()
        
        logger.success(f"指标计算完成！成功 {success_count}/{len(stock_codes)} 只股票，共 {total_count} 条记录")
        return True
        
    except Exception as e:
        logger.error(f"自动计算指标失败: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = auto_calc_indicators()
    sys.exit(0 if success else 1)
