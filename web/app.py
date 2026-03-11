# -*- coding: utf-8 -*-
"""
股票分析系统 - Web主入口 (Streamlit)
"""
import sys
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="股票分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 股票分析系统")

st.markdown("""
### 欢迎使用股票分析系统

**功能导航：**
- **🔍 股票查询** - 输入代码获取数据，自动保存到数据库，计算技术指标
- **🔄 策略回测** - 均线/RSI/MACD策略回测，查看净值曲线和交易记录

请从左侧导航栏选择功能。
""")

# 检查数据库
from config import get_session_factory
from database.models import Stock

try:
    db = get_session_factory()()
    stock_count = db.query(Stock).count()
    db.close()
    st.success(f"✅ 数据库连接正常 | 已存储 {stock_count} 只股票")
except Exception as e:
    st.error(f"❌ 数据库连接失败: {e}")
    st.info("首次使用请运行: python scripts/init_db.py")
