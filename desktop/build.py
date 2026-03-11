# -*- coding: utf-8 -*-
"""
打包脚本 - 使用 PyInstaller
支持 Windows(.exe) 和 macOS(.app/.dmg)
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DESKTOP_DIR = Path(__file__).parent.resolve()
BUILD_DIR = DESKTOP_DIR / "build"
DIST_DIR = DESKTOP_DIR / "dist"


def clean():
    """清理构建目录"""
    print("清理构建目录...")
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  删除 {d}")


def build_windows():
    """构建 Windows exe"""
    print("\n构建 Windows 可执行文件...")
    
    cmd = [
        "pyinstaller",
        "--name=股票分析系统",
        "--windowed",  # 无控制台窗口
        "--onefile",   # 单文件
        "--icon=NONE",
        f"--distpath={DIST_DIR}/windows",
        f"--workpath={BUILD_DIR}/windows",
        f"--specpath={BUILD_DIR}",
        # 包含数据文件
        f"--add-data={PROJECT_ROOT}/data;data",
        # 隐藏导入
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--hidden-import=sqlalchemy",
        "--hidden-import=akshare",
        "--hidden-import=scipy",
        "--hidden-import=pyqtgraph",
        # 主程序
        f"{DESKTOP_DIR}/main.py"
    ]
    
    subprocess.run(cmd, check=True)
    print(f"✅ Windows 构建完成: {DIST_DIR}/windows/股票分析系统.exe")


def build_macos():
    """构建 macOS app"""
    print("\n构建 macOS 应用...")
    
    cmd = [
        "pyinstaller",
        "--name=StockAnalyzer",
        "--windowed",
        "--onefile",
        f"--distpath={DIST_DIR}/macos",
        f"--workpath={BUILD_DIR}/macos",
        f"--specpath={BUILD_DIR}",
        # macOS 特定选项
        "--osx-bundle-identifier=com.yourcompany.stockanalyzer",
        f"--add-data={PROJECT_ROOT}/data:data",
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--hidden-import=sqlalchemy",
        "--hidden-import=akshare",
        "--hidden-import=scipy",
        "--hidden-import=pyqtgraph",
        f"{DESKTOP_DIR}/main.py"
    ]
    
    subprocess.run(cmd, check=True)
    print(f"✅ macOS 构建完成: {DIST_DIR}/macos/StockAnalyzer.app")


def create_dmg():
    """创建 macOS DMG 安装包（需要在 macOS 上运行）"""
    print("\n创建 DMG 安装包...")
    
    app_path = DIST_DIR / "macos" / "StockAnalyzer.app"
    dmg_path = DIST_DIR / "macos" / "StockAnalyzer.dmg"
    
    # 使用 create-dmg 工具
    cmd = [
        "create-dmg",
        "--volname", "StockAnalyzer",
        "--window-pos", "200", "120",
        "--window-size", "800", "400",
        "--icon-size", "100",
        "--app-drop-link", "600", "185",
        str(dmg_path),
        str(app_path)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ DMG 创建完成: {dmg_path}")
    except FileNotFoundError:
        print("⚠️ 未找到 create-dmg，跳过 DMG 创建")
        print("   你可以手动下载: brew install create-dmg")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="构建股票分析系统桌面应用")
    parser.add_argument("--platform", choices=["windows", "macos", "all"], 
                       default="all", help="目标平台")
    parser.add_argument("--clean", action="store_true", help="清理构建目录")
    args = parser.parse_args()
    
    if args.clean:
        clean()
        return
    
    # 检查 pyinstaller
    try:
        subprocess.run(["pyinstaller", "--version"], capture_output=True, check=True)
    except FileNotFoundError:
        print("❌ 请先安装 pyinstaller: pip install pyinstaller")
        sys.exit(1)
    
    # 根据平台构建
    current_platform = sys.platform
    
    if args.platform == "windows" or (args.platform == "all" and current_platform == "win32"):
        build_windows()
    
    if args.platform == "macos" or (args.platform == "all" and current_platform == "darwin"):
        build_macos()
        create_dmg()
    
    print("\n✨ 构建完成！")
    print(f"输出目录: {DIST_DIR}")


if __name__ == "__main__":
    main()
