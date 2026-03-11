"""仪表盘页面"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import func

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator


def show():
    """显示仪表盘"""
    st.title("📊 仪表盘")
    
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
        
        # 最近热门股票（按换手率）
        st.subheader("🔥 最近活跃股票")
        
        latest_date = db.query(func.max(DailyPrice.trade_date)).scalar()
        if latest_date:
            hot_stocks = db.query(
                DailyPrice.stock_code,
                Stock.stock_name,
                DailyPrice.close_price,
                DailyPrice.change_pct,
                DailyPrice.turnover_rate
            ).join(Stock, DailyPrice.stock_code == Stock.stock_code).filter(
                DailyPrice.trade_date == latest_date
            ).order_by(DailyPrice.turnover_rate.desc()).limit(10).all()
            
            if hot_stocks:
                df_hot = pd.DataFrame(hot_stocks, columns=[
                    '代码', '名称', '最新价', '涨跌幅', '换手率'
                ])
                df_hot['涨跌幅'] = df_hot['涨跌幅'].apply(lambda x: f"{x:+.2f}%")
                df_hot['换手率'] = df_hot['换手率'].apply(lambda x: f"{x:.2f}%")
                st.dataframe(df_hot, use_container_width=True)
        
        # 市场概览
        st.subheader("📈 市场概览")
        
        # 涨跌分布
        if latest_date:
            distribution = db.query(
                func.case(
                    (DailyPrice.change_pct > 7, '涨停 (>7%)'),
                    (DailyPrice.change_pct > 3, '大涨 (3-7%)'),
                    (DailyPrice.change_pct > 0, '上涨 (0-3%)'),
                    (DailyPrice.change_pct == 0, '平盘'),
                    (DailyPrice.change_pct > -3, '下跌 (-3-0%)'),
                    (DailyPrice.change_pct > -7, '大跌 (-7--3%)'),
                    else='跌停 (<-7%)'
                ).label('range'),
                func.count(DailyPrice.id).label('count')
            ).filter(
                DailyPrice.trade_date == latest_date
            ).group_by('range').all()
            
            if distribution:
                df_dist = pd.DataFrame(distribution)
                
                fig = px.pie(
                    df_dist,
                    values='count',
                    names='range',
                    title='涨跌分布',
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # 最近更新
        st.subheader("📝 最近更新")
        from database.models import DataUpdateLog
        
        recent_logs = db.query(DataUpdateLog).order_by(
            DataUpdateLog.created_at.desc()
        ).limit(5).all()
        
        if recent_logs:
            logs_data = []
            for log in recent_logs:
                logs_data.append({
                    '时间': log.created_at.strftime('%Y-%m-%d %H:%M'),
                    '表名': log.table_name,
                    '类型': log.update_type,
                    '记录数': log.record_count,
                    '状态': log.status
                })
            st.dataframe(pd.DataFrame(logs_data), use_container_width=True)
        
    except Exception as e:
        st.error(f"加载数据失败: {e}")
    finally:
        db.close()
