"""
数据库初始化脚本
使用方法: python scripts/init_db.py
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings, init_database
from loguru import logger


def init_database_tables():
    """初始化数据库表结构"""
    logger.info("开始初始化数据库...")
    
    settings = get_settings()
    
    # 确保数据目录存在
    if settings.is_sqlite and settings.database_path:
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"数据库路径: {settings.database_path}")
    
    # 创建所有表
    init_database()
    
    logger.success("数据库初始化完成！")
    
    # 显示创建的表
    from sqlalchemy import inspect
    from config import get_engine
    
    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    logger.info(f"已创建 {len(tables)} 张表:")
    for table in tables:
        logger.info(f"  - {table}")


if __name__ == "__main__":
    init_database_tables()
