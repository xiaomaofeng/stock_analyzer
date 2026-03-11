"""
数据库迁移管理脚本

使用方法:
    python scripts/db_migrate.py init          # 初始化迁移环境
    python scripts/db_migrate.py migrate       # 创建迁移脚本
    python scripts/db_migrate.py upgrade       # 升级到最新版本
    python scripts/db_migrate.py downgrade     # 回滚一个版本
    python scripts/db_migrate.py history       # 查看迁移历史
    python scripts/db_migrate.py current       # 查看当前版本
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command
from config import get_settings


def get_alembic_config():
    """获取Alembic配置"""
    settings = get_settings()
    
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    
    return alembic_cfg


def init_migration():
    """初始化迁移环境"""
    settings = get_settings()
    
    # 创建迁移目录
    migrations_dir = Path("database/migrations")
    migrations_dir.mkdir(parents=True, exist_ok=True)
    
    # 对于SQLite，直接使用init_db初始化
    if settings.is_sqlite:
        print("SQLite数据库使用init_db.py初始化")
        from scripts.init_db import init_database_tables
        init_database_tables()
        return
    
    # PostgreSQL/MySQL使用Alembic
    alembic_cfg = get_alembic_config()
    
    try:
        command.init(alembic_cfg, "database/migrations")
        print("✅ 迁移环境初始化完成")
    except Exception as e:
        print(f"迁移环境已存在或出错: {e}")


def create_migration(message: str = "auto migration"):
    """创建迁移脚本"""
    settings = get_settings()
    
    if settings.is_sqlite:
        print("SQLite数据库无需迁移，使用init_db.py同步表结构")
        from database import init_database
        init_database()
        return
    
    alembic_cfg = get_alembic_config()
    
    try:
        command.revision(alembic_cfg, autogenerate=True, message=message)
        print(f"✅ 迁移脚本创建完成: {message}")
    except Exception as e:
        print(f"❌ 创建迁移失败: {e}")


def upgrade_database(revision: str = "head"):
    """升级数据库"""
    settings = get_settings()
    
    if settings.is_sqlite:
        print("SQLite数据库使用init_db.py同步")
        from database import init_database
        init_database()
        return
    
    alembic_cfg = get_alembic_config()
    
    try:
        command.upgrade(alembic_cfg, revision)
        print(f"✅ 数据库升级完成: {revision}")
    except Exception as e:
        print(f"❌ 升级失败: {e}")


def downgrade_database(revision: str = "-1"):
    """回滚数据库"""
    settings = get_settings()
    
    if settings.is_sqlite:
        print("SQLite数据库不支持回滚，请备份后重建")
        return
    
    alembic_cfg = get_alembic_config()
    
    try:
        command.downgrade(alembic_cfg, revision)
        print(f"✅ 数据库回滚完成: {revision}")
    except Exception as e:
        print(f"❌ 回滚失败: {e}")


def show_history():
    """显示迁移历史"""
    settings = get_settings()
    
    if settings.is_sqlite:
        print("SQLite数据库无迁移历史")
        return
    
    alembic_cfg = get_alembic_config()
    
    try:
        command.history(alembic_cfg)
    except Exception as e:
        print(f"❌ 查看历史失败: {e}")


def show_current():
    """显示当前版本"""
    settings = get_settings()
    
    if settings.is_sqlite:
        print(f"SQLite数据库: {settings.DATABASE_URL}")
        return
    
    alembic_cfg = get_alembic_config()
    
    try:
        command.current(alembic_cfg)
    except Exception as e:
        print(f"❌ 查看当前版本失败: {e}")


def main():
    parser = argparse.ArgumentParser(description='数据库迁移管理')
    parser.add_argument(
        'action',
        choices=['init', 'migrate', 'upgrade', 'downgrade', 'history', 'current'],
        help='迁移操作'
    )
    parser.add_argument('--message', '-m', default='auto migration', help='迁移说明')
    parser.add_argument('--revision', '-r', default='head', help='目标版本')
    
    args = parser.parse_args()
    
    # 显示数据库信息
    settings = get_settings()
    print(f"数据库类型: {settings.database_type}")
    print(f"数据库URL: {settings.DATABASE_URL if settings.is_sqlite else '***'}")
    print("-" * 50)
    
    if args.action == 'init':
        init_migration()
    elif args.action == 'migrate':
        create_migration(args.message)
    elif args.action == 'upgrade':
        upgrade_database(args.revision)
    elif args.action == 'downgrade':
        downgrade_database(args.revision)
    elif args.action == 'history':
        show_history()
    elif args.action == 'current':
        show_current()


if __name__ == "__main__":
    main()
