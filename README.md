# 📈 股票分析系统 - 自动化部署版

[![CI](https://github.com/xiaomaofeng/stock_analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/xiaomaofeng/stock_analyzer/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://github.com/xiaomaofeng/stock_analyzer/pkgs/container/stock_analyzer)
[![Deploy](https://img.shields.io/badge/Deploy-Automated-green)](DEPLOY.md)

基于 Python + AKShare 的股票数据分析系统，**一键部署**，部署完成即可通过网页查看 159892 等股票的真实数据分析。

## 🚀 一键部署（3分钟完成）

### Windows (PowerShell)
```powershell
git clone https://github.com/xiaomaofeng/stock_analyzer.git
cd stock_analyzer
.\deploy.ps1
```

### macOS / Linux
```bash
git clone https://github.com/xiaomaofeng/stock_analyzer.git
cd stock_analyzer
chmod +x deploy.sh
./deploy.sh
```

部署完成后访问：**http://localhost:8501**

---

## ✨ 功能特性

### 📊 自动导入数据
部署时自动导入 **159892 (恒生互联网ETF)** 等 15 只股票的真实历史数据。

### 🔢 40+ 技术指标
- **趋势**: MA, MACD, DMI, SAR
- **动量**: RSI, KDJ, ROC, MTM, CCI, Williams %R
- **量能**: OBV, CMF, MFI
- **波动**: 布林带, ATR
- **情绪**: PSY

### 📈 多因子策略分析
综合评分系统，从趋势、动量、量能、情绪四个维度给出买卖建议。

### 🔄 自动更新
每日定时自动更新数据并重新计算指标。

---

## 📋 详细部署指南

查看完整部署文档：[DEPLOY.md](DEPLOY.md)

### 部署方式对比

| 方式 | 命令 | 适用场景 |
|------|------|----------|
| **一键脚本** | `./deploy.sh` | 本地快速部署 |
| **Docker** | `docker-compose up` | 简单体验 |
| **生产部署** | `docker-compose -f docker-compose.prod.yml up` | 完整功能 |
| **云服务器** | SSH + `./deploy.sh` | 公网访问 |

---

## 🖥️ 系统预览

### 主界面
- K线图表（含均线、布林带）
- 成交量分析
- 实时技术指标

### 159892 专用分析
- ETF净值走势
- 港股互联网板块分析
- 多因子评分系统

### 数据面板
- 日线数据表格
- 指标历史数据
- CSV导出功能

---

## 🗄️ 包含股票数据

部署后立即可查看：

| 代码 | 名称 | 备注 |
|------|------|------|
| **159892** | 华夏恒生互联网ETF | ⭐ 主分析对象 |
| 000001 | 平安银行 | 银行股代表 |
| 000333 | 美的集团 | 家电龙头 |
| 600519 | 贵州茅台 | 白酒龙头 |
| ... | 共15只 | 覆盖多行业 |

**数据自动更新**：每日收盘后自动获取最新数据。

---

## 🔧 技术架构

```
┌─────────────────────────────────────────┐
│           Docker Containers             │
│  ┌─────────┐  ┌──────────┐  ┌────────┐ │
│  │   Web   │  │ PostgreSQL│  │Scheduler│
│  │Streamlit│  │  (Data)  │  │ (Cron) │ │
│  │ :8501   │  │  :5432   │  │        │ │
│  └────┬────┘  └────┬─────┘  └────────┘ │
│       │            │                   │
│       └────────────┘                   │
│            自动数据初始化               │
│       (导入159892 + 计算指标)          │
└─────────────────────────────────────────┘
```

---

## 📁 项目结构

```
stock_analyzer/
├── 📄 deploy.sh / deploy.ps1    # 一键部署脚本 ⭐
├── 📄 docker-compose.prod.yml   # 生产环境配置
├── 📄 DEPLOY.md                 # 部署文档
├── 📁 web/                      # Streamlit界面
├── 📁 scripts/                  # 数据导入/计算脚本
│   ├── auto_import.py          # 自动导入股票数据
│   └── auto_calc_indicators.py # 自动计算技术指标
├── 📁 collectors/               # AKShare数据采集
├── 📁 processors/               # 40+技术指标计算
├── 📁 analysis/                 # 趋势/归因/风险分析
└── 📁 backtest/                 # 策略回测框架
```

---

## 🛠️ 开发环境

如需本地开发调试：

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python scripts/init_db.py

# 3. 导入数据
python scripts/import_stock_data.py --code 159892 --start 2023-01-01

# 4. 计算指标
python scripts/calc_indicators.py --code 159892

# 5. 启动Web
cd web && streamlit run app.py
```

---

## ⚙️ 配置说明

### 修改初始股票

编辑 `docker-compose.prod.yml`：
```yaml
environment:
  - INIT_STOCKS=159892,000001,000333  # 添加你想要的股票
```

### 修改数据库密码

编辑 `.env`：
```bash
DB_PASSWORD=YourStrongPassword123!
```

### 修改端口

编辑 `.env`：
```bash
WEB_PORT=8080
```

---

## 🤝 使用说明

### 查看159892分析

1. 访问 http://localhost:8501
2. 在侧边栏选择 "159892 恒生互联网ETF"
3. 查看：
   - K线走势与技术指标
   - MACD/RSI/KDJ/OBV 图表
   - 多因子策略评分
   - 买卖信号建议

### 数据更新

系统自动更新，也可手动触发：
```bash
docker-compose -f docker-compose.prod.yml exec web python scripts/daily_update.py
```

---

## 📊 技术栈

- **数据采集**: AKShare (免费)
- **数据库**: PostgreSQL / SQLite
- **ORM**: SQLAlchemy + Alembic
- **Web界面**: Streamlit + Plotly
- **容器化**: Docker + Docker Compose
- **调度**: APScheduler

---

## 🔒 安全提示

1. **修改默认密码**：部署后请修改 `DB_PASSWORD`
2. **防火墙配置**：生产环境只开放必要端口
3. **HTTPS**：公网访问请配置 SSL

---

## 📞 获取帮助

- 部署问题：[DEPLOY.md](DEPLOY.md)
- 详细文档：[QUICKSTART.md](QUICKSTART.md)
- 提交 Issue：https://github.com/xiaomaofeng/stock_analyzer/issues

---

⭐ 如果这个项目对你有帮助，请给个 Star！
