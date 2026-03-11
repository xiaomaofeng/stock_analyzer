"""
数据质量检查脚本

使用方法:
    python scripts/check_quality.py --code 000001     # 检查单只股票
    python scripts/check_quality.py --all            # 检查所有股票
    python scripts/check_quality.py --summary        # 显示质量摘要
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import distinct

from config import get_session_factory
from database.models import DailyPrice
from processors import QualityChecker


def check_stock_quality(db, stock_code: str) -> dict:
    """检查单只股票的数据质量"""
    logger.info(f"检查 {stock_code} 的数据质量...")
    
    # 查询数据
    prices = db.query(DailyPrice).filter(
        DailyPrice.stock_code == stock_code
    ).order_by(DailyPrice.trade_date).all()
    
    if not prices:
        return {
            'stock_code': stock_code,
            'status': 'no_data',
            'message': '无数据'
        }
    
    # 转换为DataFrame
    import pandas as pd
    df = pd.DataFrame([{
        'trade_date': p.trade_date,
        'open_price': p.open_price,
        'high_price': p.high_price,
        'low_price': p.low_price,
        'close_price': p.close_price,
        'volume': p.volume,
        'amount': p.amount,
        'change_pct': p.change_pct,
        'turnover_rate': p.turnover_rate,
    } for p in prices])
    
    # 执行质量检查
    checker = QualityChecker()
    report = checker.check_all(df, stock_code)
    
    return report.to_dict()


def check_all_stocks():
    """检查所有股票的数据质量"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        stock_codes = [code[0] for code in db.query(distinct(DailyPrice.stock_code)).all()]
        
        logger.info(f"开始检查 {len(stock_codes)} 只股票的数据质量...")
        
        reports = []
        for i, code in enumerate(stock_codes, 1):
            report = check_stock_quality(db, code)
            reports.append(report)
            
            if i % 10 == 0:
                logger.info(f"已检查 {i}/{len(stock_codes)}...")
        
        # 生成摘要
        checker = QualityChecker()
        from processors.quality_checker import QualityReport
        
        quality_reports = [
            QualityReport(
                stock_code=r['stock_code'],
                check_date=datetime.fromisoformat(r['check_date']),
                total_records=r['total_records'],
                valid_records=r['valid_records'],
                issues=r['issues'],
                score=r['score']
            ) for r in reports if 'score' in r
        ]
        
        summary = QualityChecker.generate_summary(quality_reports)
        
        print("\n" + "="*60)
        print("数据质量检查摘要")
        print("="*60)
        print(f"检查股票数: {summary['total_stocks']}")
        print(f"平均得分: {summary['average_score']}")
        print(f"总错误数: {summary['total_errors']}")
        print(f"总警告数: {summary['total_warnings']}")
        print("\n质量分级:")
        print(f"  优秀 (90-100): {summary['grade_distribution']['excellent']}")
        print(f"  良好 (70-89):  {summary['grade_distribution']['good']}")
        print(f"  一般 (50-69):  {summary['grade_distribution']['fair']}")
        print(f"  较差 (0-49):   {summary['grade_distribution']['poor']}")
        print("="*60)
        
        # 保存详细报告
        import json
        report_file = f"data/quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': summary,
                'details': reports
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"详细报告已保存到: {report_file}")
        
    except Exception as e:
        logger.error(f"质量检查失败: {e}")
    finally:
        db.close()


def show_quality_detail(stock_code: str):
    """显示质量详情"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        report = check_stock_quality(db, stock_code)
        
        print(f"\n{'='*60}")
        print(f"股票: {stock_code} 数据质量报告")
        print(f"{'='*60}")
        
        if report.get('status') == 'no_data':
            print("无数据")
            return
        
        print(f"总记录数: {report['total_records']}")
        print(f"有效记录: {report['valid_records']}")
        print(f"质量得分: {report['score']}")
        print(f"问题数量: {report['issues_count']}")
        
        if report['issues']:
            print("\n问题详情:")
            for issue in report['issues']:
                severity_icon = "✗" if issue['severity'] == 'error' else "⚠"
                print(f"  {severity_icon} [{issue['type']}] {issue['message']}")
        else:
            print("\n✓ 数据质量良好，未发现问题")
        
        print(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"检查失败: {e}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='数据质量检查工具')
    parser.add_argument('--code', type=str, help='股票代码')
    parser.add_argument('--all', action='store_true', help='检查所有股票')
    parser.add_argument('--summary', action='store_true', help='显示质量摘要')
    
    args = parser.parse_args()
    
    if args.code:
        show_quality_detail(args.code)
    elif args.all:
        check_all_stocks()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
