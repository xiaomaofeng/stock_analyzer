# -*- coding: utf-8 -*-
"""
股票分析系统 - Desktop App (PySide6)
支持多语言: 中文 / English
同时维护 Web 和 Desktop 两个版本
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QStackedWidget,
    QFrame, QGridLayout, QStatusBar, QMenuBar, QMenu,
    QFileDialog, QMessageBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QFont
import pandas as pd
from datetime import datetime, timedelta

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator
from collectors import AKShareCollector
from processors import TechnicalCalculator
from processors.calculators import save_indicators_to_db
from analysis import TrendAnalyzer
from analysis.risk_metrics import RiskMetrics

from desktop.styles.modern_theme import MODERN_STYLE, COLORS

# 多语言支持
I18N = {
    'zh': {
        'title': '股票分析系统',
        'stock_query': '股票查询',
        'dashboard': '仪表盘',
        'stock_viewer': '个股分析',
        'backtest': '策略回测',
        'screener': '股票筛选',
        'settings': '设置',
        'language': '语言',
        'stock_code': '股票代码',
        'query': '查询',
        'days': '天数',
        'latest_price': '最新价',
        'change': '涨跌幅',
        'volume': '成交量',
        'high': '最高',
        'low': '最低',
        'total_return': '总收益率',
        'annual_return': '年化收益',
        'max_dd': '最大回撤',
        'sharpe': '夏普比率',
        'run_backtest': '开始回测',
        'export': '导出',
        'exit': '退出',
        'ready': '就绪',
        'db_connected': '数据库已连接',
    },
    'en': {
        'title': 'Stock Analyzer',
        'stock_query': 'Stock Query',
        'dashboard': 'Dashboard',
        'stock_viewer': 'Stock Viewer',
        'backtest': 'Backtest',
        'screener': 'Screener',
        'settings': 'Settings',
        'language': 'Language',
        'stock_code': 'Stock Code',
        'query': 'Query',
        'days': 'Days',
        'latest_price': 'Latest Price',
        'change': 'Change',
        'volume': 'Volume',
        'high': 'High',
        'low': 'Low',
        'total_return': 'Total Return',
        'annual_return': 'Annual Return',
        'max_dd': 'Max Drawdown',
        'sharpe': 'Sharpe Ratio',
        'run_backtest': 'Run Backtest',
        'export': 'Export',
        'exit': 'Exit',
        'ready': 'Ready',
        'db_connected': 'Database connected',
    }
}


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.lang = 'zh'  # 默认中文
        self.current_df = None
        self.stock_code = None
        
        self.setWindowTitle(I18N[self.lang]['title'])
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        self.init_ui()
        self.setStyleSheet(MODERN_STYLE)
        self.check_database()
    
    def t(self, key):
        """翻译"""
        return I18N[self.lang].get(key, key)
    
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
        self.status_bar.showMessage(self.t('ready'))
        
        self.create_menu()
    
    def create_sidebar(self):
        """创建侧边栏"""
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background-color: {COLORS['surface']}; border-right: 1px solid {COLORS['border']};")
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)
        
        # 标题
        title = QLabel("📈 " + self.t('title'))
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 700;")
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # 导航按钮
        self.nav_buttons = []
        
        pages = [
            ('stock_query', '🔍'),
            ('dashboard', '📊'),
            ('stock_viewer', '📈'),
            ('backtest', '🔄'),
            ('screener', '🔎'),
        ]
        
        for page_key, icon in pages:
            btn = QPushButton(f"{icon}  {self.t(page_key)}")
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['text_secondary']};
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                    font-size: 13px;
                    text-align: left;
                }}
                QPushButton:hover {{ background-color: {COLORS['hover']}; }}
                QPushButton:checked {{ background-color: {COLORS['primary']}; color: white; }}
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=len(self.nav_buttons): self.switch_page(idx))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        self.nav_buttons[0].setChecked(True)
        
        layout.addStretch()
        
        # 语言切换
        lang_label = QLabel(self.t('language'))
        lang_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(lang_label)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(['🇨🇳 中文', '🇺🇸 English'])
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        layout.addWidget(self.lang_combo)
        
        layout.addSpacing(10)
        
        # 版本
        version = QLabel("v2.0")
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
        
        # 添加所有页面
        self.stack.addWidget(self.create_query_page())
        self.stack.addWidget(self.create_dashboard_page())
        self.stack.addWidget(self.create_viewer_page())
        self.stack.addWidget(self.create_backtest_page())
        self.stack.addWidget(self.create_screener_page())
        
        return content
    
    def create_query_page(self):
        """股票查询页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        # 搜索栏
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        search_layout = QHBoxLayout(search_frame)
        
        self.query_code_input = QLineEdit()
        self.query_code_input.setPlaceholderText("159892")
        self.query_code_input.setText("159892")
        self.query_code_input.setFixedWidth(150)
        search_layout.addWidget(QLabel(self.t('stock_code')))
        search_layout.addWidget(self.query_code_input)
        
        self.query_days = QComboBox()
        self.query_days.addItems(['60', '120', '252', '500'])
        self.query_days.setCurrentIndex(2)
        search_layout.addWidget(QLabel(self.t('days')))
        search_layout.addWidget(self.query_days)
        
        btn = QPushButton(self.t('query'))
        btn.setFixedWidth(100)
        btn.clicked.connect(self.on_query)
        search_layout.addWidget(btn)
        
        search_layout.addStretch()
        layout.addWidget(search_frame)
        
        # 结果区（简化版，实际可添加图表）
        self.query_result = QLabel("Enter stock code to query")
        self.query_result.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 40px;")
        self.query_result.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.query_result)
        
        layout.addStretch()
        return page
    
    def create_dashboard_page(self):
        """仪表盘页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        label = QLabel("Dashboard - Overview of your stock database")
        label.setStyleSheet(f"color: {COLORS['text']}; font-size: 18px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # 这里可以添加统计卡片等
        layout.addStretch()
        return page
    
    def create_viewer_page(self):
        """个股分析页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        label = QLabel("Stock Viewer - Detailed charts and indicators")
        label.setStyleSheet(f"color: {COLORS['text']}; font-size: 18px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        layout.addStretch()
        return page
    
    def create_backtest_page(self):
        """回测页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        # 设置区
        settings = QFrame()
        settings.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        settings_layout = QHBoxLayout(settings)
        
        self.bt_code = QLineEdit("159892")
        self.bt_code.setFixedWidth(100)
        settings_layout.addWidget(QLabel(self.t('stock_code')))
        settings_layout.addWidget(self.bt_code)
        
        self.bt_strategy = QComboBox()
        self.bt_strategy.addItems(["MA Cross", "RSI", "MACD"])
        settings_layout.addWidget(QLabel(self.t('backtest')))
        settings_layout.addWidget(self.bt_strategy)
        
        self.bt_capital = QSpinBox()
        self.bt_capital.setRange(10000, 10000000)
        self.bt_capital.setValue(100000)
        self.bt_capital.setSingleStep(10000)
        settings_layout.addWidget(QLabel(self.t('query')))  # Capital label
        settings_layout.addWidget(self.bt_capital)
        
        btn = QPushButton(self.t('run_backtest'))
        btn.setStyleSheet(f"background-color: {COLORS['success']}; color: white;")
        btn.clicked.connect(self.on_backtest)
        settings_layout.addWidget(btn)
        
        settings_layout.addStretch()
        layout.addWidget(settings)
        
        # 结果区
        self.bt_result = QLabel("Run backtest to see results")
        self.bt_result.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 40px;")
        self.bt_result.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.bt_result)
        
        layout.addStretch()
        return page
    
    def create_screener_page(self):
        """筛选器页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        label = QLabel("Stock Screener - Filter stocks by conditions")
        label.setStyleSheet(f"color: {COLORS['text']}; font-size: 18px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        layout.addStretch()
        return page
    
    def create_menu(self):
        """菜单栏"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        
        export_action = QAction(self.t('export'), self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(self.t('exit'), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
    def switch_page(self, index):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        for btn in self.nav_buttons:
            btn.setChecked(False)
        self.nav_buttons[index].setChecked(True)
    
    def change_language(self, index):
        """切换语言"""
        self.lang = 'en' if index == 1 else 'zh'
        self.setWindowTitle(self.t('title'))
        # 实际应用需要重新创建UI或更新所有文本
        QMessageBox.information(self, "Language Changed", "Please restart to apply changes" if self.lang == 'en' else "请重启应用以生效")
    
    def check_database(self):
        """检查数据库"""
        try:
            db = get_session_factory()()
            count = db.query(Stock).count()
            self.status_bar.showMessage(f"{self.t('db_connected')} | {count} stocks")
            db.close()
        except Exception as e:
            self.status_bar.showMessage(f"DB Error: {e}")
    
    def on_query(self):
        """查询"""
        code = self.query_code_input.text().strip()
        if code:
            self.query_result.setText(f"Querying {code}... (Function to be implemented)")
    
    def on_backtest(self):
        """回测"""
        code = self.bt_code.text().strip()
        if code:
            self.bt_result.setText(f"Running backtest for {code}... (Function to be implemented)")
    
    def export_data(self):
        """导出"""
        QMessageBox.information(self, "Export", "Export function to be implemented")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Stock Analyzer")
    
    font = QFont("Segoe UI" if sys.platform == 'win32' else "PingFang SC", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
