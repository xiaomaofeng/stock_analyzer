# 股票分析系统 / Stock Analyzer

支持 Web (Streamlit) 和 Desktop (PySide6) 双版本，中英双语界面。

## 快速开始 / Quick Start

### 统一入口 / Unified Entry

```bash
# 查看所有命令
python manage.py --help

# 安装依赖
python manage.py install

# 启动 Web 版本
python manage.py web

# 启动 Desktop 版本  
python manage.py desktop

# 构建 Desktop 可执行文件
python manage.py build

# 清理缓存
python manage.py clean
```

### 平台特定脚本 / Platform Scripts

#### Windows (双击运行)
| 脚本 | 功能 |
|------|------|
| `install.bat` | 安装依赖 |
| `start-web.bat` | 启动 Web 版本 |
| `start-desktop.bat` | 启动 Desktop 版本 |

#### macOS / Linux
```bash
# 给脚本添加执行权限
chmod +x *.sh

# 安装依赖
./install.sh

# 启动 Web
./start-web.sh

# 启动 Desktop
./start-desktop.sh
```

## 功能模块 / Features

| 模块 | 描述 |
|------|------|
| 🔍 股票查询 | 输入代码获取数据、技术指标、趋势分析、指标学习 |
| 📊 仪表盘 | 查看已存储的股票数据概览 |
| 📈 个股分析 | K线图、详细指标、风险评估 |
| 🔄 策略回测 | 均线/RSI/MACD策略回测 |
| 🔎 股票筛选 | 多条件筛选已存储的股票 |

## 项目结构 / Project Structure

```
stock_db/
├── manage.py                 # 统一管理脚本 (主入口)
├── start-web.bat/.sh         # 启动 Web (快捷方式)
├── start-desktop.bat/.sh     # 启动 Desktop (快捷方式)
├── install.bat/.sh           # 安装依赖 (快捷方式)
│
├── web/                      # Web 版本 (Streamlit)
│   ├── app.py
│   └── pages/
│       ├── stock_query.py    # 股票查询 + 指标学习
│       ├── dashboard.py
│       ├── stock_viewer.py
│       ├── backtest.py
│       └── screener.py
│
├── desktop/                  # Desktop 版本 (PySide6)
│   ├── main.py
│   ├── styles/
│   └── widgets/
│
├── collectors/               # 数据采集 (AKShare)
├── processors/               # 指标计算 (完整版)
├── analysis/                 # 趋势/风险分析
├── backtest/                 # 回测引擎
└── database/                 # 数据模型 (SQLite)
```

## 多语言 / Multi-language

- 🇨🇳 中文 (默认)
- 🇺🇸 English

语言切换在界面侧边栏

## 技术特点

- **跨平台**: Windows / macOS / Linux
- **统一入口**: 单脚本管理所有操作
- **完整指标计算**: MACD、ADX、RSI、KDJ 等使用标准算法
- **双语支持**: 界面和学习内容都支持中英文切换
- **双版本**: Web 易于分享，Desktop 原生体验

## 开发命令

```bash
# 运行测试
python manage.py test

# 初始化数据库
python manage.py init-db

# 清理所有缓存
python manage.py clean
```
