# 📈 个人股票数据库系统

[![CI](https://github.com/yourusername/stock_db/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/stock_db/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://github.com/yourusername/stock_db/pkgs/container/stock_db)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)

基于 Python + AKShare 的跨平台股票数据分析系统，支持 A股/港股/美股 数据采集、多因子技术指标分析、趋势归因分析和策略回测。

## ✨ 功能特性

### 📊 数据采集
- **免费数据源**: 基于 AKShare 无需付费
- **多市场支持**: A股、港股、美股
- **自动更新**: 支持定时任务每日更新

### 🔢 技术指标 (40+)
- **趋势指标**: MA, EMA, MACD, DMI, SAR
- **动量指标**: RSI, KDJ, ROC, MTM, CCI, Williams %R
- **成交量指标**: OBV, CMF, MFI
- **波动率指标**: 布林带, ATR
- **情绪指标**: PSY
- **其他**: TRIX

### 📈 分析功能
- **趋势分析**: ADX趋势强度、支撑阻力、形态识别
- **归因分析**: CAPM、多因子归因、Brinson模型
- **风险分析**: 夏普比率、VaR、CVaR、最大回撤
- **多因子策略**: 综合评分系统 (趋势/动量/量能/情绪)

### 🔄 回测框架
- **策略类型**: 多因子策略、均值回归、趋势跟踪
- **参数优化**: 网格搜索最优参数
- **完整报告**: 收益、风险、交易记录

### 🌐 Web界面 (Streamlit)
- **仪表盘**: 市场概览、热门股票
- **个股分析**: K线图、技术指标可视化
- **智能筛选**: 多条件股票筛选器
- **策略回测**: 可视化回测结果

## 🚀 快速开始

### 方式一：本地安装

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/stock_db.git
cd stock_db

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化
python scripts/setup.py

# 4. 导入数据
python scripts/import_stock_data.py --code 000001 --start 2023-01-01

# 5. 启动Web界面
cd web && streamlit run app.py
```

### 方式二：Docker (推荐跨平台)

```bash
# 使用 Docker Compose 启动
docker-compose up -d

# 或使用 Makefile
make docker-build
make docker-run
```

### 方式三：GitHub Codespaces / Gitpod

点击按钮一键启动云端开发环境：

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=yourusername/stock_db)

## 📁 项目结构

```
stock_db/
├── 📁 config/              # 配置管理 (支持多数据库/跨平台)
├── 📁 database/            # 数据库模型 & 迁移
├── 📁 collectors/          # 数据采集 (AKShare)
├── 📁 processors/          # 数据处理 (40+ 技术指标)
│   ├── calculators.py      # 基础指标
│   └── advanced_indicators.py  # 高级指标
├── 📁 analysis/            # 分析模块
│   ├── trend_analyzer.py   # 趋势分析
│   ├── attribution.py      # 归因分析
│   └── risk_metrics.py     # 风险指标
├── 📁 backtest/            # 回测框架
│   ├── engine.py
│   └── strategies/         # 策略库
│       └── strategy_base.py # 多因子策略
├── 📁 web/                 # Streamlit界面
├── 📁 scheduler/           # 定时任务 & 监控
├── 📁 scripts/             # 工具脚本
├── 📄 docker-compose.yml   # Docker编排
├── 📄 Dockerfile           # Docker镜像
├── 📄 Makefile             # 跨平台命令
└── 📄 requirements.txt     # 依赖列表
```

## 🗄️ 数据库支持

### SQLite (默认) - 本地开发
```bash
# 无需配置，开箱即用
DATABASE_URL=sqlite:///./data/stock_db.sqlite
```

### PostgreSQL - 团队共享 (推荐)

```bash
# 1. 安装驱动
pip install psycopg2-binary

# 2. 配置 .env
DATABASE_URL=postgresql://user:password@localhost:5432/stock_db

# 3. 使用 Docker 启动 PostgreSQL
docker-compose --profile postgres up -d

# 4. 数据库迁移
python scripts/db_migrate.py migrate
python scripts/db_migrate.py upgrade
```

### MySQL - 企业环境

```bash
# 安装驱动
pip install pymysql

# 配置 .env
DATABASE_URL=mysql://user:password@localhost:3306/stock_db
```

## 🔧 跨平台支持

| 平台 | 支持 | 说明 |
|------|------|------|
| Windows | ✅ | PowerShell / CMD / Git Bash |
| macOS | ✅ | Terminal / iTerm2 |
| Linux | ✅ | Bash / Zsh |
| Docker | ✅ | 所有平台 |

### 跨平台命令 (Makefile)

```bash
# 所有平台通用
make install          # 安装依赖
make init             # 初始化项目
make db-init          # 初始化数据库
make run-web          # 启动Web界面
make docker-build     # 构建Docker镜像
```

## 📊 使用示例

### 批量导入股票数据

```bash
# 编辑股票列表
vim scripts/stock_list.txt

# 批量导入
python scripts/import_stock_data.py --batch --file scripts/stock_list.txt --start 2022-01-01
```

### 计算高级技术指标

```bash
# 计算所有指标
python scripts/calc_indicators.py --code 000001

# 查看信号
python scripts/calc_indicators.py --code 000001 --show
```

### 多因子策略分析

```python
from backtest.strategies import MultiFactorStrategy

# 创建策略
strategy = MultiFactorStrategy({
    'weight_trend': 0.3,
    'weight_momentum': 0.3,
    'weight_volume': 0.2,
    'weight_sentiment': 0.2
})

# 分析信号
signal = strategy.analyze(df)
print(f"信号: {signal.signal.value}, 评分: {signal.score}")
print(f"原因: {signal.reason}")

# 参数优化
from backtest.strategies import ParameterOptimizer

optimizer = ParameterOptimizer(strategy, df)
best_params, best_score = optimizer.grid_search('sharpe')
print(f"最优参数: {best_params}")
```

### 定时任务设置

**Linux/Mac (crontab)**:
```bash
# 每天17:00更新数据
0 17 * * * cd /path/to/stock_db && python scripts/daily_update.py
```

**Windows (任务计划程序)**:
```powershell
# 使用 PowerShell 创建任务
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "scripts/daily_update.py" -WorkingDirectory "C:\path\to\stock_db"
$trigger = New-ScheduledTaskTrigger -Daily -At 17:00
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "StockDB_DailyUpdate"
```

## 🔐 安全配置

### GitHub上传前必做

1. **复制环境变量文件**
   ```bash
   cp .env.example .env
   # 编辑 .env 填入你的配置
   ```

2. **确保敏感信息不提交**
   - `.env` 已在 `.gitignore` 中
   - 数据库密码只保存在本地

3. **PostgreSQL密码管理**
   ```bash
   # 生成随机密码
   openssl rand -base64 32
   
   # 写入 .env，不要提交到Git
   echo "DB_PASSWORD=your_random_password" >> .env
   ```

## 🧪 测试

```bash
# 运行测试
make test

# 代码检查
make lint
```

## 🐳 Docker部署

### 本地开发

```bash
# 构建并运行
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止
docker-compose down
```

### 生产部署 (使用 PostgreSQL)

```bash
# 启动完整环境
docker-compose --profile postgres up -d

# 数据库迁移
docker-compose exec app python scripts/db_migrate.py upgrade
```

### 使用 GitHub Container Registry

```bash
# 拉取镜像
docker pull ghcr.io/yourusername/stock_db:latest

# 运行
docker run -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env \
  ghcr.io/yourusername/stock_db:latest
```

## 📝 技术栈

| 类别 | 技术 |
|------|------|
| **数据库** | SQLite / PostgreSQL / MySQL (SQLAlchemy + Alembic) |
| **数据采集** | AKShare (免费) |
| **数据处理** | Pandas, NumPy |
| **技术指标** | 自定义实现 (40+ 指标) |
| **Web界面** | Streamlit, Plotly |
| **任务调度** | APScheduler |
| **容器化** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [AKShare](https://www.akshare.xyz/) - 免费财经数据接口
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM框架
- [Streamlit](https://streamlit.io/) - Web应用框架

---

⭐ 如果这个项目对你有帮助，请给个 Star！
