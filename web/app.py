"""
股票分析系统 - 主入口

Streamlit 会自动识别 pages/ 目录下的文件作为子页面
"""
import sys
from pathlib import Path
import os

# 动态检测项目根目录
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

# 主页内容
st.title("📈 股票分析系统")

st.markdown("""
### 欢迎使用股票分析系统

本系统提供以下功能：

- **🔍 股票查询** (stock_query) - 输入代码获取数据，自动保存到数据库
- **📊 仪表盘** (dashboard) - 查看数据库统计和股票列表  
- **📈 个股分析** (stock_viewer) - K线图、技术指标、风险分析
- **🔄 策略回测** (backtest) - 均线/RSI/MACD策略回测
- **🔎 股票筛选** (screener) - 多条件筛选股票

请从左侧导航栏选择功能。
""")

# 检查数据库连接
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
