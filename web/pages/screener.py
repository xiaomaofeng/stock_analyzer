# -*- coding: utf-8 -*-
"""股票筛选器 - 多条件筛选"""
import sys
from pathlib import Path
import os

# 设置项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import streamlit as st
import pandas as pd
from sqlalchemy import func, and_

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator


def show():
    """显示筛选器页面"""
    st.title("🔍 股票筛选器")
    
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        # 筛选条件
        st.sidebar.header("筛选条件")
        
        # 价格范围
        price_range = st.sidebar.slider(
            "价格范围",
            min_value=0.0,
            max_value=500.0,
            value=(0.0, 200.0),
            step=1.0
        )
        
        # 涨跌幅
        change_range = st.sidebar.slider(
            "今日涨跌幅 (%)",
            min_value=-20.0,
            max_value=20.0,
            value=(-10.0, 10.0),
            step=0.5
        )
        
        # 换手率
        turnover_range = st.sidebar.slider(
            "换手率 (%)",
            min_value=0.0,
            max_value=50.0,
            value=(0.0, 20.0),
            step=0.5
        )
        
        # 技术指标筛选
        st.sidebar.header("技术指标")
        
        use_ma_filter = st.sidebar.checkbox("均线多头排列")
        use_macd_filter = st.sidebar.checkbox("MACD金叉")
        use_rsi_filter = st.sidebar.checkbox("RSI超卖 (RSI<30)")
        use_volume_filter = st.sidebar.checkbox("放量上涨")
        
        # 执行筛选
        latest_date = db.query(func.max(DailyPrice.trade_date)).scalar()
        
        if latest_date:
            query = db.query(
                DailyPrice.stock_code,
                Stock.stock_name,
                DailyPrice.close_price,
                DailyPrice.change_pct,
                DailyPrice.turnover_rate,
                DailyPrice.volume,
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
            
            # 应用技术指标筛选
            if use_ma_filter:
                query = query.filter(
                    TechnicalIndicator.ma5 > TechnicalIndicator.ma10,
                    TechnicalIndicator.ma10 > TechnicalIndicator.ma20
                )
            
            if use_macd_filter:
                query = query.filter(
                    TechnicalIndicator.macd_dif > TechnicalIndicator.macd_dea
                )
            
            if use_rsi_filter:
                query = query.filter(
                    TechnicalIndicator.rsi12 < 30
                )
            
            # 执行查询
            results = query.limit(100).all()
            
            if results:
                df = pd.DataFrame(results, columns=[
                    '代码', '名称', '最新价', '涨跌幅', '换手率', '成交量',
                    'MACD_DIF', 'MACD_DEA', 'RSI12', 'MA5', 'MA10', 'MA20'
                ])
                
                # 格式化显示
                df['涨跌幅'] = df['涨跌幅'].apply(lambda x: f"{x:+.2f}%")
                df['换手率'] = df['换手率'].apply(lambda x: f"{x:.2f}%")
                df['成交量'] = df['成交量'].apply(lambda x: f"{x/10000:.0f}万")
                
                # 添加技术信号列
                df['均线多头'] = df.apply(lambda row: 
                    '✓' if row['MA5'] and row['MA10'] and row['MA20'] and 
                    row['MA5'] > row['MA10'] > row['MA20'] else '', axis=1)
                
                df['MACD金叉'] = df.apply(lambda row: 
                    '✓' if row['MACD_DIF'] and row['MACD_DEA'] and 
                    row['MACD_DIF'] > row['MACD_DEA'] else '', axis=1)
                
                df['RSI超卖'] = df.apply(lambda row: 
                    '✓' if row['RSI12'] and row['RSI12'] < 30 else '', axis=1)
                
                # 显示结果
                st.success(f"找到 {len(df)} 只符合条件的股票")
                
                display_cols = ['代码', '名称', '最新价', '涨跌幅', '换手率', '均线多头', 'MACD金叉', 'RSI超卖']
                st.dataframe(df[display_cols], use_container_width=True)
                
                # 导出按钮
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="导出CSV",
                    data=csv,
                    file_name=f"stock_screener_{latest_date}.csv",
                    mime="text/csv"
                )
            else:
                st.info("未找到符合条件的股票，请调整筛选条件")
        else:
            st.warning("暂无数据，请先导入股票数据")
            
    except Exception as e:
        st.error(f"筛选失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


# 执行页面
show()
