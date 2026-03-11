"""
Streamlit主应用 - 增强版
支持股票代码查询、自动数据获取、实时分析
"""
import sys
from pathlib import Path
import os

# 设置项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# 页面配置
st.set_page_config(
    page_title="股票分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入页面模块
from pages import dashboard, stock_viewer, screener, backtest, stock_query

# 侧边栏导航
st.sidebar.title("📊 股票分析系统")

page = st.sidebar.radio(
    "选择功能",
    ["📈 仪表盘", "🔍 股票查询", "📊 个股分析", "🔎 股票筛选", "🔄 回测"],
    index=0
)

# 根据选择显示不同页面
if page == "📈 仪表盘":
    dashboard.show()
elif page == "🔍 股票查询":
    stock_query.show()
elif page == "📊 个股分析":
    stock_viewer.show()
elif page == "🔎 股票筛选":
    screener.show()
elif page == "🔄 回测":
    backtest.show()

# 侧边栏底部信息
st.sidebar.markdown("---")
st.sidebar.info("""
**使用说明**
1. 🔍 股票查询 - 输入代码自动获取数据
2. 📊 个股分析 - 查看详细技术指标
3. 数据自动保存到本地数据库
""")

# 显示系统状态
st.sidebar.markdown("---")
st.sidebar.caption(f"工作目录: {PROJECT_ROOT}")
