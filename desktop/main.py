# -*- coding: utf-8 -*-
"""
股票分析系统 - 桌面应用 (PySide6)
支持 Windows 和 macOS
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit, QMessageBox,
    QProgressBar, QStatusBar, QMenuBar, QMenu, QGridLayout, QGroupBox,
    QFileDialog, QTabWidget, QSpinBox, QDoubleSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QFont
import pandas as pd
from datetime import datetime, timedelta

from config import get_session_factory, get_settings
from database.models import Stock, DailyPrice, TechnicalIndicator
from collectors import AKShareCollector
from processors import TechnicalCalculator
from processors.calculators import save_indicators_to_db
from analysis import TrendAnalyzer
from analysis.risk_metrics import RiskMetrics

# 导入自定义组件
from widgets.candlestick_chart import CandlestickChart, BacktestChart


class DataFetchThread(QThread):
    """数据获取后台线程"""
    progress = Signal(int)
    status = Signal(str)
    finished_signal = Signal(bool, str)
    data_ready = Signal(object, object)  # df, indicators
    
    def __init__(self, stock_code, days):
        super().__init__()
        self.stock_code = stock_code
        self.days = days
        
    def run(self):
        try:
            self.status.emit(f"正在获取 {self.stock_code} 数据...")
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
                    
                    # 计算指标
                    self.status.emit("计算技术指标...")
                    calculator = TechnicalCalculator()
                    df_calc = calculator.calculate_all(df)
                    save_indicators_to_db(self.stock_code, df_calc, db)
                
                # 查询数据
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
                self.finished_signal.emit(True, f"成功加载 {len(df)} 条数据")
                
            finally:
                db.close()
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class BacktestThread(QThread):
    """回测后台线程"""
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
                    self.finished_signal.emit(False, "数据不足，至少需要60天数据", None)
                    return
                
                df = pd.DataFrame([{
                    'trade_date': p.trade_date,
                    'open_price': float(p.open_price) if p.open_price else 0,
                    'high_price': float(p.high_price) if p.high_price else 0,
                    'low_price': float(p.low_price) if p.low_price else 0,
                    'close_price': float(p.close_price) if p.close_price else 0,
                    'volume': p.volume or 0,
                } for p in prices])
                
                # 计算指标
                from processors import TechnicalCalculator
                calc = TechnicalCalculator()
                df = calc.calculate_all(df)
                
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
                else:  # MACD
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
            self.finished_signal.emit(False, str(e) + "\n" + traceback.format_exc(), None)


class StockAnalyzerApp(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("股票分析系统 v2.0")
        self.setGeometry(100, 100, 1600, 1000)
        
        self.current_df = None
        self.current_indicators = None
        self.stock_code = None
        
        self.init_ui()
        self.init_menu()
        self.check_database()
    
    def init_ui(self):
        """初始化界面"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # 创建标签页
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 股票查询页
        self.query_tab = self.create_query_tab()
        self.tabs.addTab(self.query_tab, "股票查询")
        
        # 回测页
        self.backtest_tab = self.create_backtest_tab()
        self.tabs.addTab(self.backtest_tab, "策略回测")
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
    
    def create_query_tab(self):
        """创建股票查询页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧面板
        left_panel = self.create_query_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧图表
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.chart = CandlestickChart()
        right_layout.addWidget(self.chart)
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 1200])
        return tab
    
    def create_query_left_panel(self):
        """创建查询左侧面板"""
        panel = QGroupBox("控制面板")
        layout = QVBoxLayout()
        
        # 股票代码
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("股票代码:"))
        self.code_input = QLineEdit("159892")
        code_layout.addWidget(self.code_input)
        layout.addLayout(code_layout)
        
        # 数据范围
        days_layout = QHBoxLayout()
        days_layout.addWidget(QLabel("数据范围:"))
        self.days_combo = QComboBox()
        self.days_combo.addItems(["60天", "120天", "252天", "500天"])
        self.days_combo.setCurrentIndex(2)
        days_layout.addWidget(self.days_combo)
        layout.addLayout(days_layout)
        
        # 查询按钮
        self.query_btn = QPushButton("查询并分析")
        self.query_btn.setStyleSheet("""
            QPushButton {
                background-color: #1890ff; color: white;
                padding: 10px; font-size: 14px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #40a9ff; }
        """)
        self.query_btn.clicked.connect(self.on_query)
        layout.addWidget(self.query_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 基本信息
        self.info_group = QGroupBox("基本信息")
        info_layout = QGridLayout()
        self.info_labels = {}
        for i, (label, key) in enumerate([("最新价", "price"), ("涨跌幅", "change"), ("成交量", "vol"), ("最高", "high"), ("最低", "low")]):
            info_layout.addWidget(QLabel(f"{label}:"), i, 0)
            self.info_labels[key] = QLabel("-")
            self.info_labels[key].setStyleSheet("color: #1890ff; font-weight: bold;")
            info_layout.addWidget(self.info_labels[key], i, 1)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)
        
        # 技术指标
        self.indicator_group = QGroupBox("技术指标")
        ind_layout = QGridLayout()
        self.indicator_labels = {}
        fields = [("MA5", "ma5"), ("MA20", "ma20"), ("MA60", "ma60"), ("MACD DIF", "dif"), ("MACD DEA", "dea"), ("RSI12", "rsi")]
        for i, (label, key) in enumerate(fields):
            ind_layout.addWidget(QLabel(f"{label}:"), i//2, (i%2)*2)
            self.indicator_labels[key] = QLabel("-")
            ind_layout.addWidget(self.indicator_labels[key], i//2, (i%2)*2+1)
        self.indicator_group.setLayout(ind_layout)
        layout.addWidget(self.indicator_group)
        
        # 趋势分析
        self.trend_group = QGroupBox("趋势分析")
        trend_layout = QVBoxLayout()
        self.trend_text = QTextEdit()
        self.trend_text.setReadOnly(True)
        self.trend_text.setMaximumHeight(100)
        trend_layout.addWidget(self.trend_text)
        self.trend_group.setLayout(trend_layout)
        layout.addWidget(self.trend_group)
        
        # 风险指标
        self.risk_group = QGroupBox("风险指标")
        risk_layout = QGridLayout()
        self.risk_labels = {}
        for i, (label, key) in enumerate([("年化收益", "ret"), ("波动率", "vol"), ("最大回撤", "dd"), ("夏普比率", "sharpe")]):
            risk_layout.addWidget(QLabel(f"{label}:"), i//2, (i%2)*2)
            self.risk_labels[key] = QLabel("-")
            risk_layout.addWidget(self.risk_labels[key], i//2, (i%2)*2+1)
        self.risk_group.setLayout(risk_layout)
        layout.addWidget(self.risk_group)
        
        layout.addStretch()
        
        # 导出按钮
        self.export_btn = QPushButton("导出数据(CSV)")
        self.export_btn.clicked.connect(self.export_data)
        layout.addWidget(self.export_btn)
        
        panel.setLayout(layout)
        panel.setMaximumWidth(380)
        return panel
    
    def create_backtest_tab(self):
        """创建回测页面"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧控制面板
        left_panel = QGroupBox("回测设置")
        left_layout = QVBoxLayout()
        
        # 股票代码
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("股票代码:"))
        self.bt_code_input = QLineEdit("159892")
        code_layout.addWidget(self.bt_code_input)
        left_layout.addLayout(code_layout)
        
        # 策略选择
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("策略:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["均线交叉", "RSI超买超卖", "MACD金叉死叉"])
        strategy_layout.addWidget(self.strategy_combo)
        left_layout.addLayout(strategy_layout)
        
        # 初始资金
        capital_layout = QHBoxLayout()
        capital_layout.addWidget(QLabel("初始资金:"))
        self.capital_spin = QSpinBox()
        self.capital_spin.setRange(10000, 10000000)
        self.capital_spin.setValue(100000)
        self.capital_spin.setSingleStep(10000)
        capital_layout.addWidget(self.capital_spin)
        left_layout.addLayout(capital_layout)
        
        # 手续费
        commission_layout = QHBoxLayout()
        commission_layout.addWidget(QLabel("手续费率:"))
        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setRange(0.0001, 0.01)
        self.commission_spin.setValue(0.0003)
        self.commission_spin.setDecimals(4)
        self.commission_spin.setSingleStep(0.0001)
        commission_layout.addWidget(self.commission_spin)
        left_layout.addLayout(commission_layout)
        
        # 回测按钮
        self.backtest_btn = QPushButton("开始回测")
        self.backtest_btn.setStyleSheet("""
            QPushButton {
                background-color: #52c41a; color: white;
                padding: 10px; font-size: 14px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #73d13d; }
        """)
        self.backtest_btn.clicked.connect(self.run_backtest)
        left_layout.addWidget(self.backtest_btn)
        
        # 结果摘要
        self.bt_result_group = QGroupBox("回测结果")
        result_layout = QGridLayout()
        self.bt_result_labels = {}
        fields = [
            ("总收益率", "total_ret"), ("年化收益率", "annual_ret"),
            ("最大回撤", "max_dd"), ("夏普比率", "sharpe"),
            ("交易次数", "trades"), ("胜率", "win_rate")
        ]
        for i, (label, key) in enumerate(fields):
            result_layout.addWidget(QLabel(f"{label}:"), i//2, (i%2)*2)
            self.bt_result_labels[key] = QLabel("-")
            self.bt_result_labels[key].setStyleSheet("color: #52c41a; font-weight: bold;")
            result_layout.addWidget(self.bt_result_labels[key], i//2, (i%2)*2+1)
        self.bt_result_group.setLayout(result_layout)
        left_layout.addWidget(self.bt_result_group)
        
        # 交易记录表格
        self.trades_group = QGroupBox("交易记录")
        trades_layout = QVBoxLayout()
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(5)
        self.trades_table.setHorizontalHeaderLabels(["日期", "操作", "价格", "数量", "金额"])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        trades_layout.addWidget(self.trades_table)
        self.trades_group.setLayout(trades_layout)
        left_layout.addWidget(self.trades_group)
        
        left_layout.addStretch()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(400)
        splitter.addWidget(left_panel)
        
        # 右侧图表
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.backtest_chart = BacktestChart()
        right_layout.addWidget(self.backtest_chart)
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 1200])
        return tab
    
    def init_menu(self):
        """初始化菜单"""
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
        
        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def check_database(self):
        """检查数据库"""
        try:
            db = get_session_factory()()
            count = db.query(Stock).count()
            self.status_bar.showMessage(f"就绪 | 数据库有 {count} 只股票")
            db.close()
        except Exception as e:
            self.status_bar.showMessage(f"数据库错误: {e}")
    
    def on_query(self):
        """查询股票"""
        stock_code = self.code_input.text().strip()
        if not stock_code:
            QMessageBox.warning(self, "警告", "请输入股票代码")
            return
        
        self.stock_code = stock_code
        days = int(self.days_combo.currentText().replace("天", ""))
        
        self.query_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.thread = DataFetchThread(stock_code, days)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.status.connect(self.status_bar.showMessage)
        self.thread.finished_signal.connect(self.on_query_finished)
        self.thread.data_ready.connect(self.on_data_ready)
        self.thread.start()
    
    def on_query_finished(self, success, message):
        """查询完成"""
        self.query_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            self.status_bar.showMessage(message)
        else:
            QMessageBox.critical(self, "错误", message)
    
    def on_data_ready(self, df, indicators):
        """数据就绪"""
        self.current_df = df
        self.current_indicators = indicators
        
        if df.empty:
            return
        
        latest = df.iloc[-1]
        
        # 更新基本信息
        self.info_labels["price"].setText(f"{latest['close_price']:.3f}")
        self.info_labels["change"].setText(f"{latest['change_pct']:.2f}%")
        self.info_labels["vol"].setText(f"{latest['volume']/10000:.0f}万")
        self.info_labels["high"].setText(f"{latest['high_price']:.3f}")
        self.info_labels["low"].setText(f"{latest['low_price']:.3f}")
        
        # 更新指标
        if indicators:
            self.indicator_labels["ma5"].setText(f"{indicators.ma5:.3f}" if indicators.ma5 else "-")
            self.indicator_labels["ma20"].setText(f"{indicators.ma20:.3f}" if indicators.ma20 else "-")
            self.indicator_labels["ma60"].setText(f"{indicators.ma60:.3f}" if indicators.ma60 else "-")
            self.indicator_labels["dif"].setText(f"{indicators.macd_dif:.4f}" if indicators.macd_dif else "-")
            self.indicator_labels["dea"].setText(f"{indicators.macd_dea:.4f}" if indicators.macd_dea else "-")
            self.indicator_labels["rsi"].setText(f"{indicators.rsi12:.2f}" if indicators.rsi12 else "-")
        
        # 更新趋势分析
        try:
            analyzer = TrendAnalyzer(df)
            result = analyzer.analyze()
            text = f"趋势: {result.direction.value} | 强度: {result.strength.value} | 持续{result.trend_days}天\n{result.description}"
            self.trend_text.setText(text)
        except Exception as e:
            self.trend_text.setText(f"分析失败: {e}")
        
        # 更新风险指标
        try:
            returns = df['close_price'].pct_change().dropna()
            if len(returns) > 30:
                metrics = RiskMetrics(returns)
                result = metrics.calculate_all()
                self.risk_labels["ret"].setText(f"{result.annualized_return*100:.1f}%")
                self.risk_labels["vol"].setText(f"{result.annualized_volatility*100:.1f}%")
                self.risk_labels["dd"].setText(f"{result.max_drawdown*100:.1f}%")
                self.risk_labels["sharpe"].setText(f"{result.sharpe_ratio:.2f}")
        except Exception as e:
            pass
        
        # 更新图表
        self.chart.update_chart(df, indicators)
    
    def run_backtest(self):
        """运行回测"""
        stock_code = self.bt_code_input.text().strip()
        if not stock_code:
            QMessageBox.warning(self, "警告", "请输入股票代码")
            return
        
        # 使用全部历史数据回测
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # 2年
        
        strategy = self.strategy_combo.currentText()
        capital = self.capital_spin.value()
        commission = self.commission_spin.value()
        
        self.backtest_btn.setEnabled(False)
        self.status_bar.showMessage("回测中...")
        
        self.bt_thread = BacktestThread(stock_code, start_date, end_date, strategy, capital, commission)
        self.bt_thread.status.connect(self.status_bar.showMessage)
        self.bt_thread.finished_signal.connect(self.on_backtest_finished)
        self.bt_thread.start()
    
    def on_backtest_finished(self, success, message, results):
        """回测完成"""
        self.backtest_btn.setEnabled(True)
        
        if not success:
            QMessageBox.critical(self, "回测失败", message)
            self.status_bar.showMessage("回测失败")
            return
        
        self.status_bar.showMessage(message)
        
        # 更新结果
        self.bt_result_labels["total_ret"].setText(f"{results['total_return']*100:.2f}%")
        self.bt_result_labels["annual_ret"].setText(f"{results['annualized_return']*100:.2f}%")
        self.bt_result_labels["max_dd"].setText(f"{results['max_drawdown']*100:.2f}%")
        self.bt_result_labels["sharpe"].setText(f"{results['sharpe_ratio']:.2f}")
        self.bt_result_labels["trades"].setText(str(len(results['trades'])))
        
        # 计算胜率
        if results['trades']:
            profits = [t['pnl'] for t in results['trades'] if t['pnl'] is not None]
            wins = sum(1 for p in profits if p > 0)
            win_rate = wins / len(profits) * 100 if profits else 0
            self.bt_result_labels["win_rate"].setText(f"{win_rate:.1f}%")
            
            # 更新交易记录表
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
        """导出数据"""
        if self.current_df is None:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "保存数据", f"{self.stock_code}.csv", "CSV (*.csv)")
        if path:
            self.current_df.to_csv(path, index=False)
            QMessageBox.information(self, "成功", f"数据已保存到:\n{path}")
    
    def show_about(self):
        """关于"""
        QMessageBox.about(self, "关于", "股票分析系统 v2.0\n\n基于 PySide6 的跨平台桌面应用")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("股票分析系统")
    app.setStyle('Fusion')
    
    font = QFont("Microsoft YaHei" if sys.platform == 'win32' else "PingFang SC", 10)
    app.setFont(font)
    
    window = StockAnalyzerApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
