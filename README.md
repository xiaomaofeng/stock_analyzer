# 股票分析系统 - Web版

基于 Streamlit 的股票分析 Web 应用。

## 功能

- **🔍 股票查询** - 输入代码获取数据，自动计算技术指标，显示K线图
- **🔄 策略回测** - 均线/RSI/MACD策略回测，查看净值曲线

## 快速启动

```bash
# 启动 Web 服务
start.bat

# 或
launch.bat
```

访问 http://localhost:8501

## 项目结构

```
stock_db/
├── web/
│   ├── app.py              # 主入口
│   └── pages/
│       ├── stock_query.py  # 股票查询
│       └── backtest.py     # 策略回测
├── collectors/             # 数据采集
├── processors/             # 指标计算
├── analysis/               # 趋势/风险分析
├── backtest/               # 回测引擎
└── database/               # 数据模型
```

## 依赖安装

```bash
pip install -r requirements.txt
```

主要依赖：streamlit, plotly, pandas, sqlalchemy, akshare
