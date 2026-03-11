#!/bin/bash
# Mac 桌面版启动脚本

cd "$(dirname "$0")"

# 设置 Python 路径
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# 启动桌面应用
python3 desktop/main.py
