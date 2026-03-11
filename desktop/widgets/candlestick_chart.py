# -*- coding: utf-8 -*-
"""
K线图组件 - 支持蜡烛图、均线、成交量
"""
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
import numpy as np
import pandas as pd


class CandlestickItem(pg.GraphicsObject):
    """蜡烛图绘制项"""
    
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data
        self.generatePicture()
    
    def generatePicture(self):
        """生成绘制图片"""
        self.picture = pg.QtGui.QPicture()
        p = pg.QtGui.QPainter(self.picture)
        
        w = 0.3
        
        for (t, open_price, high, low, close) in self.data:
            if close >= open_price:
                p.setPen(pg.mkPen('red', width=1))
                p.setBrush(pg.mkBrush('red'))
            else:
                p.setPen(pg.mkPen('green', width=1))
                p.setBrush(pg.mkBrush('green'))
            
            p.drawRect(pg.QtCore.QRectF(t-w, open_price, w*2, close-open_price))
            p.drawLine(pg.QtCore.QPointF(t, low), pg.QtCore.QPointF(t, high))
        
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        return pg.QtCore.QRectF(self.picture.boundingRect())


class CandlestickChart(QWidget):
    """K线图组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.graphics_layout)
        
        self.price_plot = self.graphics_layout.addPlot(row=0, col=0)
        self.price_plot.setMenuEnabled(False)
        self.price_plot.setLabel('left', '价格')
        self.price_plot.showGrid(x=True, y=True)
        
        self.volume_plot = self.graphics_layout.addPlot(row=1, col=0)
        self.volume_plot.setMenuEnabled(False)
        self.volume_plot.setLabel('left', '成交量')
        self.volume_plot.setLabel('bottom', '日期')
        self.volume_plot.showGrid(x=True, y=True)
        self.volume_plot.setXLink(self.price_plot)
        
        self.macd_plot = self.graphics_layout.addPlot(row=2, col=0)
        self.macd_plot.setMenuEnabled(False)
        self.macd_plot.setLabel('left', 'MACD')
        self.macd_plot.showGrid(x=True, y=True)
        self.macd_plot.setXLink(self.price_plot)
        
        self.graphics_layout.ci.layout.setRowStretchFactor(0, 3)
        self.graphics_layout.ci.layout.setRowStretchFactor(1, 1)
        self.graphics_layout.ci.layout.setRowStretchFactor(2, 1)
        
        self.df = None
        
    def update_chart(self, df, indicators=None):
        """更新图表"""
        self.df = df
        if df is None or df.empty:
            return
        
        self.price_plot.clear()
        self.volume_plot.clear()
        self.macd_plot.clear()
        
        x_data = np.arange(len(df))
        
        candle_data = []
        for i, row in df.iterrows():
            candle_data.append((
                i, row['open_price'], row['high_price'],
                row['low_price'], row['close_price']
            ))
        
        self.candle_item = CandlestickItem(candle_data)
        self.price_plot.addItem(self.candle_item)
        
        # 均线
        if indicators:
            for period, color in [(5, '#FFD700'), (20, '#00CED1'), (60, '#FF69B4')]:
                ma_data = df['close_price'].rolling(window=period, min_periods=1).mean()
                self.price_plot.plot(x_data, ma_data, pen=pg.mkPen(color, width=2))
        
        # 成交量
        colors = ['red' if df.iloc[i]['close_price'] >= df.iloc[i]['open_price'] else 'green'
                  for i in range(len(df))]
        bar_item = pg.BarGraphItem(x=x_data, height=df['volume'].values, width=0.6, brushes=colors)
        self.volume_plot.addItem(bar_item)
        
        # MACD
        if 'macd_dif' in df.columns:
            self.macd_plot.plot(x_data, df['macd_dif'], pen=pg.mkPen('yellow', width=1.5))
            self.macd_plot.plot(x_data, df['macd_dea'], pen=pg.mkPen('blue', width=1.5))
        
        self.price_plot.autoRange()
        self.volume_plot.autoRange()
        self.macd_plot.autoRange()


class BacktestChart(QWidget):
    """回测结果图表"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.graphics_layout)
        
        self.equity_plot = self.graphics_layout.addPlot(row=0, col=0, title='净值曲线')
        self.equity_plot.showGrid(x=True, y=True)
        
        self.drawdown_plot = self.graphics_layout.addPlot(row=1, col=0, title='回撤曲线')
        self.drawdown_plot.showGrid(x=True, y=True)
        self.drawdown_plot.setXLink(self.equity_plot)
    
    def update_backtest(self, results):
        """更新回测图表"""
        self.equity_plot.clear()
        self.drawdown_plot.clear()
        
        if not results or 'daily_values' not in results:
            return
        
        daily_values = results['daily_values']
        if not daily_values:
            return
        
        x_data = np.arange(len(daily_values))
        total_values = [v['total_value'] for v in daily_values]
        
        self.equity_plot.plot(x_data, total_values, pen=pg.mkPen('#1890ff', width=2))
        
        peak = total_values[0]
        drawdowns = []
        for v in total_values:
            if v > peak:
                peak = v
            drawdowns.append((v - peak) / peak * 100)
        
        self.drawdown_plot.plot(x_data, drawdowns, pen=pg.mkPen('red', width=1), fillLevel=0, brush=pg.mkBrush(255, 0, 0, 50))
