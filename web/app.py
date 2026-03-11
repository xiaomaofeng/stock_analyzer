"""
Streamlit主应用

启动命令: streamlit run web/app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

# 页面配置
st.set_page_config(
    page_title="股票分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入页面模块
from pages import dashboard, stock_viewer, screener, backtest

# 侧边栏导航
st.sidebar.title("📊 股票分析系统")

page = st.sidebar.radio(
    "选择功能",
    ["仪表盘", "个股分析", "股票筛选", "回测"],
    index=0
)

# 根据选择显示不同页面
if page == "仪表盘":
    dashboard.show()
elif page == "个股分析":
    stock_viewer.show()
elif page == "股票筛选":
    screener.show()
elif page == "回测":
    backtest.show()

# 侧边栏底部信息
st.sidebar.markdown("---")
st.sidebar.info("""
**使用说明**
1. 先在命令行导入数据
2. 然后在此查看分析
3. 支持趋势、风险、归因分析
""")
