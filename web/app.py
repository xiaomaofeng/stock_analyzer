# -*- coding: utf-8 -*-
"""
股票分析系统 - Web主入口 (Streamlit)
支持多语言: 中文 / English
"""
import sys
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# 多语言支持
I18N = {
    'zh': {
        'title': '📈 股票分析系统',
        'welcome': '欢迎使用股票分析系统',
        'features': '功能导航',
        'stock_query': '🔍 股票查询 - 获取数据、技术指标、趋势分析',
        'dashboard': '📊 仪表盘 - 数据库统计、股票列表',
        'stock_viewer': '📈 个股分析 - K线图、详细指标',
        'backtest': '🔄 策略回测 - 均线/RSI/MACD策略',
        'screener': '🔎 股票筛选 - 多条件筛选',
        'select_func': '请从左侧导航栏选择功能',
        'db_ok': '✅ 数据库连接正常 | 已存储 {} 只股票',
        'db_error': '❌ 数据库连接失败: {}',
        'first_use': '首次使用请运行: python scripts/init_db.py',
        'language': '🌐 语言 / Language',
    },
    'en': {
        'title': '📈 Stock Analyzer',
        'welcome': 'Welcome to Stock Analyzer',
        'features': 'Features',
        'stock_query': '🔍 Stock Query - Data & Technical Analysis',
        'dashboard': '📊 Dashboard - Database Statistics',
        'stock_viewer': '📈 Stock Viewer - Charts & Indicators',
        'backtest': '🔄 Backtest - MA/RSI/MACD Strategies',
        'screener': '🔎 Screener - Multi-condition Filter',
        'select_func': 'Please select a feature from the sidebar',
        'db_ok': '✅ Database Connected | {} stocks stored',
        'db_error': '❌ Database Error: {}',
        'first_use': 'First time? Run: python scripts/init_db.py',
        'language': '🌐 Language / 语言',
    }
}

# 初始化语言设置
if 'lang' not in st.session_state:
    st.session_state.lang = 'zh'

def t(key):
    """翻译函数"""
    return I18N[st.session_state.lang].get(key, key)

st.set_page_config(
    page_title="Stock Analyzer" if st.session_state.lang == 'en' else "股票分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 侧边栏语言切换
with st.sidebar:
    lang = st.selectbox(
        t('language'),
        options=['zh', 'en'],
        format_func=lambda x: '🇨🇳 中文' if x == 'zh' else '🇺🇸 English',
        index=0 if st.session_state.lang == 'zh' else 1
    )
    if lang != st.session_state.lang:
        st.session_state.lang = lang
        st.rerun()

st.title(t('title'))

st.markdown(f"### {t('welcome')}")

st.markdown(f"**{t('features')}：**")
st.markdown(f"- {t('stock_query')}")
st.markdown(f"- {t('dashboard')}")
st.markdown(f"- {t('stock_viewer')}")
st.markdown(f"- {t('backtest')}")
st.markdown(f"- {t('screener')}")

st.info(t('select_func'))

# 检查数据库
from config import get_session_factory
from database.models import Stock

try:
    db = get_session_factory()()
    stock_count = db.query(Stock).count()
    db.close()
    st.success(t('db_ok').format(stock_count))
except Exception as e:
    st.error(t('db_error').format(e))
    st.info(t('first_use'))
