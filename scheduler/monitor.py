"""
数据监控和告警模块
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from loguru import logger

from config import get_session_factory
from database.models import DailyPrice, DataUpdateLog, Stock


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    check_name: str
    status: str  # 'ok', 'warning', 'error'
    message: str
    details: Dict = None


class HealthMonitor:
    """数据健康监控器"""
    
    def __init__(self):
        self.SessionLocal = get_session_factory()
        self.checks = []
        self.alerts = []
    
    def check_data_freshness(self, max_delay_hours: int = 24) -> HealthCheckResult:
        """检查数据时效性"""
        db = self.SessionLocal()
        
        try:
            latest_date = db.query(DailyPrice.trade_date).order_by(
                DailyPrice.trade_date.desc()
            ).first()
            
            if not latest_date:
                return HealthCheckResult(
                    check_name='数据时效性',
                    status='error',
                    message='数据库中无数据',
                    details={'latest_date': None}
                )
            
            latest_date = latest_date[0]
            today = datetime.now().date()
            days_diff = (today - latest_date).days
            
            if days_diff == 0:
                status = 'ok'
                message = f'数据已更新至 {latest_date}'
            elif days_diff <= 2:
                status = 'warning'
                message = f'数据有 {days_diff} 天延迟，最新日期 {latest_date}'
            else:
                status = 'error'
                message = f'数据延迟 {days_diff} 天，请及时更新'
            
            return HealthCheckResult(
                check_name='数据时效性',
                status=status,
                message=message,
                details={
                    'latest_date': str(latest_date),
                    'days_delay': days_diff
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name='数据时效性',
                status='error',
                message=f'检查失败: {str(e)}'
            )
        finally:
            db.close()
    
    def check_data_completeness(self, min_stocks: int = 10) -> HealthCheckResult:
        """检查数据完整性"""
        db = self.SessionLocal()
        
        try:
            # 统计股票数量
            stock_count = db.query(Stock).count()
            price_count = db.query(DailyPrice).count()
            
            if stock_count < min_stocks:
                status = 'warning'
                message = f'股票数量较少: {stock_count} 只'
            else:
                status = 'ok'
                message = f'数据完整: {stock_count} 只股票，{price_count} 条记录'
            
            # 检查最近是否有数据更新失败
            recent_logs = db.query(DataUpdateLog).filter(
                DataUpdateLog.created_at >= datetime.now() - timedelta(days=1)
            ).order_by(DataUpdateLog.created_at.desc()).all()
            
            failed_logs = [log for log in recent_logs if log.status == 'FAILED']
            
            if failed_logs:
                status = 'warning'
                message += f' (最近有 {len(failed_logs)} 次更新失败)'
            
            return HealthCheckResult(
                check_name='数据完整性',
                status=status,
                message=message,
                details={
                    'stock_count': stock_count,
                    'price_count': price_count,
                    'failed_logs': len(failed_logs)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name='数据完整性',
                status='error',
                message=f'检查失败: {str(e)}'
            )
        finally:
            db.close()
    
    def check_data_quality(self) -> HealthCheckResult:
        """检查数据质量"""
        db = self.SessionLocal()
        
        try:
            # 检查异常数据
            # 1. 价格为0或负数
            zero_prices = db.query(DailyPrice).filter(
                DailyPrice.close_price <= 0
            ).count()
            
            # 2. 缺失成交量
            zero_volume = db.query(DailyPrice).filter(
                DailyPrice.volume == 0
            ).count()
            
            issues = []
            if zero_prices > 0:
                issues.append(f"{zero_prices} 条记录收盘价异常")
            if zero_volume > 0:
                issues.append(f"{zero_volume} 条记录成交量为0")
            
            if issues:
                status = 'warning'
                message = f"发现数据质量问题: {'; '.join(issues)}"
            else:
                status = 'ok'
                message = '数据质量良好'
            
            return HealthCheckResult(
                check_name='数据质量',
                status=status,
                message=message,
                details={
                    'zero_prices': zero_prices,
                    'zero_volume': zero_volume
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name='数据质量',
                status='error',
                message=f'检查失败: {str(e)}'
            )
        finally:
            db.close()
    
    def check_update_status(self) -> HealthCheckResult:
        """检查更新任务状态"""
        db = self.SessionLocal()
        
        try:
            # 查询最近的更新日志
            recent_logs = db.query(DataUpdateLog).filter(
                DataUpdateLog.created_at >= datetime.now() - timedelta(hours=25)
            ).order_by(DataUpdateLog.created_at.desc()).all()
            
            if not recent_logs:
                return HealthCheckResult(
                    check_name='更新状态',
                    status='warning',
                    message='24小时内无更新记录',
                    details={'last_update': None}
                )
            
            # 检查是否有失败记录
            failed = [log for log in recent_logs if log.status == 'FAILED']
            
            if failed:
                status = 'error'
                message = f'最近24小时内有 {len(failed)} 次更新失败'
            else:
                status = 'ok'
                last_update = recent_logs[0].created_at
                message = f'更新正常，上次更新: {last_update.strftime("%Y-%m-%d %H:%M")}'
            
            return HealthCheckResult(
                check_name='更新状态',
                status=status,
                message=message,
                details={
                    'recent_updates': len(recent_logs),
                    'failed_updates': len(failed)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name='更新状态',
                status='error',
                message=f'检查失败: {str(e)}'
            )
        finally:
            db.close()
    
    def check_all(self) -> List[HealthCheckResult]:
        """执行所有检查"""
        checks = [
            self.check_data_freshness(),
            self.check_data_completeness(),
            self.check_data_quality(),
            self.check_update_status()
        ]
        
        # 记录检查结果
        for check in checks:
            if check.status == 'error':
                logger.error(f"[健康检查] {check.check_name}: {check.message}")
            elif check.status == 'warning':
                logger.warning(f"[健康检查] {check.check_name}: {check.message}")
            else:
                logger.info(f"[健康检查] {check.check_name}: {check.message}")
        
        return checks
    
    def generate_report(self) -> Dict:
        """生成健康报告"""
        checks = self.check_all()
        
        ok_count = sum(1 for c in checks if c.status == 'ok')
        warning_count = sum(1 for c in checks if c.status == 'warning')
        error_count = sum(1 for c in checks if c.status == 'error')
        
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(checks),
                'ok': ok_count,
                'warning': warning_count,
                'error': error_count,
                'health_score': int(ok_count / len(checks) * 100) if checks else 0
            },
            'checks': [
                {
                    'name': c.check_name,
                    'status': c.status,
                    'message': c.message,
                    'details': c.details
                } for c in checks
            ]
        }


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alerts = []
    
    def send_alert(self, level: str, message: str, details: Dict = None):
        """发送告警"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'details': details or {}
        }
        
        self.alerts.append(alert)
        
        # 记录到日志
        if level == 'critical':
            logger.critical(f"[告警] {message}")
        elif level == 'warning':
            logger.warning(f"[告警] {message}")
        else:
            logger.info(f"[通知] {message}")
        
        return alert
    
    def check_and_alert(self, monitor: HealthMonitor):
        """检查并发送告警"""
        checks = monitor.check_all()
        
        for check in checks:
            if check.status == 'error':
                self.send_alert('critical', check.message, check.details)
            elif check.status == 'warning':
                self.send_alert('warning', check.message, check.details)
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """获取最近告警"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert['timestamp']) > cutoff
        ]


def run_health_check():
    """运行健康检查并打印报告"""
    monitor = HealthMonitor()
    report = monitor.generate_report()
    
    print("\n" + "="*60)
    print("系统健康报告")
    print("="*60)
    print(f"检查时间: {report['timestamp']}")
    print(f"健康评分: {report['summary']['health_score']}/100")
    print(f"正常: {report['summary']['ok']}, 警告: {report['summary']['warning']}, 错误: {report['summary']['error']}")
    print("-"*60)
    
    for check in report['checks']:
        status_icon = "✓" if check['status'] == 'ok' else "⚠" if check['status'] == 'warning' else "✗"
        print(f"{status_icon} {check['name']}: {check['message']}")
    
    print("="*60 + "\n")
    
    return report


if __name__ == "__main__":
    run_health_check()
