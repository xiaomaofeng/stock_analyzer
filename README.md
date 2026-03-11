# 股票分析系统 v2.0 - 桌面版

基于 PySide6 开发的跨平台股票分析桌面应用，支持 Windows 和 macOS。

## 特性

- 📊 **专业K线图** - 蜡烛图 + 均线(MA5/20/60) + MACD + 成交量
- 🔍 **股票查询** - 自动从AKShare获取数据，本地SQLite存储
- 📈 **技术分析** - 趋势分析、支撑阻力、风险指标(夏普比率、最大回撤等)
- 🔄 **策略回测** - 均线/RSI/MACD策略回测，可视化净值曲线
- 💾 **数据导出** - 支持CSV导出
- 🖥️ **跨平台** - Windows(.exe) 和 macOS(.app) 原生应用

## 快速开始

### 安装依赖

```bash
cd F:\Dev\FinanceReport\stock_db
pip install -r requirements.txt
```

### 运行桌面应用

```bash
python desktop/main.py
```

### 打包分发

```bash
cd desktop

# Windows
python build.py --platform windows

# macOS
python build.py --platform macos
```

## 项目结构

```
stock_db/
├── desktop/               # 桌面应用
│   ├── main.py           # 主程序入口
│   ├── widgets/          # 自定义组件
│   │   └── candlestick_chart.py  # K线图组件
│   ├── build.py          # 打包脚本
│   └── requirements.txt  # 桌面应用依赖
├── collectors/           # 数据采集 (AKShare)
├── processors/           # 指标计算
├── analysis/             # 趋势/风险分析
├── backtest/             # 回测引擎
│   ├── engine.py
│   └── strategies/       # 策略库
│       ├── ma_strategy.py
│       ├── rsi_strategy.py
│       └── macd_strategy.py
├── database/             # 数据模型和存储
├── config/               # 配置管理
└── data/                 # SQLite数据库
```

## 功能说明

### 股票查询
- 输入股票代码，自动获取历史数据
- 实时计算技术指标(MACD、RSI、KDJ、均线等)
- 趋势方向判断、支撑阻力位
- 风险指标分析(年化收益、波动率、夏普比率、最大回撤)

### 策略回测
- 均线交叉策略
- RSI超买超卖策略
- MACD金叉死叉策略
- 显示净值曲线、回撤曲线
- 交易记录明细

## 技术栈

- **GUI框架**: PySide6 (Qt6)
- **图表库**: PyQtGraph
- **数据库**: SQLite + SQLAlchemy
- **数据源**: AKShare
- **打包工具**: PyInstaller

## 开发计划

- [x] 基础K线图
- [x] 股票查询与分析
- [x] 技术指标计算
- [x] 回测功能
- [ ] 多股票监控
- [ ] 实时行情推送
- [ ] 自动更新

## 许可证

MIT
