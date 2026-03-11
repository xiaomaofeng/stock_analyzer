"""仪表盘页面 - 简化版"""
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import func

from config import get_session_factory, get_settings
from database.models import Stock, DailyPrice, TechnicalIndicator


def show():
    """显示仪表盘"""
    st.title("📈 仪表盘")
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 统计卡片
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            stock_count = db.query(Stock).count()
            st.metric("股票总数", f"{stock_count}")
        
        with col2:
            price_count = db.query(DailyPrice).count()
            st.metric("日线数据", f"{price_count:,}")
        
        with col3:
            indicator_count = db.query(TechnicalIndicator).count()
            st.metric("指标数据", f"{indicator_count:,}")
        
        with col4:
            from datetime import datetime
            latest_date = db.query(func.max(DailyPrice.trade_date)).scalar()
            if latest_date:
                days_ago = (datetime.now().date() - latest_date).days
                st.metric("最新数据", f"{latest_date}", f"{days_ago}天前")
        
        st.divider()
        
        # 快捷查询
        st.subheader("🔍 快捷股票查询")
        st.markdown("输入股票代码，快速获取数据并分析")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            quick_code = st.text_input("股票代码", placeholder="如: 159892, 000001, 600519", key="quick_search")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("查询", use_container_width=True) and quick_code:
                st.session_state['search_code'] = quick_code
                st.switch_page("pages/stock_query.py")
        
        st.divider()
        
        # 最近热门股票
        st.subheader("📊 数据库中的股票")
        
        stocks = db.query(Stock).limit(20).all()
        if stocks:
            stock_data = []
            for s in stocks:
                # 获取最新价格
                latest = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == s.stock_code
                ).order_by(DailyPrice.trade_date.desc()).first()
                
                if latest:
                    stock_data.append({
                        '代码': s.stock_code,
                        '名称': s.stock_name,
                        '最新价': latest.close_price,
                        '涨跌幅': f"{latest.change_pct:.2f}%" if latest.change_pct else "-",
                        '更新日期': latest.trade_date
                    })
            
            if stock_data:
                st.dataframe(pd.DataFrame(stock_data), use_container_width=True, hide_index=True)
        
        # 使用说明
        st.divider()
        st.info("""
        **使用提示**
        1. 点击左侧 🔍 **股票查询** 进行股票分析
        2. 输入股票代码后系统自动获取数据并计算指标
        3. 数据会自动保存到本地数据库，下次查询更快
        """)
        
    except Exception as e:
        st.error(f"加载数据失败: {e}")
        st.info("提示: 如果是首次使用，请先通过 🔍 股票查询 添加股票数据")
    finally:
        db.close()
