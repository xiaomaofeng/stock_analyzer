# -*- coding: utf-8 -*-
"""
依赖安装脚本 - 一键安装所有依赖
"""
import subprocess
import sys

dependencies = [
    # 核心依赖
    "PySide6>=6.5.0",
    "pyqtgraph>=0.13.0",
    
    # 数据处理
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    
    # 数据库
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    
    # 数据采集
    "akshare>=1.12.0",
    
    # 技术指标
    "ta-lib>=0.4.28",
    
    # 分析
    "scipy>=1.10.0",
    
    # 工具
    "python-dotenv>=1.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "loguru>=0.7.0",
]

def install():
    print("=" * 50)
    print("股票分析系统 - 依赖安装")
    print("=" * 50)
    
    for dep in dependencies:
        print(f"\n安装: {dep}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "-q"])
            print(f"✅ 成功")
        except Exception as e:
            print(f"❌ 失败: {e}")
    
    print("\n" + "=" * 50)
    print("安装完成！可以运行: python desktop/main.py")
    print("=" * 50)

if __name__ == "__main__":
    install()
