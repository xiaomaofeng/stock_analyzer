"""
技术指标计算脚本

使用方法:
    python scripts/calc_indicators.py --code 000001    # 计算单只股票
    python scripts/calc_indicators.py --all           # 计算所有股票
    python scripts/calc_indicators.py --batch --file list.txt
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy.orm import Session

from config import get_session_factory
from database.models import DailyPrice, TechnicalIndicator
from processors import TechnicalCalculator
from processors.calculators import save_indicators_to_db


def calculate_for_stock(db: Session, stock_code: str, force_update: bool = False) -> int:
    """
    为单只股票计算技术指标
    
    Args:
        db: 数据库会话
        stock_code: 股票代码
        force_update: 是否强制重新计算
    
    Returns:
        计算并保存的记录数
    """
    logger.info(f"开始计算 {stock_code} 的技术指标...")
    
    # 查询日线数据
    query = db.query(DailyPrice).filter(
        DailyPrice.stock_code == stock_code
    ).order_by(DailyPrice.trade_date)
    
    # 如果不需要强制更新，只计算还没有指标的数据
    if not force_update:
        existing_dates = db.query(TechnicalIndicator.trade_date).filter(
            TechnicalIndicator.stock_code == stock_code
        ).all()
        existing_dates = [d[0] for d in existing_dates]
        
        if existing_dates:
            query = query.filter(~DailyPrice.trade_date.in_(existing_dates))
    
    prices = query.all()
    
    if not prices:
        logger.info(f"{stock_code} 没有需要计算的新数据")
        return 0
    
    if len(prices) < 20:
        logger.warning(f"{stock_code} 数据量不足 ({len(prices)} 条)，无法计算有效指标")
        return 0
    
    # 转换为DataFrame
    import pandas as pd
    df = pd.DataFrame([{
        'trade_date': p.trade_date,
        'open_price': float(p.open_price) if p.open_price else None,
        'high_price': float(p.high_price) if p.high_price else None,
        'low_price': float(p.low_price) if p.low_price else None,
        'close_price': float(p.close_price) if p.close_price else None,
        'volume': p.volume,
    } for p in prices])
    
    # 计算指标
    calculator = TechnicalCalculator()
    df = calculator.calculate_all(df)
    
    # 保存到数据库
    count = save_indicators_to_db(stock_code, df, db)
    
    logger.success(f"{stock_code} 成功计算并保存 {count} 条指标记录")
    return count


def calculate_all_stocks(force_update: bool = False):
    """计算所有股票的技术指标"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 获取所有有日线数据的股票
        from sqlalchemy import distinct
        stock_codes = [code[0] for code in db.query(distinct(DailyPrice.stock_code)).all()]
        
        logger.info(f"开始计算 {len(stock_codes)} 只股票的技术指标...")
        
        total_count = 0
        success_count = 0
        failed_stocks = []
        
        for i, code in enumerate(stock_codes, 1):
            try:
                logger.info(f"[{i}/{len(stock_codes)}] 处理 {code}...")
                count = calculate_for_stock(db, code, force_update)
                if count >= 0:
                    total_count += count
                    success_count += 1
            except Exception as e:
                logger.error(f"{code} 计算失败: {e}")
                failed_stocks.append(code)
                db.rollback()
        
        logger.success(f"计算完成！成功 {success_count}/{len(stock_codes)} 只股票，共 {total_count} 条记录")
        
        if failed_stocks:
            logger.warning(f"失败的股票: {failed_stocks}")
            
    except Exception as e:
        logger.error(f"批量计算失败: {e}")
    finally:
        db.close()


def calculate_batch(stock_codes: list, force_update: bool = False):
    """批量计算指定股票"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        total_count = 0
        
        for i, code in enumerate(stock_codes, 1):
            try:
                logger.info(f"[{i}/{len(stock_codes)}] 处理 {code}...")
                count = calculate_for_stock(db, code, force_update)
                total_count += count
            except Exception as e:
                logger.error(f"{code} 计算失败: {e}")
                db.rollback()
        
        logger.success(f"批量计算完成！共 {total_count} 条记录")
        
    except Exception as e:
        logger.error(f"批量计算失败: {e}")
    finally:
        db.close()


def show_latest_indicators(stock_code: str):
    """显示最新的技术指标"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 查询日线数据
        prices = db.query(DailyPrice).filter(
            DailyPrice.stock_code == stock_code
        ).order_by(DailyPrice.trade_date.desc()).limit(120).all()
        
        if not prices:
            print(f"未找到 {stock_code} 的数据")
            return
        
        import pandas as pd
        df = pd.DataFrame([{
            'trade_date': p.trade_date,
            'open_price': p.open_price,
            'high_price': p.high_price,
            'low_price': p.low_price,
            'close_price': p.close_price,
            'volume': p.volume,
        } for p in reversed(prices)])
        
        # 计算指标
        calculator = TechnicalCalculator()
        df = calculator.calculate_all(df)
        
        # 获取最新信号
        signals = calculator.get_latest_signals(df)
        
        print(f"\n{'='*60}")
        print(f"股票: {stock_code}")
        print(f"最新日期: {df.iloc[-1]['trade_date']}")
        print(f"{'='*60}\n")
        
        # 价格信息
        price = signals['price']
        print("【价格信息】")
        print(f"  收盘: {price['close']:.2f}")
        print(f"  开盘: {price['open']:.2f}")
        print(f"  最高: {price['high']:.2f}")
        print(f"  最低: {price['low']:.2f}")
        
        # 均线
        print("\n【均线系统】")
        for ma, value in signals['ma'].items():
            if value:
                print(f"  {ma.upper()}: {value:.2f}")
        
        # MACD
        macd = signals['macd']
        print("\n【MACD】")
        print(f"  DIF: {macd['dif']:.4f}")
        print(f"  DEA: {macd['dea']:.4f}")
        print(f"  BAR: {macd['bar']:.4f}")
        if macd['golden_cross']:
            print("  信号: 金叉 ✓")
        elif macd['dead_cross']:
            print("  信号: 死叉 ✗")
        
        # KDJ
        kdj = signals['kdj']
        print("\n【KDJ】")
        print(f"  K: {kdj['k']:.2f}")
        print(f"  D: {kdj['d']:.2f}")
        print(f"  J: {kdj['j']:.2f}")
        if kdj['golden_cross']:
            print("  信号: 金叉 ✓")
        
        # RSI
        print("\n【RSI】")
        for rsi_name, value in signals['rsi'].items():
            if value:
                status = "超买" if value > 80 else "超卖" if value < 20 else "正常"
                print(f"  {rsi_name.upper()}: {value:.2f} ({status})")
        
        # 布林带
        boll = signals['bollinger']
        print("\n【布林带】")
        print(f"  上轨: {boll['upper']:.2f}")
        print(f"  中轨: {boll['mid']:.2f}")
        print(f"  下轨: {boll['lower']:.2f}")
        print(f"  位置: {boll['position']*100:.1f}%")
        if boll['break_upper']:
            print("  信号: 突破上轨")
        elif boll['break_lower']:
            print("  信号: 突破下轨")
        
        # 趋势
        trend = signals['trend']
        print("\n【趋势判断】")
        print(f"  短期: {trend['short']}")
        print(f"  中期: {trend['medium']}")
        print(f"  长期: {trend['long']}")
        
        print(f"\n{'='*60}")
        
    except Exception as e:
        logger.error(f"查询失败: {e}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='技术指标计算工具')
    parser.add_argument('--code', type=str, help='股票代码')
    parser.add_argument('--all', action='store_true', help='计算所有股票')
    parser.add_argument('--batch', action='store_true', help='批量模式')
    parser.add_argument('--file', type=str, help='股票代码列表文件')
    parser.add_argument('--force', action='store_true', help='强制重新计算')
    parser.add_argument('--show', action='store_true', help='显示最新指标')
    
    args = parser.parse_args()
    
    if args.show and args.code:
        show_latest_indicators(args.code)
    elif args.code:
        calculate_for_stock(get_session_factory()(), args.code, args.force)
    elif args.all:
        calculate_all_stocks(args.force)
    elif args.batch and args.file:
        with open(args.file, 'r') as f:
            codes = [line.strip() for line in f if line.strip()]
        calculate_batch(codes, args.force)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
