"""
Streamlit主应用 - 简化版
"""
import sys
from pathlib import Path
import os

# 动态检测项目根目录（web/app.py -> 项目根目录）
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(
    page_title="股票分析系统",
    page_icon="📈",
    layout="wide"
)

# 简单导入，避免复杂逻辑
from config import get_session_factory
from database.models import Stock, DailyPrice

# 检查数据库连接
try:
    db = get_session_factory()()
    stock_count = db.query(Stock).count()
    db.close()
    db_ok = True
except Exception as e:
    db_ok = False
    error_msg = str(e)

st.title("📈 股票分析系统")

if not db_ok:
    st.error(f"数据库连接失败: {error_msg}")
    st.info("尝试重新初始化数据库...")
    try:
        from scripts.init_db import init_database_tables
        init_database_tables()
        st.success("数据库初始化完成，请刷新页面")
    except Exception as e2:
        st.error(f"初始化失败: {e2}")
    st.stop()

st.success(f"系统正常 | 数据库中有 {stock_count} 只股票")

# 简单导航
page = st.sidebar.radio("功能", ["股票查询", "仪表盘"])

if page == "股票查询":
    st.header("🔍 股票查询")
    
    stock_code = st.text_input("股票代码", value="159892")
    
    if st.button("查询") and stock_code:
        from collectors import AKShareCollector
        
        with st.spinner(f"获取 {stock_code}..."):
            try:
                collector = AKShareCollector()
                end = datetime.now()
                start = end - timedelta(days=365)
                
                df = collector.get_daily_prices(
                    stock_code,
                    start.strftime('%Y-%m-%d'),
                    end.strftime('%Y-%m-%d')
                )
                
                if not df.empty:
                    st.success(f"获取成功，共 {len(df)} 条数据")
                    st.line_chart(df.set_index('trade_date')['close_price'])
                    
                    # 保存到数据库 - 使用INSERT OR IGNORE模式避免重复
                    db = get_session_factory()()
                    
                    # 获取已存在的日期
                    existing = db.query(DailyPrice.trade_date).filter(
                        DailyPrice.stock_code == stock_code
                    ).all()
                    existing_dates = {d[0] for d in existing}
                    
                    # 保存股票信息
                    stock = db.query(Stock).filter_by(stock_code=stock_code).first()
                    if not stock:
                        stock = Stock(
                            stock_code=stock_code,
                            stock_name=stock_code,
                            exchange="A"
                        )
                        db.add(stock)
                    
                    # 保存价格数据（跳过已存在的）
                    added_count = 0
                    for _, row in df.iterrows():
                        trade_date = row['trade_date']
                        if trade_date not in existing_dates:
                            dp = DailyPrice(
                                stock_code=stock_code,
                                trade_date=trade_date,
                                open_price=float(row['open_price']),
                                high_price=float(row['high_price']),
                                low_price=float(row['low_price']),
                                close_price=float(row['close_price']),
                                volume=int(row['volume'])
                            )
                            db.add(dp)
                            added_count += 1
                    
                    db.commit()
                    db.close()
                    
                    if added_count > 0:
                        st.success(f"新增 {added_count} 条数据到数据库")
                    else:
                        st.info("数据已存在，无需重复保存")
                else:
                    st.error("无数据")
                    
            except Exception as e:
                st.error(f"失败: {e}")

else:
    st.header("📊 仪表盘")
    st.info("系统运行正常")
    
    try:
        db = get_session_factory()()
        stocks = db.query(Stock).all()
        st.write(f"已有股票: {len(stocks)}")
        for s in stocks:
            st.write(f"- {s.stock_code}")
        db.close()
    except Exception as e:
        st.error(f"查询失败: {e}")
