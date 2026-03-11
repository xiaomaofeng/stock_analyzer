# 股票分析系统 / Stock Analyzer

支持 Web (Streamlit) 和 Desktop (PySide6) 双版本，中英双语界面。

## 功能模块 / Features

| 模块 / Module | 描述 / Description |
|--------------|-------------------|
| 🔍 股票查询 / Stock Query | 获取数据、技术指标、趋势分析 |
| 📊 仪表盘 / Dashboard | 数据库统计、股票列表 |
| 📈 个股分析 / Stock Viewer | K线图、详细指标、风险评估 |
| 🔄 策略回测 / Backtest | 均线/RSI/MACD策略回测 |
| 🔎 股票筛选 / Screener | 多条件筛选股票 |

## 快速启动 / Quick Start

### Web 版本 / Web Version
```bash
# 启动 / Start
start.bat

# 或 / Or
launch.bat
```
访问 / Visit: http://localhost:8501

### Desktop 版本 / Desktop Version
```bash
# 运行 / Run
python desktop/main.py

# 打包 Windows EXE / Build Windows EXE
cd desktop
python build_exe.py
```

## 项目结构 / Project Structure

```
stock_db/
├── web/                      # Web 版本 (Streamlit)
│   ├── app.py               # 主入口 / Main entry
│   └── pages/               # 功能页面 / Pages
│       ├── stock_query.py   # 股票查询
│       ├── dashboard.py     # 仪表盘
│       ├── stock_viewer.py  # 个股分析
│       ├── backtest.py      # 策略回测
│       └── screener.py      # 股票筛选
├── desktop/                  # Desktop 版本 (PySide6)
│   ├── main.py              # 主程序
│   ├── styles/              # UI 样式
│   └── widgets/             # 自定义组件
├── collectors/              # 数据采集
├── processors/              # 指标计算
├── analysis/                # 趋势/风险分析
├── backtest/                # 回测引擎
└── database/                # 数据模型
```

## 依赖安装 / Install Dependencies

```bash
pip install -r requirements.txt
```

## 多语言 / Multi-language

- 🇨🇳 中文 (默认 / Default)
- 🇺🇸 English

语言切换在界面侧边栏 / Language switch in sidebar

## 双版本维护 / Dual Version Maintenance

同时维护 Web 和 Desktop 两个版本：
- **Web**: 快速迭代、易于分享
- **Desktop**: 原生体验、可离线使用

根据后续需求确定最终保留版本。
