# -*- coding: utf-8 -*-
"""
股票分析系统 - Desktop Application
统一入口：股票查询 + 策略回测 + 现代化UI
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QStackedWidget,
    QFrame, QGridLayout, QStatusBar, QMenuBar, QMenu,
    QFileDialog, QMessageBox, QScrollArea, QTableWidget, 
    QTableWidgetItem, QHeaderView, QSpinBox, QDoubleSpinBox,
    QDateEdit, QSplitter, QTabWidget, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal, QDate
from PySide6.QtGui import QAction, QFont
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator
from collectors import AKShareCollector
from processors import TechnicalCalculator
from processors.calculators import save_indicators_to_db
from analysis import TrendAnalyzer
from analysis.risk_metrics import RiskMetrics

from desktop.styles.modern_theme import MODERN_STYLE, COLORS
from desktop.widgets.candlestick_chart import CandlestickChart, BacktestChart


class DataFetchThread(QThread):
    """数据获取线程"""
    status = Signal(str)
    finished_signal = Signal(bool, str)
    data_ready = Signal(object, object)
    
    def __init__(self, stock_code, days):
        super().__init__()
        self.stock_code = stock_code
        self.days = days
        
    def run(self):
        try:
            self.status.emit(f"获取 {self.stock_code} 数据中...")
            SessionLocal = get_session_factory()
            db = SessionLocal()
            
            try:
                # 检查本地数据
                existing = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == self.stock_code
                ).count()
                
                # 如果没有数据，从网络获取
                if existing == 0:
                    self.status.emit("从网络获取数据...")
                    collector = AKShareCollector(request_delay=0.5)
                    stock_info = collector.get_stock_info(self.stock_code)
                    
                    # 保存股票信息
                    stock = Stock(
                        stock_code=self.stock_code,
                        stock_name=stock_info.get('stock_name', self.stock_code) if stock_info else self.stock_code,
                        exchange=collector._get_exchange(self.stock_code),
                    )
                    db.merge(stock)
                    db.commit()
                    
                    # 获取历史数据
                    end = datetime.now()
                    start = end - timedelta(days=self.days * 2)
                    df = collector.get_daily_prices(
                        self.stock_code,
                        start.strftime('%Y-%m-%d'),
                        end.strftime('%Y-%m-%d')
                    )
                    
                    if df.empty:
                        self.finished_signal.emit(False, "无法获取数据，请检查股票代码")
                        return
                    
                    # 保存到数据库
                    for idx, row in df.iterrows():
                        dp = DailyPrice(
                            stock_code=self.stock_code,
                            trade_date=row['trade_date'],
                            open_price=float(row['open_price']) if pd.notna(row['open_price']) else None,
                            high_price=float(row['high_price']) if pd.notna(row['high_price']) else None,
                            low_price=float(row['low_price']) if pd.notna(row['low_price']) else None,
                            close_price=float(row['close_price']) if pd.notna(row['close_price']) else None,
                            volume=int(row['volume']) if pd.notna(row['volume']) else None,
                        )
                        db.merge(dp)
                    
                    db.commit()
                    
                    # 计算技术指标
                    self.status.emit("计算技术指标...")
                    calculator = TechnicalCalculator()
                    df_calc = calculator.calculate_all(df)
                    save_indicators_to_db(self.stock_code, df_calc, db)
                
                # 从数据库读取数据
                prices = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == self.stock_code
                ).order_by(DailyPrice.trade_date.desc()).limit(self.days).all()
                
                indicators = db.query(TechnicalIndicator).filter(
                    TechnicalIndicator.stock_code == self.stock_code
                ).order_by(TechnicalIndicator.trade_date.desc()).first()
                
                # 转换为DataFrame
                df = pd.DataFrame([{
                    'trade_date': p.trade_date,
                    'open_price': float(p.open_price) if p.open_price else 0,
                    'high_price': float(p.high_price) if p.high_price else 0,
                    'low_price': float(p.low_price) if p.low_price else 0,
                    'close_price': float(p.close_price) if p.close_price else 0,
                    'volume': p.volume or 0,
                    'change_pct': float(p.change_pct) if p.change_pct else 0,
                } for p in reversed(prices)])
                
                self.data_ready.emit(df, indicators)
                self.finished_signal.emit(True, f"已加载 {len(df)} 条数据")
                
            finally:
                db.close()
        except Exception as e:
            import traceback
            self.finished_signal.emit(False, f"{str(e)}\n{traceback.format_exc()}")


class BacktestThread(QThread):
    """回测线程"""
    status = Signal(str)
    finished_signal = Signal(bool, str, object)
    
    def __init__(self, stock_code, start_date, end_date, strategy_name, initial_capital, commission):
        super().__init__()
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_name = strategy_name
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run(self):
        try:
            self.status.emit("加载回测数据...")
            from backtest.engine import BacktestEngine, BacktestConfig
            from backtest.strategies import MAStrategy, RSIStrategy, MACDStrategy
            
            SessionLocal = get_session_factory()
            db = SessionLocal()
            
            try:
                prices = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == self.stock_code,
                    DailyPrice.trade_date >= self.start_date,
                    DailyPrice.trade_date <= self.end_date
                ).order_by(DailyPrice.trade_date).all()
                
                if len(prices) < 60:
                    self.finished_signal.emit(False, "数据不足，至少需要60个交易日", None)
                    return
                
                # 构建DataFrame
                df = pd.DataFrame([{
                    'trade_date': p.trade_date,
                    'open_price': float(p.open_price) if p.open_price else 0,
                    'high_price': float(p.high_price) if p.high_price else 0,
                    'low_price': float(p.low_price) if p.low_price else 0,
                    'close_price': float(p.close_price) if p.close_price else 0,
                    'volume': p.volume or 0,
                } for p in prices])
                
                # 计算技术指标
                calculator = TechnicalCalculator()
                df = calculator.calculate_all(df)
                
                # 配置回测
                config = BacktestConfig(
                    initial_capital=self.initial_capital,
                    commission_rate=self.commission
                )
                engine = BacktestEngine(config)
                
                # 选择策略
                if self.strategy_name == "均线交叉":
                    strategy = MAStrategy(short_period=5, long_period=20)
                elif self.strategy_name == "RSI超买超卖":
                    strategy = RSIStrategy(overbought=70, oversold=30)
                else:  # MACD金叉死叉
                    strategy = MACDStrategy()
                
                engine.set_strategy(strategy)
                engine.load_data(df)
                
                self.status.emit("运行回测...")
                results = engine.run()
                
                self.finished_signal.emit(True, "回测完成", results)
                
            finally:
                db.close()
        except Exception as e:
            import traceback
            self.finished_signal.emit(False, f"{str(e)}\n{traceback.format_exc()}", None)


class MetricCard(QFrame):
    """指标卡片"""
    def __init__(self, title, value="-", unit="", color=None, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 16, 16, 16)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(self.title_label)
        
        value_layout = QHBoxLayout()
        self.value_label = QLabel(value)
        text_color = color if color else COLORS['text']
        self.value_label.setStyleSheet(f"color: {text_color}; font-size: 24px; font-weight: 700;")
        value_layout.addWidget(self.value_label)
        
        if unit:
            self.unit_label = QLabel(unit)
            self.unit_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            value_layout.addWidget(self.unit_label)
        
        value_layout.addStretch()
        layout.addLayout(value_layout)
        
        self.setMinimumWidth(160)
        self.setMaximumWidth(220)
    
    def set_value(self, value, color=None):
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 700;")


class SidebarButton(QPushButton):
    """侧边栏按钮"""
    def __init__(self, text, icon, parent=None):
        super().__init__(parent)
        self.setText(f"{icon}  {text}")
        self.setCheckable(True)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                color: white;
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("股票分析系统")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        self.current_df = None
        self.current_indicators = None
        self.stock_code = None
        
        self.init_ui()
        self.setStyleSheet(MODERN_STYLE)
        self.check_database()
    
    def init_ui(self):
        """初始化界面"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 侧边栏
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # 内容区
        content = self.create_content()
        main_layout.addWidget(content, 1)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        self.create_menu()
    
    def create_sidebar(self):
        """创建侧边栏"""
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"background-color: {COLORS['surface']}; border-right: 1px solid {COLORS['border']};")
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)
        
        # 标题
        title = QLabel("📈 股票分析")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 18px; font-weight: 700; padding: 8px;")
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # 导航按钮
        self.nav_buttons = []
        
        self.btn_query = SidebarButton("股票查询", "🔍")
        self.btn_query.setChecked(True)
        self.btn_query.clicked.connect(lambda: self.switch_page(0))
        layout.addWidget(self.btn_query)
        self.nav_buttons.append(self.btn_query)
        
        self.btn_backtest = SidebarButton("策略回测", "📊")
        self.btn_backtest.clicked.connect(lambda: self.switch_page(1))
        layout.addWidget(self.btn_backtest)
        self.nav_buttons.append(self.btn_backtest)
        
        layout.addStretch()
        
        # 版本
        version = QLabel("v2.0.0")
        version.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        return sidebar
    
    def create_content(self):
        """创建内容区"""
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLORS['background']};")
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        
        # 页面堆叠
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # 添加页面
        self.stack.addWidget(self.create_query_page())
        self.stack.addWidget(self.create_backtest_page())
        
        return content
    
    def create_query_page(self):
        """股票查询页"""
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        
        # 搜索栏
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 4px;
            }}
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setSpacing(12)
        
        search_title = QLabel("股票查询")
        search_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 18px; font-weight: 600;")
        search_layout.addWidget(search_title)
        
        search_layout.addStretch()
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("输入股票代码，如 159892")
        self.code_input.setText("159892")
        self.code_input.setFixedWidth(180)
        search_layout.addWidget(self.code_input)
        
        self.days_combo = QComboBox()
        self.days_combo.addItems(["60天", "120天", "252天", "500天"])
        self.days_combo.setCurrentIndex(2)
        self.days_combo.setFixedWidth(90)
        search_layout.addWidget(self.days_combo)
        
        self.query_btn = QPushButton("查询")
        self.query_btn.setFixedWidth(80)
        self.query_btn.clicked.connect(self.on_query)
        search_layout.addWidget(self.query_btn)
        
        layout.addWidget(search_frame)
        
        # 指标卡片
        cards_frame = QFrame()
        cards_layout = QHBoxLayout(cards_frame)
        cards_layout.setSpacing(12)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        self.metric_cards = {
            'price': MetricCard("最新价", "-"),
            'change': MetricCard("涨跌幅", "-", "%"),
            'volume': MetricCard("成交量", "-", "万"),
            'high': MetricCard("最高", "-"),
            'low': MetricCard("最低", "-"),
        }
        
        for card in self.metric_cards.values():
            cards_layout.addWidget(card)
        
        cards_layout.addStretch()
        layout.addWidget(cards_frame)
        
        # 图表区
        chart_frame = QFrame()
        chart_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(12, 12, 12, 12)
        
        self.chart = CandlestickChart()
        chart_layout.addWidget(self.chart)
        
        layout.addWidget(chart_frame, 1)
        
        # 分析区
        analysis_splitter = QSplitter(Qt.Horizontal)
        
        # 趋势分析
        trend_frame = QFrame()
        trend_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        trend_layout = QVBoxLayout(trend_frame)
        
        trend_title = QLabel("趋势分析")
        trend_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600;")
        trend_layout.addWidget(trend_title)
        
        self.trend_text = QLabel("点击查询开始分析")
        self.trend_text.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        self.trend_text.setWordWrap(True)
        self.trend_text.setMinimumHeight(80)
        trend_layout.addWidget(self.trend_text)
        trend_layout.addStretch()
        
        analysis_splitter.addWidget(trend_frame)
        
        # 技术指标
        ind_frame = QFrame()
        ind_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        ind_layout = QGridLayout(ind_frame)
        ind_layout.setSpacing(12)
        
        ind_title = QLabel("技术指标")
        ind_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600;")
        ind_layout.addWidget(ind_title, 0, 0, 1, 4)
        
        self.indicator_labels = {}
        indicators = [("MA5", "ma5"), ("MA20", "ma20"), ("MA60", "ma60"),
                      ("DIF", "dif"), ("DEA", "dea"), ("RSI", "rsi")]
        
        for i, (name, key) in enumerate(indicators):
            row = (i // 3) + 1
            col = (i % 3) * 2
            label = QLabel(f"{name}:")
            label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            ind_layout.addWidget(label, row, col)
            
            value = QLabel("-")
            value.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
            self.indicator_labels[key] = value
            ind_layout.addWidget(value, row, col + 1)
        
        analysis_splitter.addWidget(ind_frame)
        analysis_splitter.setSizes([300, 400])
        
        layout.addWidget(analysis_splitter)
        
        page.setWidget(container)
        return page
    
    def create_backtest_page(self):
        """回测页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        # 设置区
        settings_frame = QFrame()
        settings_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 8px;
            }}
        """)
        settings_layout = QHBoxLayout(settings_frame)
        settings_layout.setSpacing(16)
        
        # 股票代码
        settings_layout.addWidget(QLabel("股票:"))
        self.bt_code_input = QLineEdit("159892")
        self.bt_code_input.setFixedWidth(100)
        settings_layout.addWidget(self.bt_code_input)
        
        # 策略
        settings_layout.addWidget(QLabel("策略:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["均线交叉", "RSI超买超卖", "MACD金叉死叉"])
        self.strategy_combo.setFixedWidth(120)
        settings_layout.addWidget(self.strategy_combo)
        
        # 初始资金
        settings_layout.addWidget(QLabel("资金:"))
        self.capital_spin = QSpinBox()
        self.capital_spin.setRange(10000, 10000000)
        self.capital_spin.setValue(100000)
        self.capital_spin.setSingleStep(10000)
        self.capital_spin.setFixedWidth(100)
        settings_layout.addWidget(self.capital_spin)
        
        # 回测按钮
        self.backtest_btn = QPushButton("开始回测")
        self.backtest_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: #2da44e; }}
        """)
        self.backtest_btn.clicked.connect(self.on_backtest)
        settings_layout.addWidget(self.backtest_btn)
        
        settings_layout.addStretch()
        layout.addWidget(settings_frame)
        
        # 结果区
        result_splitter = QSplitter(Qt.Horizontal)
        
        # 结果摘要
        result_frame = QFrame()
        result_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        result_layout = QVBoxLayout(result_frame)
        
        result_title = QLabel("回测结果")
        result_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600;")
        result_layout.addWidget(result_title)
        
        self.bt_result_labels = {}
        result_grid = QGridLayout()
        result_grid.setSpacing(12)
        
        fields = [
            ("总收益率", "total_ret"), ("年化收益", "annual_ret"),
            ("最大回撤", "max_dd"), ("夏普比率", "sharpe"),
            ("交易次数", "trades"), ("胜率", "win_rate")
        ]
        
        for i, (label, key) in enumerate(fields):
            result_grid.addWidget(QLabel(f"{label}:", styleSheet=f"color: {COLORS['text_secondary']};"), i, 0)
            value_label = QLabel("-")
            value_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: 600;")
            self.bt_result_labels[key] = value_label
            result_grid.addWidget(value_label, i, 1)
        
        result_layout.addLayout(result_grid)
        result_layout.addStretch()
        
        result_splitter.addWidget(result_frame)
        
        # 图表
        chart_frame = QFrame()
        chart_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(12, 12, 12, 12)
        
        self.backtest_chart = BacktestChart()
        chart_layout.addWidget(self.backtest_chart)
        
        result_splitter.addWidget(chart_frame)
        result_splitter.setSizes([250, 750])
        
        layout.addWidget(result_splitter, 1)
        
        # 交易记录
        trades_frame = QFrame()
        trades_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)
        trades_layout = QVBoxLayout(trades_frame)
        
        trades_title = QLabel("交易记录")
        trades_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 600;")
        trades_layout.addWidget(trades_title)
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(5)
        self.trades_table.setHorizontalHeaderLabels(["日期", "操作", "价格", "数量", "金额"])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setMaximumHeight(200)
        trades_layout.addWidget(self.trades_table)
        
        layout.addWidget(trades_frame)
        
        return page
    
    def create_menu(self):
        """菜单栏"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件")
        
        export_action = QAction("导出数据", self)
        export_action.setShortcut("Ctrl+S")
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
    def check_database(self):
        """检查数据库"""
        try:
            db = get_session_factory()()
            count = db.query(Stock).count()
            self.status_bar.showMessage(f"就绪 | 数据库有 {count} 只股票")
            db.close()
        except Exception as e:
            self.status_bar.showMessage(f"数据库错误: {e}")
    
    def switch_page(self, index):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        for btn in self.nav_buttons:
            btn.setChecked(False)
        self.nav_buttons[index].setChecked(True)
    
    def on_query(self):
        """查询"""
        stock_code = self.code_input.text().strip()
        if not stock_code:
            QMessageBox.warning(self, "提示", "请输入股票代码")
            return
        
        self.stock_code = stock_code
        days = int(self.days_combo.currentText().replace("天", ""))
        
        self.query_btn.setEnabled(False)
        self.query_btn.setText("加载中...")
        
        self.thread = DataFetchThread(stock_code, days)
        self.thread.status.connect(self.status_bar.showMessage)
        self.thread.finished_signal.connect(self.on_query_finished)
        self.thread.data_ready.connect(self.on_data_ready)
        self.thread.start()
    
    def on_query_finished(self, success, message):
        """查询完成"""
        self.query_btn.setEnabled(True)
        self.query_btn.setText("查询")
        self.status_bar.showMessage(message)
        
        if not success:
            QMessageBox.critical(self, "错误", message)
    
    def on_data_ready(self, df, indicators):
        """数据就绪"""
        self.current_df = df
        self.current_indicators = indicators
        
        if df.empty:
            return
        
        latest = df.iloc[-1]
        
        # 更新卡片
        self.metric_cards['price'].set_value(f"{latest['close_price']:.3f}")
        
        change_color = COLORS['success'] if latest['change_pct'] >= 0 else COLORS['danger']
        self.metric_cards['change'].set_value(f"{latest['change_pct']:+.2f}", change_color)
        
        self.metric_cards['volume'].set_value(f"{latest['volume']/10000:.1f}")
        self.metric_cards['high'].set_value(f"{latest['high_price']:.3f}")
        self.metric_cards['low'].set_value(f"{latest['low_price']:.3f}")
        
        # 更新图表
        self.chart.update_chart(df, indicators)
        
        # 更新趋势
        try:
            analyzer = TrendAnalyzer(df)
            result = analyzer.analyze()
            text = f"<b>趋势:</b> {result.direction.value} | <b>强度:</b> {result.strength.value} | <b>持续:</b> {result.trend_days}天<br><br>{result.description}"
            if result.support_levels:
                text += f"<br><br><b>支撑:</b> {', '.join([f'{s:.3f}' for s in result.support_levels[:3]])}"
            if result.resistance_levels:
                text += f"<br><b>阻力:</b> {', '.join([f'{r:.3f}' for r in result.resistance_levels[:3]])}"
            self.trend_text.setText(text)
        except Exception as e:
            self.trend_text.setText(f"分析失败: {e}")
        
        # 更新指标
        if indicators:
            self.indicator_labels['ma5'].setText(f"{indicators.ma5:.2f}" if indicators.ma5 else "-")
            self.indicator_labels['ma20'].setText(f"{indicators.ma20:.2f}" if indicators.ma20 else "-")
            self.indicator_labels['ma60'].setText(f"{indicators.ma60:.2f}" if indicators.ma60 else "-")
            self.indicator_labels['dif'].setText(f"{indicators.macd_dif:.3f}" if indicators.macd_dif else "-")
            self.indicator_labels['dea'].setText(f"{indicators.macd_dea:.3f}" if indicators.macd_dea else "-")
            self.indicator_labels['rsi'].setText(f"{indicators.rsi12:.1f}" if indicators.rsi12 else "-")
    
    def on_backtest(self):
        """回测"""
        stock_code = self.bt_code_input.text().strip()
        if not stock_code:
            QMessageBox.warning(self, "提示", "请输入股票代码")
            return
        
        # 默认回测最近2年
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)
        
        strategy = self.strategy_combo.currentText()
        capital = self.capital_spin.value()
        commission = 0.0003
        
        self.backtest_btn.setEnabled(False)
        self.backtest_btn.setText("回测中...")
        
        self.bt_thread = BacktestThread(stock_code, start_date, end_date, strategy, capital, commission)
        self.bt_thread.status.connect(self.status_bar.showMessage)
        self.bt_thread.finished_signal.connect(self.on_backtest_finished)
        self.bt_thread.start()
    
    def on_backtest_finished(self, success, message, results):
        """回测完成"""
        self.backtest_btn.setEnabled(True)
        self.backtest_btn.setText("开始回测")
        self.status_bar.showMessage(message)
        
        if not success:
            QMessageBox.critical(self, "回测失败", message)
            return
        
        # 更新结果
        self.bt_result_labels['total_ret'].setText(f"{results['total_return']*100:.2f}%")
        self.bt_result_labels['annual_ret'].setText(f"{results['annualized_return']*100:.2f}%")
        self.bt_result_labels['max_dd'].setText(f"{results['max_drawdown']*100:.2f}%")
        self.bt_result_labels['sharpe'].setText(f"{results['sharpe_ratio']:.2f}")
        self.bt_result_labels['trades'].setText(str(len(results['trades'])))
        
        # 计算胜率
        if results['trades']:
            profits = [t['pnl'] for t in results['trades'] if t['pnl'] is not None]
            wins = sum(1 for p in profits if p > 0)
            win_rate = wins / len(profits) * 100 if profits else 0
            self.bt_result_labels['win_rate'].setText(f"{win_rate:.1f}%")
            
            # 更新交易表
            self.trades_table.setRowCount(min(len(results['trades']), 50))
            for i, trade in enumerate(results['trades'][:50]):
                self.trades_table.setItem(i, 0, QTableWidgetItem(str(trade['timestamp'])))
                self.trades_table.setItem(i, 1, QTableWidgetItem(trade['side']))
                self.trades_table.setItem(i, 2, QTableWidgetItem(f"{trade['price']:.2f}"))
                self.trades_table.setItem(i, 3, QTableWidgetItem(str(trade['quantity'])))
                self.trades_table.setItem(i, 4, QTableWidgetItem(f"{trade['amount']:.2f}"))
        
        # 更新图表
        self.backtest_chart.update_backtest(results)
    
    def export_data(self):
        """导出"""
        if self.current_df is None:
            QMessageBox.warning(self, "提示", "没有数据可导出")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "导出", f"{self.stock_code}.csv", "CSV (*.csv)")
        if path:
            self.current_df.to_csv(path, index=False)
            QMessageBox.information(self, "成功", "数据已导出")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("股票分析系统")
    
    # 字体
    font = QFont("Segoe UI" if sys.platform == 'win32' else "PingFang SC", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
