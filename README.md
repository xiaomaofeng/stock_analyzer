# 📈 股票分析系统 / Stock Analyzer

> 一个支持 Web 和 Desktop 双版本的股票分析工具，提供实时数据获取、技术指标计算、趋势分析和策略回测功能。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Cross Platform">
</p>

<p align="center">
  <b>🇨🇳 中文</b> | <b>🇺🇸 English</b> | Web + Desktop | 完全免费
</p>

---

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 🔍 **股票查询** | 输入代码自动获取数据，支持 A 股、ETF 等 |
| 📊 **技术指标** | MA、MACD、RSI、KDJ、布林带等完整计算 |
| 📚 **指标学习** | 内置指标教程，新手也能看懂 |
| 📈 **趋势分析** | 自动判断趋势方向、支撑阻力位 |
| 🔄 **策略回测** | 均线/RSI/MACD 策略回测，验证交易思路 |
| 🔎 **股票筛选** | 多条件筛选，找出符合条件的股票 |
| 🌐 **双语界面** | 一键切换中文/英文 |

---

## 🚀 快速开始

### 方式一：使用管理脚本（推荐）

```bash
# 安装依赖
python manage.py install

# 启动 Web 版本（浏览器访问 http://localhost:8501）
python manage.py web

# 或启动 Desktop 版本
python manage.py desktop
```

### 方式二：双击运行（Windows）

| 脚本 | 功能 |
|------|------|
| 🔧 `install.bat` | 一键安装所有依赖 |
| 🌐 `start-web.bat` | 启动 Web 版本 |
| 💻 `start-desktop.bat` | 启动 Desktop 版本 |

### 方式三：终端运行（macOS/Linux）

```bash
# 给脚本添加执行权限
chmod +x *.sh

# 安装并启动
./install.sh
./start-web.sh
```

---

## 📖 详细命令

```bash
python manage.py web [PORT]      # 启动 Web 版本（默认端口 8501）
python manage.py desktop         # 启动 Desktop 版本
python manage.py install         # 安装/更新依赖
python manage.py build           # 打包 Desktop 可执行文件
python manage.py clean           # 清理缓存文件
python manage.py test            # 运行测试
python manage.py init-db         # 初始化数据库
```

---

## 📁 项目结构

```
stock_db/
├── 📜 manage.py              # 统一管理脚本（主入口）
├── 🌐 web/                   # Web 版本 (Streamlit)
│   ├── app.py
│   └── pages/
│       ├── stock_query.py    # 股票查询 + 指标学习
│       ├── dashboard.py      # 数据仪表盘
│       ├── stock_viewer.py   # 个股分析
│       ├── backtest.py       # 策略回测
│       └── screener.py       # 股票筛选
│
├── 💻 desktop/               # Desktop 版本 (PySide6)
│   ├── main.py
│   ├── styles/               # UI 样式
│   └── widgets/              # 图表组件
│
├── 🔧 collectors/            # 数据采集 (AKShare)
├── 🧮 processors/            # 指标计算引擎
├── 📊 analysis/              # 趋势/风险分析
├── 🎲 backtest/              # 回测引擎
└── 🗄️ database/              # SQLite 数据库
```

---

## 🛠️ 技术栈

- **Web 框架**: [Streamlit](https://streamlit.io/) - 快速构建数据应用
- **Desktop 框架**: [PySide6](https://doc.qt.io/qtforpython/) - Qt for Python
- **数据源**: [AKShare](https://www.akshare.xyz/) - 开源财经数据接口
- **图表**: [Plotly](https://plotly.com/python/) / [PyQtGraph](https://pyqtgraph.org/)
- **数据库**: SQLite + SQLAlchemy

---

## 🌍 多语言支持

系统支持 **中文** 和 **英文** 一键切换：

- 在界面侧边栏选择语言
- 指标学习文档也会自动切换

---

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源，可自由使用和修改。

---

## ⭐ 支持项目

如果这个项目对你有帮助，请给它一个 **Star**！

<p align="center">
  <a href="https://github.com/xiaomaofeng/stock_analyzer">
    <img src="https://img.shields.io/github/stars/xiaomaofeng/stock_analyzer?style=social" alt="GitHub Stars">
  </a>
</p>

你的支持是我持续更新的动力！❤️

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/xiaomaofeng">xiaomaofeng</a>
</p>
