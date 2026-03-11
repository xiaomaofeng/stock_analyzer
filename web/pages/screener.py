# -*- coding: utf-8 -*-
"""股票筛选器"""
import sys
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
from sqlalchemy import func, and_

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator

st.set_page_config(page_title="Screener | 股票筛选", layout="wide")

I18N = {
    'zh': {
        'title': '🔎 股票筛选器',
        'filters': '筛选条件',
        'price_range': '价格范围',
        'change_range': '涨跌幅范围 (%)',
        'turnover_range': '换手率范围 (%)',
        'technical': '技术指标',
        'ma_bullish': '均线多头排列 (MA5>MA10>MA20)',
        'macd_golden': 'MACD金叉 (DIF>DEA)',
        'rsi_oversold': 'RSI超卖 (RSI<30)',
        'volume_increase': '放量上涨',
        'results': '筛选结果',
        'found': '找到 {} 只股票',
        'no_results': '未找到符合条件的股票',
        'export': '导出CSV',
        'code': '代码',
        'name': '名称',
        'price': '最新价',
        'change': '涨跌幅',
        'turnover': '换手率',
        'ma_bull': '均线多头',
        'macd_cross': 'MACD金叉',
        'rsi_low': 'RSI超卖',
    },
    'en': {
        'title': '🔎 Stock Screener',
        'filters': 'Filters',
        'price_range': 'Price Range',
        'change_range': 'Change Range (%)',
        'turnover_range': 'Turnover Range (%)',
        'technical': 'Technical Indicators',
        'ma_bullish': 'MA Bullish (MA5>MA10>MA20)',
        'macd_golden': 'MACD Golden Cross (DIF>DEA)',
        'rsi_oversold': 'RSI Oversold (RSI<30)',
        'volume_increase': 'Volume Increase',
        'results': 'Results',
        'found': 'Found {} stocks',
        'no_results': 'No stocks match the criteria',
        'export': 'Export CSV',
        'code': 'Code',
        'name': 'Name',
        'price': 'Price',
        'change': 'Change',
        'turnover': 'Turnover',
        'ma_bull': 'MA Bull',
        'macd_cross': 'MACD Cross',
        'rsi_low': 'RSI Low',
    }
}

lang = st.session_state.get('lang', 'zh')
t = lambda k: I18N[lang].get(k, k)

st.title(t('title'))

SessionLocal = get_session_factory()
db = SessionLocal()

try:
    with st.sidebar:
        st.header(t('filters'))
        
        # 价格范围
        price_range = st.slider(t('price_range'), 0.0, 500.0, (0.0, 200.0), 1.0)
        
        # 涨跌幅
        change_range = st.slider(t('change_range'), -20.0, 20.0, (-10.0, 10.0), 0.5)
        
        # 换手率
        turnover_range = st.slider(t('turnover_range'), 0.0, 50.0, (0.0, 20.0), 0.5)
        
        st.divider()
        st.header(t('technical'))
        
        use_ma = st.checkbox(t('ma_bullish'))
        use_macd = st.checkbox(t('macd_golden'))
        use_rsi = st.checkbox(t('rsi_oversold'))
        use_volume = st.checkbox(t('volume_increase'))
        
        run_btn = st.button('Run Screener' if lang == 'en' else '开始筛选', type='primary', use_container_width=True)
    
    if run_btn:
        latest_date = db.query(func.max(DailyPrice.trade_date)).scalar()
        
        if latest_date:
            query = db.query(
                DailyPrice.stock_code,
                Stock.stock_name,
                DailyPrice.close_price,
                DailyPrice.change_pct,
                DailyPrice.turnover_rate,
                TechnicalIndicator.macd_dif,
                TechnicalIndicator.macd_dea,
                TechnicalIndicator.rsi12,
                TechnicalIndicator.ma5,
                TechnicalIndicator.ma10,
                TechnicalIndicator.ma20,
            ).join(
                Stock, DailyPrice.stock_code == Stock.stock_code
            ).outerjoin(
                TechnicalIndicator,
                and_(
                    DailyPrice.stock_code == TechnicalIndicator.stock_code,
                    DailyPrice.trade_date == TechnicalIndicator.trade_date
                )
            ).filter(
                DailyPrice.trade_date == latest_date,
                DailyPrice.close_price >= price_range[0],
                DailyPrice.close_price <= price_range[1],
                DailyPrice.change_pct >= change_range[0],
                DailyPrice.change_pct <= change_range[1],
                DailyPrice.turnover_rate >= turnover_range[0],
                DailyPrice.turnover_rate <= turnover_range[1]
            )
            
            # 技术指标筛选
            if use_ma:
                query = query.filter(
                    TechnicalIndicator.ma5 > TechnicalIndicator.ma10,
                    TechnicalIndicator.ma10 > TechnicalIndicator.ma20
                )
            
            if use_macd:
                query = query.filter(
                    TechnicalIndicator.macd_dif > TechnicalIndicator.macd_dea
                )
            
            if use_rsi:
                query = query.filter(
                    TechnicalIndicator.rsi12 < 30
                )
            
            results = query.limit(100).all()
            
            st.subheader(t('results'))
            
            if results:
                st.success(t('found').format(len(results)))
                
                df = pd.DataFrame(results, columns=[
                    t('code'), t('name'), t('price'), t('change'), t('turnover'),
                    'MACD_DIF', 'MACD_DEA', 'RSI12', 'MA5', 'MA10', 'MA20'
                ])
                
                # 格式化
                df[t('change')] = df[t('change')].apply(lambda x: f"{x:+.2f}%")
                df[t('turnover')] = df[t('turnover')].apply(lambda x: f"{x:.2f}%")
                
                # 添加信号列
                df[t('ma_bull')] = df.apply(lambda row: '✓' if row['MA5'] and row['MA10'] and row['MA20'] and row['MA5'] > row['MA10'] > row['MA20'] else '', axis=1)
                df[t('macd_cross')] = df.apply(lambda row: '✓' if row['MACD_DIF'] and row['MACD_DEA'] and row['MACD_DIF'] > row['MACD_DEA'] else '', axis=1)
                df[t('rsi_low')] = df.apply(lambda row: '✓' if row['RSI12'] and row['RSI12'] < 30 else '', axis=1)
                
                display_cols = [t('code'), t('name'), t('price'), t('change'), t('turnover'), t('ma_bull'), t('macd_cross'), t('rsi_low')]
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
                
                # 导出
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(t('export'), csv, f"screener_{latest_date}.csv", "text/csv")
            else:
                st.info(t('no_results'))
        else:
            st.error("No data available")
            
except Exception as e:
    st.error(f"Error: {e}")
finally:
    db.close()
