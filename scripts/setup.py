"""
项目初始化脚本

一键初始化整个项目

使用方法:
    python scripts/setup.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
import os


def setup_directories():
    """创建必要的目录"""
    dirs = [
        'data/raw',
        'data/processed',
        'data/cache',
        'logs',
    ]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        logger.info(f"创建目录: {d}")


def setup_database():
    """初始化数据库"""
    from scripts.init_db import init_database_tables
    init_database_tables()


def create_env_file():
    """创建环境变量文件"""
    env_file = Path('.env')
    
    if env_file.exists():
        logger.info("环境变量文件已存在，跳过创建")
        return
    
    env_content = """# 数据库配置 (默认SQLite)
DATABASE_URL=sqlite:///./data/stock_db.sqlite

# 日志级别
LOG_LEVEL=INFO

# AKShare配置
AKSHARE_REQUEST_DELAY=0.5
AKSHARE_MAX_RETRIES=3

# 回测配置
INITIAL_CAPITAL=1000000.0
COMMISSION_RATE=0.0003
SLIPPAGE=0.0001
"""
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    logger.info("创建环境变量文件: .env")


def print_usage():
    """打印使用说明"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                  股票数据库系统初始化完成                      ║
╚══════════════════════════════════════════════════════════════╝

快速开始:

1. 导入股票数据:
   python scripts/import_stock_data.py --code 000001 --start 2023-01-01

2. 批量导入:
   python scripts/import_stock_data.py --batch --file stock_list.txt

3. 计算技术指标:
   python scripts/calc_indicators.py --code 000001

4. 启动Web界面:
   cd web && streamlit run app.py

5. 每日自动更新:
   python scheduler/jobs.py

常用脚本:
- 查询数据: python scripts/query_data.py --code 000001
- 趋势分析: python scripts/analyze_stock.py --code 000001 --trend
- 风险分析: python scripts/analyze_stock.py --code 000001 --risk
- 健康检查: python scheduler/monitor.py

更多帮助请查看 README.md
""")


def main():
    """主函数"""
    print("正在初始化股票数据库系统...\n")
    
    # 设置日志
    logger.add("logs/setup_{time}.log", rotation="1 day")
    
    try:
        setup_directories()
        setup_database()
        create_env_file()
        
        print_usage()
        
        logger.success("初始化完成！")
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise


if __name__ == "__main__":
    main()
