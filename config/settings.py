"""全局配置管理 - 支持跨平台和共享数据库"""
import os
import platform
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类 - 支持Windows/Mac/Linux和多种数据库"""
    
    # 项目路径 (跨平台)
    PROJECT_ROOT: Path = Path(__file__).parent.parent.absolute()
    
    # 平台检测
    PLATFORM: str = Field(default_factory=lambda: platform.system().lower())
    
    # 数据库配置 - 支持多种数据库
    # SQLite (本地开发): sqlite:///./data/stock_db.sqlite
    # PostgreSQL (共享): postgresql://user:pass@host:5432/dbname
    # MySQL (共享): mysql://user:pass@host:3306/dbname
    DATABASE_URL: str = Field(
        default="sqlite:///./data/stock_db.sqlite",
        description="数据库连接URL，支持SQLite/PostgreSQL/MySQL"
    )
    
    # 数据库连接池配置 (PostgreSQL/MySQL)
    DB_POOL_SIZE: int = Field(default=5, description="连接池大小")
    DB_MAX_OVERFLOW: int = Field(default=10, description="最大溢出连接")
    DB_POOL_TIMEOUT: int = Field(default=30, description="连接超时(秒)")
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="日志格式"
    )
    LOG_PATH: Path = Field(default=None, description="日志路径")
    
    # AKShare配置
    AKSHARE_REQUEST_DELAY: float = Field(default=0.5, description="请求间隔(秒)")
    AKSHARE_MAX_RETRIES: int = Field(default=3, description="最大重试次数")
    AKSHARE_TIMEOUT: int = Field(default=30, description="请求超时(秒)")
    
    # 数据更新配置
    UPDATE_START_TIME: str = Field(default="09:00", description="更新开始时间")
    UPDATE_END_TIME: str = Field(default="17:00", description="更新结束时间")
    
    # 回测配置
    INITIAL_CAPITAL: float = Field(default=1000000.0, description="初始资金")
    COMMISSION_RATE: float = Field(default=0.0003, description="手续费率")
    SLIPPAGE: float = Field(default=0.0001, description="滑点")
    
    # GitHub/GitLab配置 (敏感信息不要提交到版本控制)
    GIT_REMOTE_URL: str = Field(default="", description="Git远程仓库URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 设置跨平台日志路径
        if self.LOG_PATH is None:
            self.LOG_PATH = self.PROJECT_ROOT / "logs"
    
    @property
    def is_windows(self) -> bool:
        """是否Windows系统"""
        return self.PLATFORM == "windows"
    
    @property
    def is_mac(self) -> bool:
        """是否Mac系统"""
        return self.PLATFORM == "darwin"
    
    @property
    def is_linux(self) -> bool:
        """是否Linux系统"""
        return self.PLATFORM == "linux"
    
    @property
    def is_sqlite(self) -> bool:
        """是否使用SQLite数据库"""
        return self.DATABASE_URL.startswith("sqlite")
    
    @property
    def is_postgresql(self) -> bool:
        """是否使用PostgreSQL数据库"""
        return self.DATABASE_URL.startswith("postgresql") or self.DATABASE_URL.startswith("postgres")
    
    @property
    def is_mysql(self) -> bool:
        """是否使用MySQL数据库"""
        return self.DATABASE_URL.startswith("mysql")
    
    @property
    def database_type(self) -> str:
        """获取数据库类型"""
        if self.is_sqlite:
            return "sqlite"
        elif self.is_postgresql:
            return "postgresql"
        elif self.is_mysql:
            return "mysql"
        return "unknown"
    
    @property
    def database_path(self) -> Path:
        """获取SQLite数据库文件路径"""
        if self.is_sqlite:
            # 提取sqlite:///后面的路径
            db_path = self.DATABASE_URL.replace("sqlite:///", "")
            if db_path.startswith("./"):
                db_path = db_path[2:]
            elif db_path.startswith("/"):
                db_path = db_path[1:]
            return self.PROJECT_ROOT / db_path
        return None
    
    def get_data_dir(self) -> Path:
        """获取数据目录 (跨平台)"""
        return self.PROJECT_ROOT / "data"
    
    def get_cache_dir(self) -> Path:
        """获取缓存目录"""
        return self.get_data_dir() / "cache"
    
    def get_raw_data_dir(self) -> Path:
        """获取原始数据目录"""
        return self.get_data_dir() / "raw"
    
    def get_processed_data_dir(self) -> Path:
        """获取处理后数据目录"""
        return self.get_data_dir() / "processed"
    
    def ensure_directories(self):
        """确保所有必要目录存在"""
        dirs = [
            self.get_data_dir(),
            self.get_raw_data_dir(),
            self.get_processed_data_dir(),
            self.get_cache_dir(),
            self.LOG_PATH
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


def print_config_info():
    """打印配置信息 (用于调试)"""
    settings = get_settings()
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    系统配置信息                               ║
╚══════════════════════════════════════════════════════════════╝

平台信息:
  操作系统: {settings.PLATFORM}
  项目路径: {settings.PROJECT_ROOT}

数据库配置:
  类型: {settings.database_type}
  URL: {settings.DATABASE_URL if settings.is_sqlite else '***'}

路径配置:
  数据目录: {settings.get_data_dir()}
  日志目录: {settings.LOG_PATH}

AKShare配置:
  请求延迟: {settings.AKSHARE_REQUEST_DELAY}s
  最大重试: {settings.AKSHARE_MAX_RETRIES}次

═══════════════════════════════════════════════════════════════
""")


if __name__ == "__main__":
    print_config_info()
