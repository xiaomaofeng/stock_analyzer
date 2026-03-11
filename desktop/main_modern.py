# -*- coding: utf-8 -*-
"""股票分析系统 - Modern Desktop App (macOS/Win11 Style)"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QStackedWidget,
    QFrame, QGridLayout, QProgressBar, QStatusBar, QMenuBar, QMenu,
    QFileDialog, QMessageBox, QSizePolicy, QSpacerItem, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QAction, QFont, QIcon, QPixmap, QFontDatabase
import pandas as pd
from datetime import datetime, timedelta

from config import get_session_factory
from database.models import Stock, DailyPrice, TechnicalIndicator
from collectors import AKShareCollector
from processors import TechnicalCalculator
from processors.calculators import save_indicators_to_db
from analysis import TrendAnalyzer
from analysis.risk_metrics import RiskMetrics

from styles.modern_theme import MODERN_STYLE, COLORS
from widgets.candlestick_chart import CandlestickChart, BacktestChart


class DataFetchThread(QThread):
    progress = Signal(int)
    status = Signal(str)
    finished_signal = Signal(bool, str)
    data_ready = Signal(object, object)
    
    def __init__(self, stock_code, days):
        super().__init__()
        self.stock_code = stock_code
        self.days = days
        
    def run(self):
        try:
            self.status.emit(f"正在获取 {self.stock_code}...")
            from config import get_session_factory
            SessionLocal = get_session_factory()
            db = SessionLocal()
            
            try:
                existing = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == self.stock_code
                ).count()
                
                if existing == 0:
                    self.status.emit("从 AKShare 获取数据...")
                    collector = AKShareCollector(request_delay=0.5)
                    stock_info = collector.get_stock_info(self.stock_code)
                    
                    stock = Stock(
                        stock_code=self.stock_code,
                        stock_name=stock_info.get('stock_name', self.stock_code) if stock_info else self.stock_code,
                        exchange=collector._get_exchange(self.stock_code),
                    )
                    db.merge(stock)
                    
                    end = datetime.now()
                    start = end - timedelta(days=self.days * 2)
                    df = collector.get_daily_prices(
                        self.stock_code,
                        start.strftime('%Y-%m-%d'),
                        end.strftime('%Y-%m-%d')
                    )
                    
                    if df.empty:
                        self.finished_signal.emit(False, "无法获取数据")
                        return
                    
                    total = len(df)
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
                        self.progress.emit(int((idx + 1) / total * 100))
                    
                    db.commit()
                    calculator = TechnicalCalculator()
                    df_calc = calculator.calculate_all(df)
                    save_indicators_to_db(self.stock_code, df_calc, db)
                
                prices = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == self.stock_code
                ).order_by(DailyPrice.trade_date.desc()).limit(self.days).all()
                
                indicators = db.query(TechnicalIndicator).filter(
                    TechnicalIndicator.stock_code == self.stock_code
                ).order_by(TechnicalIndicator.trade_date.desc()).first()
                
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
            self.finished_signal.emit(False, str(e))


class MetricCard(QFrame):
    """指标卡片组件"""
    def __init__(self, title, value="-", unit="", color=None, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 20px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.title_label)
        
        self.value_layout = QHBoxLayout()
        self.value_label = QLabel(value)
        color_style = f"color: {color};" if color else f"color: {COLORS['text']};"
        self.value_label.setStyleSheet(f"{color_style} font-size: 28px; font-weight: 700;")
        self.value_layout.addWidget(self.value_label)
        
        if unit:
            self.unit_label = QLabel(unit)
            self.unit_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
            self.value_layout.addWidget(self.unit_label)
        
        self.value_layout.addStretch()
        layout.addLayout(self.value_layout)
        
        self.setMinimumWidth(180)
        self.setMaximumWidth(280)
    
    def set_value(self, value, color=None):
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 700;")


class SidebarButton(QPushButton):
    """侧边栏按钮"""
    def __init__(self, text, icon_text, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {text}")
        self.setCheckable(True)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 10px;
                padding: 14px 20px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
                color: {COLORS['text']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                color: white;
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)


class ModernStockAnalyzer(QMainWindow):
    """现代化主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("股票分析系统")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        self.current_df = None
        self.current_indicators = None
        
        self.init_ui()
        self.setStyleSheet(MODERN_STYLE)
    
    def init_ui(self):
        """初始化界面"""
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧边栏
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # 右侧内容区
        content = self.create_content()
        main_layout.addWidget(content, 1)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 菜单栏
        self.create_menu()
    
    def create_sidebar(self):
        """创建侧边栏"""
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(8)
        
        # Logo/标题
        title = QLabel("📈 股票分析")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 20px; font-weight: 700;")
        layout.addWidget(title)
        
        layout.addSpacing(24)
        
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
        
        # 底部信息
        version = QLabel("v2.0.0")
        version.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        return sidebar
    
    def create_content(self):
        """创建内容区"""
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLORS['background']};")
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)
        
        # 页面堆叠
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # 股票查询页
        query_page = self.create_query_page()
        self.stack.addWidget(query_page)
        
        # 回测页
        backtest_page = self.create_backtest_page()
        self.stack.addWidget(backtest_page)
        
        return content
    
    def create_query_page(self):
        """创建股票查询页"""
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(24)
        
        # 标题栏 + 搜索
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 20px;
            }}
        """)
        header_layout = QHBoxLayout(header)
        
        title = QLabel("股票查询与分析")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: 700;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 搜索框
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border-radius: 10px;
                padding: 4px;
            }}
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setSpacing(8)
        search_layout.setContentsMargins(12, 4, 4, 4)
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("输入股票代码，如 159892")
        self.code_input.setText("159892")
        self.code_input.setFixedWidth(200)
        self.code_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                padding: 8px;
            }
        """)
        search_layout.addWidget(self.code_input)
        
        self.days_combo = QComboBox()
        self.days_combo.addItems(["60天", "120天", "252天", "500天"])
        self.days_combo.setCurrentIndex(2)
        self.days_combo.setFixedWidth(90)
        self.days_combo.setStyleSheet("border: none; background: transparent;")
        search_layout.addWidget(self.days_combo)
        
        self.query_btn = QPushButton("查询")
        self.query_btn.setFixedSize(80, 36)
        self.query_btn.setCursor(Qt.PointingHandCursor)
        self.query_btn.clicked.connect(self.on_query)
        search_layout.addWidget(self.query_btn)
        
        header_layout.addWidget(search_frame)
        layout.addWidget(header)
        
        # 指标卡片区
        cards_frame = QFrame()
        cards_layout = QHBoxLayout(cards_frame)
        cards_layout.setSpacing(16)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        self.metric_cards = {
            'price': MetricCard("最新价", "-", ""),
            'change': MetricCard("涨跌幅", "-", "%"),
            'volume': MetricCard("成交量", "-", "万"),
            'high': MetricCard("最高", "-", ""),
            'low': MetricCard("最低", "-", ""),
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
                border-radius: 16px;
                padding: 20px;
            }}
        """)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chart = CandlestickChart()
        chart_layout.addWidget(self.chart)
        
        layout.addWidget(chart_frame)
        
        # 分析区
        analysis_frame = QFrame()
        analysis_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 20px;
            }}
        """)
        analysis_layout = QHBoxLayout(analysis_frame)
        
        # 趋势分析
        trend_box = QVBoxLayout()
        trend_title = QLabel("趋势分析")
        trend_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600;")
        trend_box.addWidget(trend_title)
        
        self.trend_text = QLabel("点击查询开始分析")
        self.trend_text.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; padding: 10px;")
        self.trend_text.setWordWrap(True)
        trend_box.addWidget(self.trend_text)
        trend_box.addStretch()
        
        analysis_layout.addLayout(trend_box, 1)
        
        # 技术指标
        indicator_box = QVBoxLayout()
        indicator_title = QLabel("技术指标")
        indicator_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: 600;")
        indicator_box.addWidget(indicator_title)
        
        self.indicator_grid = QGridLayout()
        self.indicator_labels = {}
        indicators = [("MA5", "ma5"), ("MA20", "ma20"), ("MA60", "ma60"), 
                      ("MACD", "macd"), ("RSI", "rsi"), ("KDJ", "kdj")]
        
        for i, (name, key) in enumerate(indicators):
            label = QLabel(f"{name}:")
            label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            self.indicator_grid.addWidget(label, i//3, (i%3)*2)
            
            value = QLabel("-")
            value.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
            self.indicator_labels[key] = value
            self.indicator_grid.addWidget(value, i//3, (i%3)*2+1)
        
        indicator_box.addLayout(self.indicator_grid)
        indicator_box.addStretch()
        
        analysis_layout.addLayout(indicator_box, 1)
        
        layout.addWidget(analysis_frame)
        
        layout.addStretch()
        
        page.setWidget(container)
        return page
    
    def create_backtest_page(self):
        """创建回测页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(24)
        
        label = QLabel("策略回测功能开发中...")
        label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        layout.addStretch()
        return page
    
    def create_menu(self):
        """创建菜单"""
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
    
    def switch_page(self, index):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        for btn in self.nav_buttons:
            btn.setChecked(False)
        self.nav_buttons[index].setChecked(True)
    
    def on_query(self):
        """查询股票"""
        stock_code = self.code_input.text().strip()
        if not stock_code:
            QMessageBox.warning(self, "提示", "请输入股票代码")
            return
        
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
            trend_text = f"<b>{result.direction.value}</b> | 强度: {result.strength.value} | 持续 {result.trend_days} 天<br><br>{result.description}"
            self.trend_text.setText(trend_text)
        except Exception as e:
            self.trend_text.setText(f"分析失败: {e}")
        
        # 更新指标
        if indicators:
            self.indicator_labels['ma5'].setText(f"{indicators.ma5:.2f}" if indicators.ma5 else "-")
            self.indicator_labels['ma20'].setText(f"{indicators.ma20:.2f}" if indicators.ma20 else "-")
            self.indicator_labels['ma60'].setText(f"{indicators.ma60:.2f}" if indicators.ma60 else "-")
            self.indicator_labels['macd'].setText(f"{indicators.macd_dif:.3f}" if indicators.macd_dif else "-")
            self.indicator_labels['rsi'].setText(f"{indicators.rsi12:.1f}" if indicators.rsi12 else "-")
    
    def export_data(self):
        """导出数据"""
        if self.current_df is None:
            QMessageBox.warning(self, "提示", "没有数据可导出")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "导出数据", "stock_data.csv", "CSV (*.csv)")
        if path:
            self.current_df.to_csv(path, index=False)
            QMessageBox.information(self, "成功", "数据已导出")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("股票分析系统")
    
    # 设置字体
    font = QFont("Segoe UI" if sys.platform == 'win32' else ".AppleSystemUIFont" if sys.platform == 'darwin' else "Noto Sans", 10)
    app.setFont(font)
    
    window = ModernStockAnalyzer()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
