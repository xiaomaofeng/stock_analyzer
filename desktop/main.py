# -*- coding: utf-8 -*-
"""
股票分析系统 - 桌面应用主入口
支持 Windows 和 macOS
"""
import sys
from pathlib import Path

# 设置项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QLineEdit, 
    QComboBox, QTableWidget, QTableWidgetItem, 
    QTabWidget, QSplitter, QTextEdit, QMessageBox,
    QProgressBar, QStatusBar, QMenuBar, QMenu,
    QFrame, QGridLayout, QGroupBox, QSpinBox,
    QDoubleSpinBox, QDateEdit, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QDate
from PySide6.QtGui import QAction, QFont, QIcon
import pyqtgraph as pg
import pandas as pd
from datetime import datetime, timedelta

# 复用现有模块
from config import get_session_factory, get_settings
from database.models import Stock, DailyPrice, TechnicalIndicator
from collectors import AKShareCollector
from processors import TechnicalCalculator
from processors.calculators import save_indicators_to_db
from analysis import TrendAnalyzer
from analysis.risk_metrics import RiskMetrics


class DataFetchThread(QThread):
    """数据获取后台线程"""
    progress = Signal(int)
    status = Signal(str)
    finished_signal = Signal(bool, str)
    data_ready = Signal(object)
    
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
                # 检查是否已有数据
                existing = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == self.stock_code
                ).count()
                
                if existing == 0:
                    self.status.emit("从 AKShare 获取数据...")
                    collector = AKShareCollector(request_delay=0.5)
                    
                    # 获取股票信息
                    stock_info = collector.get_stock_info(self.stock_code)
                    stock = Stock(
                        stock_code=self.stock_code,
                        stock_name=stock_info.get('stock_name', self.stock_code) if stock_info else self.stock_code,
                        exchange=collector._get_exchange(self.stock_code),
                    )
                    db.merge(stock)
                    
                    # 获取历史数据
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
                    
                    # 保存数据
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
                    self.calculate_indicators(db, df)
                
                # 查询数据返回
                prices = db.query(DailyPrice).filter(
                    DailyPrice.stock_code == self.stock_code
                ).order_by(DailyPrice.trade_date.desc()).limit(self.days).all()
                
                df = pd.DataFrame([{
                    'trade_date': p.trade_date,
                    'open_price': float(p.open_price) if p.open_price else 0,
                    'high_price': float(p.high_price) if p.high_price else 0,
                    'low_price': float(p.low_price) if p.low_price else 0,
                    'close_price': float(p.close_price) if p.close_price else 0,
                    'volume': p.volume or 0,
                    'change_pct': float(p.change_pct) if p.change_pct else 0,
                } for p in reversed(prices)])
                
                self.data_ready.emit(df)
                self.finished_signal.emit(True, f"成功加载 {len(df)} 条数据")
                
            finally:
                db.close()
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))
    
    def calculate_indicators(self, db, df):
        """计算技术指标"""
        calculator = TechnicalCalculator()
        df_calc = calculator.calculate_all(df)
        save_indicators_to_db(self.stock_code, df_calc, db)


class StockAnalyzerApp(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("股票分析系统")
        self.setGeometry(100, 100, 1400, 900)
        
        self.current_df = None
        self.stock_code = None
        
        self.init_ui()
        self.init_menu()
        self.check_database()
        
    def init_ui(self):
        """初始化界面"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 右侧图表区域
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 4)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
    def create_left_panel(self):
        """创建左侧面板"""
        panel = QGroupBox("控制面板")
        layout = QVBoxLayout()
        
        # 股票代码输入
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("股票代码:"))
        self.code_input = QLineEdit("159892")
        self.code_input.setPlaceholderText("如: 159892, 000001")
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
                background-color: #1890ff;
                color: white;
                padding: 10px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #40a9ff; }
            QPushButton:pressed { background-color: #096dd9; }
        """)
        self.query_btn.clicked.connect(self.on_query)
        layout.addWidget(self.query_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 基本信息显示
        self.info_group = QGroupBox("基本信息")
        info_layout = QGridLayout()
        
        self.info_labels = {}
        fields = [
            ("最新价", "latest_price"),
            ("涨跌幅", "change_pct"),
            ("成交量", "volume"),
            ("最高", "high"),
            ("最低", "low"),
        ]
        
        for i, (label, key) in enumerate(fields):
            info_layout.addWidget(QLabel(f"{label}:"), i, 0)
            self.info_labels[key] = QLabel("-")
            self.info_labels[key].setStyleSheet("font-weight: bold; color: #1890ff;")
            info_layout.addWidget(self.info_labels[key], i, 1)
        
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)
        
        # 技术指标显示
        self.indicator_group = QGroupBox("技术指标")
        indicator_layout = QGridLayout()
        
        indicator_fields = [
            ("MA5", "ma5"), ("MA20", "ma20"), ("MA60", "ma60"),
            ("MACD DIF", "dif"), ("MACD DEA", "dea"),
            ("RSI12", "rsi"), ("K", "k"), ("D", "d"),
        ]
        
        self.indicator_labels = {}
        for i, (label, key) in enumerate(indicator_fields):
            row = i // 2
            col = (i % 2) * 2
            indicator_layout.addWidget(QLabel(f"{label}:"), row, col)
            self.indicator_labels[key] = QLabel("-")
            indicator_layout.addWidget(self.indicator_labels[key], row, col + 1)
        
        self.indicator_group.setLayout(indicator_layout)
        layout.addWidget(self.indicator_group)
        
        # 趋势分析
        self.trend_group = QGroupBox("趋势分析")
        trend_layout = QVBoxLayout()
        self.trend_text = QTextEdit()
        self.trend_text.setReadOnly(True)
        self.trend_text.setMaximumHeight(150)
        trend_layout.addWidget(self.trend_text)
        self.trend_group.setLayout(trend_layout)
        layout.addWidget(self.trend_group)
        
        # 风险指标
        self.risk_group = QGroupBox("风险指标")
        risk_layout = QGridLayout()
        
        risk_fields = [
            ("年化收益", "annual_return"),
            ("波动率", "volatility"),
            ("最大回撤", "max_dd"),
            ("夏普比率", "sharpe"),
        ]
        
        self.risk_labels = {}
        for i, (label, key) in enumerate(risk_fields):
            risk_layout.addWidget(QLabel(f"{label}:"), i // 2, (i % 2) * 2)
            self.risk_labels[key] = QLabel("-")
            risk_layout.addWidget(self.risk_labels[key], i // 2, (i % 2) * 2 + 1)
        
        self.risk_group.setLayout(risk_layout)
        layout.addWidget(self.risk_group)
        
        # 弹性空间
        layout.addStretch()
        
        # 导出按钮
        self.export_btn = QPushButton("导出数据 (CSV)")
        self.export_btn.clicked.connect(self.export_data)
        layout.addWidget(self.export_btn)
        
        panel.setLayout(layout)
        panel.setMaximumWidth(350)
        return panel
    
    def create_right_panel(self):
        """创建右侧图表面板"""
        panel = QGroupBox("K线图表")
        layout = QVBoxLayout()
        
        # 使用 PyQtGraph 创建图表
        self.plot_widget = pg.GraphicsLayoutWidget()
        
        # K线图
        self.price_plot = self.plot_widget.addPlot(row=0, col=0)
        self.price_plot.setLabel('left', '价格')
        self.price_plot.showGrid(x=True, y=True)
        
        # 成交量图
        self.volume_plot = self.plot_widget.addPlot(row=1, col=0)
        self.volume_plot.setLabel('left', '成交量')
        self.volume_plot.setLabel('bottom', '时间')
        self.volume_plot.showGrid(x=True, y=True)
        self.volume_plot.setXLink(self.price_plot)
        
        layout.addWidget(self.plot_widget)
        panel.setLayout(layout)
        return panel
    
    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        export_action = QAction("导出数据", self)
        export_action.setShortcut("Ctrl+S")
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 数据菜单
        data_menu = menubar.addMenu("数据")
        
        refresh_action = QAction("刷新数据", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.on_query)
        data_menu.addAction(refresh_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def check_database(self):
        """检查数据库连接"""
        try:
            db = get_session_factory()()
            count = db.query(Stock).count()
            self.status_bar.showMessage(f"数据库连接正常 | 已存储 {count} 只股票")
            db.close()
        except Exception as e:
            self.status_bar.showMessage(f"数据库错误: {e}")
    
    def on_query(self):
        """查询按钮点击"""
        stock_code = self.code_input.text().strip()
        if not stock_code:
            QMessageBox.warning(self, "警告", "请输入股票代码")
            return
        
        self.stock_code = stock_code
        days_text = self.days_combo.currentText()
        days = int(days_text.replace("天", ""))
        
        # 禁用按钮
        self.query_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 启动后台线程
        self.thread = DataFetchThread(stock_code, days)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.status.connect(self.status_bar.showMessage)
        self.thread.finished_signal.connect(self.on_fetch_finished)
        self.thread.data_ready.connect(self.on_data_ready)
        self.thread.start()
    
    def on_fetch_finished(self, success, message):
        """数据获取完成"""
        self.query_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_bar.showMessage(message)
        else:
            QMessageBox.critical(self, "错误", message)
    
    def on_data_ready(self, df):
        """数据准备好后更新界面"""
        self.current_df = df
        
        # 更新基本信息
        if not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            self.info_labels["latest_price"].setText(f"{latest['close_price']:.3f}")
            self.info_labels["change_pct"].setText(f"{latest['change_pct']:.2f}%")
            self.info_labels["volume"].setText(f"{latest['volume']/10000:.0f}万")
            self.info_labels["high"].setText(f"{latest['high_price']:.3f}")
            self.info_labels["low"].setText(f"{latest['low_price']:.3f}")
            
            # 更新K线图
            self.update_chart(df)
            
            # 更新分析
            self.update_analysis(df)
            
            # 更新指标
            self.update_indicators(df)
    
    def update_chart(self, df):
        """更新K线图"""
        self.price_plot.clear()
        self.volume_plot.clear()
        
        # 准备数据
        x = range(len(df))
        
        # 绘制蜡烛图简化版（用高低线表示）
        for i, row in df.iterrows():
            idx = df.index.get_loc(i)
            
            # 价格线
            color = 'r' if row['close_price'] >= row['open_price'] else 'g'
            self.price_plot.plot(
                [idx, idx], 
                [row['low_price'], row['high_price']], 
                pen=pg.mkPen(color, width=1)
            )
            # 实体
            self.price_plot.plot(
                [idx, idx],
                [row['open_price'], row['close_price']],
                pen=pg.mkPen(color, width=3)
            )
        
        # 成交量
        colors = ['r' if df.iloc[i]['close_price'] >= df.iloc[i]['open_price'] else 'g' 
                  for i in range(len(df))]
        bar_graph = pg.BarGraphItem(
            x=x, 
            height=df['volume'].values, 
            width=0.6,
            brushes=colors
        )
        self.volume_plot.addItem(bar_graph)
        
        # 设置坐标轴
        self.price_plot.autoRange()
        self.volume_plot.autoRange()
    
    def update_analysis(self, df):
        """更新趋势分析"""
        try:
            analyzer = TrendAnalyzer(df)
            result = analyzer.analyze()
            
            trend_text = f"""
趋势方向: {result.direction.value}
趋势强度: {result.strength.value}
持续天数: {result.trend_days}天
ADX: {result.adx:.2f}

分析:
{result.description}
            """
            
            if result.support_levels:
                trend_text += f"\n支撑位: {', '.join([f'{s:.3f}' for s in result.support_levels[:3]])}"
            if result.resistance_levels:
                trend_text += f"\n阻力位: {', '.join([f'{r:.3f}' for r in result.resistance_levels[:3]])}"
            
            self.trend_text.setPlainText(trend_text)
            
        except Exception as e:
            self.trend_text.setPlainText(f"趋势分析失败: {e}")
    
    def update_indicators(self, df):
        """更新技术指标"""
        # 从数据库获取最新指标
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            indicator = db.query(TechnicalIndicator).filter(
                TechnicalIndicator.stock_code == self.stock_code
            ).order_by(TechnicalIndicator.trade_date.desc()).first()
            
            if indicator:
                self.indicator_labels["ma5"].setText(f"{indicator.ma5:.3f}" if indicator.ma5 else "-")
                self.indicator_labels["ma20"].setText(f"{indicator.ma20:.3f}" if indicator.ma20 else "-")
                self.indicator_labels["ma60"].setText(f"{indicator.ma60:.3f}" if indicator.ma60 else "-")
                self.indicator_labels["dif"].setText(f"{indicator.macd_dif:.4f}" if indicator.macd_dif else "-")
                self.indicator_labels["dea"].setText(f"{indicator.macd_dea:.4f}" if indicator.macd_dea else "-")
                self.indicator_labels["rsi"].setText(f"{indicator.rsi12:.2f}" if indicator.rsi12 else "-")
                self.indicator_labels["k"].setText(f"{indicator.k_value:.2f}" if indicator.k_value else "-")
                self.indicator_labels["d"].setText(f"{indicator.d_value:.2f}" if indicator.d_value else "-")
            
            # 风险指标
            if len(df) > 30:
                returns = df['close_price'].pct_change().dropna()
                metrics = RiskMetrics(returns)
                result = metrics.calculate_all()
                
                self.risk_labels["annual_return"].setText(f"{result.annualized_return*100:.1f}%")
                self.risk_labels["volatility"].setText(f"{result.annualized_volatility*100:.1f}%")
                self.risk_labels["max_dd"].setText(f"{result.max_drawdown*100:.1f}%")
                self.risk_labels["sharpe"].setText(f"{result.sharpe_ratio:.2f}")
                
        finally:
            db.close()
    
    def export_data(self):
        """导出数据"""
        if self.current_df is None:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存数据", f"{self.stock_code}_data.csv", "CSV Files (*.csv)"
        )
        
        if file_path:
            self.current_df.to_csv(file_path, index=False)
            QMessageBox.information(self, "成功", f"数据已保存到:\n{file_path}")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            "股票分析系统 v2.0\n\n"
            "基于 PySide6 开发的跨平台桌面应用\n"
            "支持 Windows 和 macOS"
        )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("股票分析系统")
    app.setStyle('Fusion')
    
    # 设置全局字体
    font = QFont("Microsoft YaHei" if sys.platform == 'win32' else "PingFang SC", 10)
    app.setFont(font)
    
    window = StockAnalyzerApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
