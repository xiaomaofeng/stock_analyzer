"""数据库连接配置 - 支持SQLite/PostgreSQL/MySQL"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool, QueuePool
from typing import Generator
import os

from .settings import get_settings

# 创建ORM基类
Base = declarative_base()

# 全局引擎和会话工厂
_engine = None
_session_factory = None


def get_engine():
    """获取数据库引擎（单例）"""
    global _engine
    if _engine is None:
        settings = get_settings()
        
        # 确保目录存在
        settings.ensure_directories()
        
        if settings.is_sqlite:
            _engine = _create_sqlite_engine(settings)
        elif settings.is_postgresql:
            _engine = _create_postgresql_engine(settings)
        elif settings.is_mysql:
            _engine = _create_mysql_engine(settings)
        else:
            raise ValueError(f"不支持的数据库类型: {settings.DATABASE_URL}")
    
    return _engine


def _create_sqlite_engine(settings):
    """创建SQLite引擎"""
    # 确保数据库目录存在
    if settings.database_path:
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # 启用外键约束
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
    
    return engine


def _create_postgresql_engine(settings):
    """创建PostgreSQL引擎"""
    # PostgreSQL需要额外的驱动
    try:
        import psycopg2
    except ImportError:
        raise ImportError(
            "使用PostgreSQL需要安装psycopg2: pip install psycopg2-binary"
        )
    
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        echo=False
    )
    
    return engine


def _create_mysql_engine(settings):
    """创建MySQL引擎"""
    # MySQL需要额外的驱动
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
    except ImportError:
        raise ImportError(
            "使用MySQL需要安装pymysql: pip install pymysql"
        )
    
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        echo=False
    )
    
    return engine


def get_session_factory():
    """获取会话工厂（单例）"""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _session_factory


def get_db() -> Generator:
    """获取数据库会话（用于依赖注入）"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """初始化数据库，创建所有表"""
    from database.models import (
        Stock, DailyPrice, FinancialReport, TechnicalIndicator,
        IndexPrice, AttributionResult, TradeRecord, DataUpdateLog
    )
    
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    
    settings = get_settings()
    print(f"✅ 数据库初始化完成 ({settings.database_type})")
    return True


def check_database_connection() -> bool:
    """检查数据库连接是否正常"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def get_database_info() -> dict:
    """获取数据库信息"""
    settings = get_settings()
    engine = get_engine()
    
    info = {
        "type": settings.database_type,
        "url": settings.DATABASE_URL if settings.is_sqlite else "***",
        "tables": []
    }
    
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        info["tables"] = inspector.get_table_names()
    except Exception as e:
        info["error"] = str(e)
    
    return info


if __name__ == "__main__":
    # 测试数据库连接
    settings = get_settings()
    print(f"数据库类型: {settings.database_type}")
    print(f"数据库URL: {settings.DATABASE_URL if settings.is_sqlite else '***'}")
    
    if check_database_connection():
        print("数据库连接正常")
        info = get_database_info()
        print(f"已创建表: {', '.join(info['tables'])}")
    else:
        print("数据库连接失败")
