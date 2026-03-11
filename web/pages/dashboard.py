# -*- coding: utf-8 -*-
"""仪表盘 - 数据概览 + 数据管理"""
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
from datetime import datetime, timedelta
from loguru import logger

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator
from collectors import AKShareCollector
from processors import TechnicalCalculator
from processors.calculators import save_indicators_to_db

# 配置日志
logger.add("logs/dashboard.log", rotation="10 MB", encoding="utf-8")

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
        'data_management': '⚙️ 数据管理',
        'delete_stock': '🗑️ 删除股票数据',
        'delete_btn': '删除选中',
        'delete_success': '✅ 已删除 {} 的数据',
        'delete_error': '❌ 删除 {} 失败: {}',
        'update_stock': '🔄 更新股票数据',
        'update_btn': '更新数据',
        'update_all': '更新全部',
        'update_success': '✅ {} 数据更新成功，共 {} 条',
        'update_failed': '❌ {} 更新失败: {}',
        'select_stock': '选择股票',
        'update_date_range': '更新天数',
        'force_update': '强制更新（覆盖现有数据）',
        'operations': '操作',
        'refresh': '🔄 刷新',
        'logs': '📜 操作日志',
        'delete_confirm_title': '⚠️ 确认删除',
        'delete_confirm_msg': '确定要删除以下 {} 只股票的所有数据吗？此操作不可恢复！',
        'cancel': '取消',
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
        'data_management': '⚙️ Data Management',
        'delete_stock': '🗑️ Delete Stock Data',
        'delete_btn': 'Delete Selected',
        'delete_success': '✅ Deleted data for {}',
        'delete_error': '❌ Failed to delete {}: {}',
        'update_stock': '🔄 Update Stock Data',
        'update_btn': 'Update',
        'update_all': 'Update All',
        'update_success': '✅ {} updated successfully, {} records',
        'update_failed': '❌ {} update failed: {}',
        'select_stock': 'Select Stock',
        'update_date_range': 'Days to Update',
        'force_update': 'Force Update (overwrite existing)',
        'operations': 'Operations',
        'refresh': '🔄 Refresh',
        'logs': '📜 Operation Logs',
        'delete_confirm_title': '⚠️ Confirm Delete',
        'delete_confirm_msg': 'Delete {} stock(s)? This cannot be undone!',
        'cancel': 'Cancel',
    }
}

lang = st.session_state.get('lang', 'zh')
t = lambda k: I18N[lang].get(k, k)

st.title(t('title'))

# 初始化 session state
if 'delete_codes' not in st.session_state:
    st.session_state['delete_codes'] = []
if 'show_delete_confirm' not in st.session_state:
    st.session_state['show_delete_confirm'] = False
if 'logs' not in st.session_state:
    st.session_state['logs'] = []

# 添加日志函数
def add_log(operation, details, status="INFO"):
    """添加操作日志"""
    log_entry = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'operation': operation,
        'details': details,
        'status': status
    }
    st.session_state['logs'].insert(0, log_entry)
    logger.info(f"[{operation}] {details} - {status}")

def delete_stocks(codes):
    """删除股票数据 - 返回成功删除的列表"""
    db = get_session_factory()()
    deleted = []
    errors = []
    
    try:
        for code in codes:
            try:
                logger.info(f"开始删除股票: {code}")
                
                # 检查股票是否存在
                stock = db.query(Stock).filter(Stock.stock_code == code).first()
                if not stock:
                    logger.warning(f"股票 {code} 不存在")
                    errors.append(f"{code}: 股票不存在")
                    continue
                
                # 删除价格数据
                price_count = db.query(DailyPrice).filter(DailyPrice.stock_code == code).count()
                db.query(DailyPrice).filter(DailyPrice.stock_code == code).delete()
                logger.info(f"删除 {code} 价格数据: {price_count} 条")
                
                # 删除技术指标
                indicator_count = db.query(TechnicalIndicator).filter(TechnicalIndicator.stock_code == code).count()
                db.query(TechnicalIndicator).filter(TechnicalIndicator.stock_code == code).delete()
                logger.info(f"删除 {code} 指标数据: {indicator_count} 条")
                
                # 删除股票信息
                db.query(Stock).filter(Stock.stock_code == code).delete()
                logger.info(f"删除股票 {code} 基本信息")
                
                db.commit()
                deleted.append(code)
                add_log("DELETE", f"删除股票 {code}, 价格数据 {price_count} 条, 指标 {indicator_count} 条", "SUCCESS")
                
            except Exception as e:
                db.rollback()
                error_msg = str(e)
                logger.error(f"删除 {code} 失败: {error_msg}")
                errors.append(f"{code}: {error_msg}")
                add_log("DELETE", f"删除股票 {code} 失败: {error_msg}", "ERROR")
    finally:
        db.close()
    
    return deleted, errors

def update_stock_data(code, days=252, force=False):
    """更新股票数据"""
    db = get_session_factory()()
    try:
        logger.info(f"开始更新股票 {code}, 天数={days}, 强制={force}")
        
        collector = AKShareCollector(request_delay=0.5)
        calculator = TechnicalCalculator()
        
        # 获取新数据
        end = datetime.now()
        start = end - timedelta(days=days * 2)
        df = collector.get_daily_prices(code, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        
        if df.empty:
            logger.warning(f"{code}: 未获取到数据")
            return False, "未获取到数据"
        
        # 如果强制更新，先删除旧数据
        if force:
            db.query(DailyPrice).filter(DailyPrice.stock_code == code).delete()
            db.query(TechnicalIndicator).filter(TechnicalIndicator.stock_code == code).delete()
            db.commit()
            logger.info(f"{code}: 强制更新，已删除旧数据")
        
        # 保存新数据
        new_count = 0
        for _, row in df.iterrows():
            existing = db.query(DailyPrice).filter(
                DailyPrice.stock_code == code,
                DailyPrice.trade_date == row['trade_date']
            ).first()
            
            if not existing or force:
                if existing and force:
                    db.delete(existing)
                
                dp = DailyPrice(
                    stock_code=code,
                    trade_date=row['trade_date'],
                    open_price=float(row['open_price']) if pd.notna(row['open_price']) else None,
                    high_price=float(row['high_price']) if pd.notna(row['high_price']) else None,
                    low_price=float(row['low_price']) if pd.notna(row['low_price']) else None,
                    close_price=float(row['close_price']) if pd.notna(row['close_price']) else None,
                    volume=int(row['volume']) if pd.notna(row['volume']) else None,
                    amount=float(row['amount']) if 'amount' in row and pd.notna(row['amount']) else None,
                    change_pct=float(row['change_pct']) if 'change_pct' in row and pd.notna(row['change_pct']) else None,
                    turnover_rate=float(row['turnover_rate']) if 'turnover_rate' in row and pd.notna(row['turnover_rate']) else None,
                )
                db.merge(dp)
                new_count += 1
        
        db.commit()
        
        # 更新技术指标
        df_calc = calculator.calculate_all(df)
        save_indicators_to_db(code, df_calc, db)
        
        add_log("UPDATE", f"更新股票 {code}, 新增 {new_count} 条数据", "SUCCESS")
        logger.info(f"{code}: 更新成功，新增 {new_count} 条")
        return True, f"新增 {new_count} 条数据"
        
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"{code}: 更新失败 - {error_msg}")
        add_log("UPDATE", f"更新股票 {code} 失败: {error_msg}", "ERROR")
        return False, error_msg
    finally:
        db.close()

# 获取数据库连接
db = get_session_factory()()

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
    
    # 获取所有股票（每次重新查询）
    stocks = db.query(Stock).all()
    stock_options = {f"{s.stock_code} - {s.stock_name}": s.stock_code for s in stocks}
    
    # 数据管理区域
    st.divider()
    st.subheader(t('data_management'))
    
    tab1, tab2, tab3 = st.tabs([t('update_stock'), t('delete_stock'), t('logs')])
    
    # === 更新数据 Tab ===
    with tab1:
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        
        with col1:
            selected_for_update = st.multiselect(
                t('select_stock'),
                options=list(stock_options.keys()),
                default=[],
                key='update_select'
            )
        
        with col2:
            update_days = st.number_input(
                t('update_date_range'),
                min_value=30,
                max_value=1000,
                value=252,
                step=30,
                key='update_days'
            )
        
        with col3:
            force_update = st.checkbox(
                t('force_update'),
                value=False,
                key='force_update'
            )
        
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            update_btn = st.button(t('update_btn'), type="primary", use_container_width=True)
            update_all_btn = st.button(t('update_all'), use_container_width=True)
        
        if update_btn and selected_for_update:
            codes_to_update = [stock_options[name] for name in selected_for_update if name in stock_options]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, code in enumerate(codes_to_update):
                progress = (i + 1) / len(codes_to_update)
                progress_bar.progress(progress)
                status_text.text(f"[{i+1}/{len(codes_to_update)}] 更新 {code}...")
                
                success, msg = update_stock_data(code, update_days, force_update)
                if success:
                    st.success(t('update_success').format(code, msg))
                else:
                    st.error(t('update_failed').format(code, msg))
            
            progress_bar.empty()
            status_text.empty()
            st.button(t('refresh'), on_click=lambda: st.rerun())
        
        elif update_all_btn and stocks:
            codes_to_update = [s.stock_code for s in stocks]
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, code in enumerate(codes_to_update):
                progress = (i + 1) / len(codes_to_update)
                progress_bar.progress(progress)
                status_text.text(f"[{i+1}/{len(codes_to_update)}] 更新 {code}...")
                
                success, msg = update_stock_data(code, update_days, force_update)
                if not success:
                    st.error(t('update_failed').format(code, msg))
            
            progress_bar.empty()
            status_text.empty()
            st.success("所有股票更新完成！")
            st.button(t('refresh'), on_click=lambda: st.rerun())
    
    # === 删除数据 Tab ===
    with tab2:
        col1, col2 = st.columns([4, 1])
        
        with col1:
            selected_for_delete = st.multiselect(
                t('select_stock'),
                options=list(stock_options.keys()),
                default=[],
                key='delete_select'
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            delete_btn = st.button(t('delete_btn'), type="secondary", use_container_width=True)
        
        # 显示删除确认对话框
        if delete_btn and selected_for_delete:
            st.session_state['delete_codes'] = [stock_options[name] for name in selected_for_delete if name in stock_options]
            st.session_state['show_delete_confirm'] = True
        
        if st.session_state['show_delete_confirm'] and st.session_state['delete_codes']:
            codes = st.session_state['delete_codes']
            
            with st.expander(t('delete_confirm_title'), expanded=True):
                st.warning(t('delete_confirm_msg').format(len(codes)))
                st.write("**将要删除的股票：**")
                for code in codes:
                    st.write(f"- {code}")
                
                col_confirm1, col_confirm2 = st.columns(2)
                
                with col_confirm1:
                    if st.button("✅ " + t('delete_confirm_title'), type="primary", key='confirm_delete'):
                        with st.spinner("删除中..."):
                            deleted, errors = delete_stocks(codes)
                        
                        st.session_state['delete_codes'] = []
                        st.session_state['show_delete_confirm'] = False
                        
                        if deleted:
                            st.success(f"✅ 成功删除 {len(deleted)} 只股票: {', '.join(deleted)}")
                        if errors:
                            for error in errors:
                                st.error(f"❌ {error}")
                        
                        # 强制刷新页面
                        st.info("3秒后自动刷新...")
                        import time
                        time.sleep(1)
                        st.rerun()
                
                with col_confirm2:
                    if st.button(t('cancel'), key='cancel_delete'):
                        st.session_state['delete_codes'] = []
                        st.session_state['show_delete_confirm'] = False
                        add_log("CANCEL", "取消删除操作", "INFO")
                        st.rerun()
    
    # === 日志 Tab ===
    with tab3:
        st.subheader(t('logs'))
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ 清空日志", use_container_width=True):
                st.session_state['logs'] = []
                st.rerun()
        
        with col2:
            if st.button("🔄 刷新日志", use_container_width=True):
                st.rerun()
        
        if st.session_state['logs']:
            log_df = pd.DataFrame(st.session_state['logs'])
            st.dataframe(log_df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无操作日志")
        
        # 显示文件日志路径
        st.caption("📁 详细日志文件: `logs/dashboard.log`")
    
    # 股票列表
    st.divider()
    st.subheader(t('stock_list'))
    
    # 重新查询股票列表（确保最新）
    db.close()
    db = get_session_factory()()
    stocks = db.query(Stock).all()
    
    if stocks:
        stock_data = []
        for s in stocks:
            latest = db.query(DailyPrice).filter(
                DailyPrice.stock_code == s.stock_code
            ).order_by(DailyPrice.trade_date.desc()).first()
            
            price_count = db.query(DailyPrice).filter(
                DailyPrice.stock_code == s.stock_code
            ).count()
            
            stock_data.append({
                t('code'): s.stock_code,
                t('name'): s.stock_name or '-',
                t('price'): f"{latest.close_price:.3f}" if latest else '-',
                t('change'): f"{latest.change_pct:.2f}%" if latest and latest.change_pct else '-',
                t('date'): latest.trade_date if latest else '-',
                '数据条数': price_count
            })
        
        if stock_data:
            st.dataframe(pd.DataFrame(stock_data), use_container_width=True, hide_index=True)
            
            # 添加一个显式的刷新按钮
            if st.button("🔄 刷新股票列表", use_container_width=True):
                st.rerun()
        else:
            st.info(t('no_data'))
    else:
        st.info(t('no_data'))
        
except Exception as e:
    logger.error(f"页面错误: {str(e)}")
    st.error(f"Error: {e}")
finally:
    db.close()
