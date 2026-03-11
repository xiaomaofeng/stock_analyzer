"""
定时任务定义

使用APScheduler实现定时数据更新
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from loguru import logger

from config import get_settings


class DataUpdateScheduler:
    """数据更新调度器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.settings = get_settings()
        self._setup_listeners()
    
    def _setup_listeners(self):
        """设置事件监听"""
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
    
    def _job_executed_listener(self, event):
        """任务执行成功监听"""
        logger.info(f"任务执行成功: {event.job_id}")
    
    def _job_error_listener(self, event):
        """任务执行失败监听"""
        logger.error(f"任务执行失败: {event.job_id}, 异常: {event.exception}")
    
    def add_daily_update_job(self, hour: int = 17, minute: int = 0):
        """
        添加每日数据更新任务
        
        Args:
            hour: 执行小时 (默认17点，收盘后)
            minute: 执行分钟
        """
        from scripts.daily_update import DailyUpdater
        
        def update_job():
            try:
                logger.info("开始执行每日数据更新...")
                updater = DailyUpdater()
                updater.update_all()
                logger.info("每日数据更新完成")
            except Exception as e:
                logger.error(f"每日数据更新失败: {e}")
        
        self.scheduler.add_job(
            update_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_update',
            name='每日数据更新',
            replace_existing=True
        )
        
        logger.info(f"已添加每日更新任务: {hour:02d}:{minute:02d}")
    
    def add_indicator_calc_job(self, hour: int = 18, minute: int = 0):
        """
        添加指标计算任务
        
        在数据更新后执行
        """
        from scripts.calc_indicators import calculate_all_stocks
        
        def calc_job():
            try:
                logger.info("开始执行指标计算...")
                calculate_all_stocks()
                logger.info("指标计算完成")
            except Exception as e:
                logger.error(f"指标计算失败: {e}")
        
        self.scheduler.add_job(
            calc_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='indicator_calc',
            name='每日指标计算',
            replace_existing=True
        )
        
        logger.info(f"已添加指标计算任务: {hour:02d}:{minute:02d}")
    
    def add_health_check_job(self, interval_minutes: int = 30):
        """
        添加健康检查任务
        
        Args:
            interval_minutes: 检查间隔（分钟）
        """
        from scheduler.monitor import HealthMonitor
        
        monitor = HealthMonitor()
        
        self.scheduler.add_job(
            monitor.check_all,
            trigger='interval',
            minutes=interval_minutes,
            id='health_check',
            name='健康检查',
            replace_existing=True
        )
        
        logger.info(f"已添加健康检查任务: 每{interval_minutes}分钟")
    
    def start(self):
        """启动调度器"""
        self.scheduler.start()
        logger.info("调度器已启动")
    
    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        logger.info("调度器已关闭")
    
    def get_jobs(self):
        """获取所有任务"""
        return self.scheduler.get_jobs()


def run_scheduler():
    """运行调度器（阻塞模式）"""
    import signal
    import time
    
    scheduler = DataUpdateScheduler()
    
    # 添加任务
    scheduler.add_daily_update_job(hour=17, minute=0)
    scheduler.add_indicator_calc_job(hour=18, minute=0)
    scheduler.add_health_check_job(interval_minutes=30)
    
    # 启动
    scheduler.start()
    
    logger.info("按 Ctrl+C 停止调度器")
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    run_scheduler()
