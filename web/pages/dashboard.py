# -*- coding: utf-8 -*-
"""仪表盘 - 数据概览"""
import sys
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
from sqlalchemy import func
from datetime import datetime

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator

st.set_page_config(page_title="Dashboard | 仪表盘", layout="wide")

I18N = {
    'zh': {
        'title': '📊 仪表盘',
        'overview': '数据概览',
        'total_stocks': '股票总数',
        'total_prices': '价格数据',
        'total_indicators': '指标数据',
        'latest_date': '最新数据',
        'days_ago': '{}天前',
        'today': '今天',
        'stock_list': '📋 股票列表',
        'code': '代码',
        'name': '名称',
        'price': '最新价',
        'change': '涨跌幅',
        'date': '日期',
        'no_data': '暂无数据',
    },
    'en': {
        'title': '📊 Dashboard',
        'overview': 'Overview',
        'total_stocks': 'Total Stocks',
        'total_prices': 'Price Records',
        'total_indicators': 'Indicators',
        'latest_date': 'Latest Data',
        'days_ago': '{} days ago',
        'today': 'Today',
        'stock_list': '📋 Stock List',
        'code': 'Code',
        'name': 'Name',
        'price': 'Price',
        'change': 'Change',
        'date': 'Date',
        'no_data': 'No data available',
    }
}

lang = st.session_state.get('lang', 'zh')
t = lambda k: I18N[lang].get(k, k)

st.title(t('title'))

SessionLocal = get_session_factory()
db = SessionLocal()

try:
    # 统计卡片
    st.subheader(t('overview'))
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        stock_count = db.query(Stock).count()
        st.metric(t('total_stocks'), f"{stock_count}")
    
    with col2:
        price_count = db.query(DailyPrice).count()
        st.metric(t('total_prices'), f"{price_count:,}")
    
    with col3:
        indicator_count = db.query(TechnicalIndicator).count()
        st.metric(t('total_indicators'), f"{indicator_count:,}")
    
    with col4:
        latest_date = db.query(func.max(DailyPrice.trade_date)).scalar()
        if latest_date:
            days_ago = (datetime.now().date() - latest_date).days
            if days_ago == 0:
                label = t('today')
            else:
                label = t('days_ago').format(days_ago)
            st.metric(t('latest_date'), f"{latest_date}", label)
        else:
            st.metric(t('latest_date'), "-")
    
    # 股票列表
    st.divider()
    st.subheader(t('stock_list'))
    
    stocks = db.query(Stock).limit(50).all()
    if stocks:
        stock_data = []
        for s in stocks:
            latest = db.query(DailyPrice).filter(
                DailyPrice.stock_code == s.stock_code
            ).order_by(DailyPrice.trade_date.desc()).first()
            
            if latest:
                stock_data.append({
                    t('code'): s.stock_code,
                    t('name'): s.stock_name,
                    t('price'): f"{latest.close_price:.3f}",
                    t('change'): f"{latest.change_pct:.2f}%" if latest.change_pct else "-",
                    t('date'): latest.trade_date
                })
        
        if stock_data:
            st.dataframe(pd.DataFrame(stock_data), use_container_width=True, hide_index=True)
        else:
            st.info(t('no_data'))
    else:
        st.info(t('no_data'))
        
except Exception as e:
    st.error(f"Error: {e}")
finally:
    db.close()
