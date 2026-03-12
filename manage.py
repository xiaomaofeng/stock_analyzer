#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票分析系统 - 统一管理脚本
支持 Windows / macOS / Linux
"""
import sys
import os
import subprocess
import shutil
import argparse
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.resolve()

# 虚拟环境路径
VENV_PATH = PROJECT_ROOT / "venv"
PYTHON_BIN = VENV_PATH / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
STREAMLIT_BIN = VENV_PATH / ("Scripts/streamlit.exe" if sys.platform == "win32" else "bin/streamlit")

# 颜色输出
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    END = "\033[0m"

def print_color(msg, color=Colors.BLUE):
    """彩色输出"""
    if sys.platform == "win32":
        # Windows 简化输出
        print(msg)
    else:
        print(f"{color}{msg}{Colors.END}")

def run_cmd(cmd, cwd=None, check=True):
    """运行命令"""
    print_color(f">>> {' '.join(cmd)}", Colors.YELLOW)
    try:
        result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print_color(f"Error: {e}", Colors.RED)
        if e.stderr:
            print(e.stderr)
        sys.exit(1)

def check_venv():
    """检查虚拟环境"""
    if not VENV_PATH.exists():
        print_color("虚拟环境不存在，正在创建...", Colors.YELLOW)
        subprocess.run([sys.executable, "-m", "venv", str(VENV_PATH)], check=True)
        print_color("虚拟环境创建完成", Colors.GREEN)

def install_deps():
    """安装依赖"""
    check_venv()
    print_color("Installing dependencies...", Colors.BLUE)
    
    pip_cmd = str(PYTHON_BIN) if PYTHON_BIN.exists() else "python"
    run_cmd([pip_cmd, "-m", "pip", "install", "--upgrade", "pip"])
    run_cmd([pip_cmd, "-m", "pip", "install", "-r", "requirements.txt"])
    
    print_color("Dependencies installed successfully!", Colors.GREEN)

def start_web(port=8501):
    """启动Web版本"""
    check_venv()
    print_color(f"Starting Web Server on port {port}...", Colors.BLUE)
    print_color(f"Open browser: http://localhost:{port}", Colors.GREEN)
    
    # 设置环境变量
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    streamlit_cmd = str(STREAMLIT_BIN) if STREAMLIT_BIN.exists() else "streamlit"
    cmd = [
        streamlit_cmd, "run", "web/app.py",
        f"--server.port={port}",
        "--server.runOnSave=false"
    ]
    
    subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)

def start_desktop():
    """启动Desktop版本"""
    check_venv()
    print_color("Starting Desktop Application...", Colors.BLUE)
    
    python_cmd = str(PYTHON_BIN) if PYTHON_BIN.exists() else "python"
    run_cmd([python_cmd, "desktop/main.py"])

def clean():
    """清理缓存和临时文件"""
    print_color("Cleaning cache files...", Colors.BLUE)
    
    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/.pytest_cache",
        "build",
        "dist",
        "*.egg-info"
    ]
    
    for pattern in patterns:
        for path in PROJECT_ROOT.glob(pattern):
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                print(f"  Removed: {path}")
    
    print_color("Cleanup complete!", Colors.GREEN)

def build_web():
    """构建Web版本（Docker等）"""
    print_color("Building Web version...", Colors.BLUE)
    # 可以添加Docker构建等
    print_color("Web build not implemented yet", Colors.YELLOW)

def build_desktop():
    """构建Desktop可执行文件"""
    check_venv()
    print_color("Building Desktop executable...", Colors.BLUE)
    
    python_cmd = str(PYTHON_BIN) if PYTHON_BIN.exists() else "python"
    
    if sys.platform == "win32":
        # Windows构建
        output_name = "股票分析系统.exe"
        icon = "NONE"
    elif sys.platform == "darwin":
        # macOS构建
        output_name = "StockAnalyzer"
        icon = "NONE"
    else:
        # Linux构建
        output_name = "stock-analyzer"
        icon = "NONE"
    
    cmd = [
        python_cmd, "-m", "PyInstaller",
        "--name", output_name.replace(".exe", ""),
        "--windowed",
        "--onefile",
        f"--icon={icon}",
        "--add-data", f"data{os.pathsep}data",
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--hidden-import=sqlalchemy",
        "--hidden-import=akshare",
        "--hidden-import=scipy",
        "--hidden-import=pyqtgraph",
        "desktop/main.py"
    ]
    
    run_cmd(cmd)
    print_color(f"Build complete! Output: dist/{output_name}", Colors.GREEN)

def init_db():
    """初始化数据库"""
    check_venv()
    print_color("Initializing database...", Colors.BLUE)
    
    python_cmd = str(PYTHON_BIN) if PYTHON_BIN.exists() else "python"
    run_cmd([python_cmd, "-c", "from scripts.init_db import init_database_tables; init_database_tables()"])
    print_color("Database initialized!", Colors.GREEN)

def test():
    """运行测试"""
    check_venv()
    print_color("Running tests...", Colors.BLUE)
    
    python_cmd = str(PYTHON_BIN) if PYTHON_BIN.exists() else "python"
    run_cmd([python_cmd, "-m", "pytest", "-v"], check=False)

def main():
    parser = argparse.ArgumentParser(
        description="股票分析系统管理脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python manage.py install     # 安装依赖
  python manage.py web         # 启动Web版本
  python manage.py desktop     # 启动Desktop版本
  python manage.py build       # 构建Desktop版本
  python manage.py clean       # 清理缓存
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # install
    p_install = subparsers.add_parser("install", help="安装依赖")
    
    # web
    p_web = subparsers.add_parser("web", help="启动Web版本")
    p_web.add_argument("--port", type=int, default=8501, help="端口号 (默认: 8501)")
    
    # desktop
    p_desktop = subparsers.add_parser("desktop", help="启动Desktop版本")
    
    # build
    p_build = subparsers.add_parser("build", help="构建Desktop可执行文件")
    
    # clean
    p_clean = subparsers.add_parser("clean", help="清理缓存文件")
    
    # init-db
    p_init = subparsers.add_parser("init-db", help="初始化数据库")
    
    # test
    p_test = subparsers.add_parser("test", help="运行测试")
    
    args = parser.parse_args()
    
    if args.command == "install":
        install_deps()
    elif args.command == "web":
        start_web(args.port)
    elif args.command == "desktop":
        start_desktop()
    elif args.command == "build":
        build_desktop()
    elif args.command == "clean":
        clean()
    elif args.command == "init-db":
        init_db()
    elif args.command == "test":
        test()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
