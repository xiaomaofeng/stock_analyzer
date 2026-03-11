# -*- coding: utf-8 -*-
"""
Windows EXE 打包脚本
"""
import subprocess
import sys
import shutil
from pathlib import Path

def build():
    print("开始打包 Windows EXE...")
    
    # 清理旧构建
    dist_dir = Path("dist")
    build_dir = Path("build")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=股票分析系统",
        "--windowed",
        "--onefile",
        "--icon=NONE",
        "--add-data=../data;data",
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--hidden-import=sqlalchemy",
        "--hidden-import=akshare",
        "--hidden-import=scipy",
        "--hidden-import=pyqtgraph",
        "main.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ 打包完成!")
        print("输出: dist/股票分析系统.exe")
    except Exception as e:
        print(f"\n❌ 打包失败: {e}")

if __name__ == "__main__":
    build()
