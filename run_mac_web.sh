#!/bin/bash
# Mac Web 版启动脚本

cd "$(dirname "$0")"

echo "🚀 启动股票分析系统 Web 版..."
echo "📍 本地地址: http://localhost:8501"
echo ""

# 设置 Python 路径
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# 启动 Streamlit
python3 -m streamlit run web/app.py --server.headless true --server.port 8501
