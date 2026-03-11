# 快速开始指南

## 📦 安装依赖

```bash
cd f:\Dev\FinanceReport\stock_db
pip install -r requirements.txt
```

## 🚀 一键初始化

```bash
python scripts/setup.py
```

这会：
1. 创建必要的目录
2. 初始化数据库
3. 创建环境配置文件

## 📥 导入数据

### 单只股票
```bash
python scripts/import_stock_data.py --code 000001 --start 2023-01-01
```

### 批量导入
```bash
# 使用示例列表
python scripts/import_stock_data.py --batch --file scripts/stock_list.txt

# 或创建自己的列表文件，每行一个股票代码
```

## 🔢 计算技术指标

```bash
# 单只股票
python scripts/calc_indicators.py --code 000001

# 查看最新指标
python scripts/calc_indicators.py --code 000001 --show

# 所有股票
python scripts/calc_indicators.py --all
```

## 📊 数据分析

```bash
# 趋势分析
python scripts/analyze_stock.py --code 000001 --trend

# 风险分析
python scripts/analyze_stock.py --code 000001 --risk

# 归因分析
python scripts/analyze_stock.py --code 000001 --attr

# 全部分析
python scripts/analyze_stock.py --code 000001 --all
```

## 🔍 数据查询

```bash
# 查看股票列表
python scripts/query_data.py --list

# 查询股票数据
python scripts/query_data.py --code 000001 --limit 20

# 查看数据库统计
python scripts/query_data.py --stats

# 导出到CSV
python scripts/query_data.py --code 000001 --export data.csv
```

## ✅ 数据质量检查

```bash
# 检查单只股票
python scripts/check_quality.py --code 000001

# 检查所有股票
python scripts/check_quality.py --all
```

## 🔄 每日更新

```bash
# 更新所有股票
python scripts/daily_update.py

# 更新单只股票
python scripts/daily_update.py --code 000001

# 更新股票信息
python scripts/daily_update.py --info
```

## 🌐 启动Web界面

```bash
cd web
streamlit run app.py
```

然后访问 http://localhost:8501

功能包括：
- 📊 仪表盘：市场概览、热门股票
- 📈 个股分析：K线图、技术指标、趋势分析
- 🔍 股票筛选：多条件筛选
- 🔄 回测：策略回测

## ⏰ 设置定时任务

### Windows 任务计划程序

1. 创建基本任务
2. 触发器：每天 17:00
3. 操作：启动程序
   - 程序: `python.exe`
   - 参数: `scripts/daily_update.py`
   - 起始于: `f:\Dev\FinanceReport\stock_db`

### Linux/Mac (crontab)

```bash
# 编辑crontab
crontab -e

# 添加以下行（每天17:00执行）
0 17 * * * cd /path/to/stock_db && python scripts/daily_update.py >> logs/cron.log 2>&1
```

## 🏥 健康检查

```bash
# 运行健康检查
python scheduler/monitor.py
```

## 📁 项目结构

```
stock_db/
├── config/              # 配置管理
├── database/            # 数据库模型
├── collectors/          # 数据采集 (AKShare)
├── processors/          # 数据处理 (指标计算)
├── analysis/            # 分析模块 (趋势、归因、风险)
├── backtest/            # 回测框架
├── web/                 # Streamlit界面
├── scheduler/           # 定时任务、监控
├── scripts/             # 工具脚本
│   ├── setup.py         # 一键初始化
│   ├── init_db.py       # 初始化数据库
│   ├── import_stock_data.py  # 导入数据
│   ├── calc_indicators.py    # 计算指标
│   ├── daily_update.py       # 每日更新
│   ├── query_data.py         # 查询数据
│   ├── analyze_stock.py      # 分析股票
│   ├── check_quality.py      # 质量检查
│   └── stock_list.txt        # 示例股票列表
├── data/                # 数据目录
│   ├── raw/            # 原始数据
│   ├── processed/      # 处理后数据
│   └── cache/          # 缓存
└── logs/               # 日志目录
```

## 🔧 配置说明

编辑 `.env` 文件可配置：

```bash
# 数据库 (默认SQLite)
DATABASE_URL=sqlite:///./data/stock_db.sqlite

# AKShare请求设置
AKSHARE_REQUEST_DELAY=0.5  # 请求间隔，防止被封
AKSHARE_MAX_RETRIES=3      # 最大重试次数

# 回测配置
INITIAL_CAPITAL=1000000    # 初始资金
COMMISSION_RATE=0.0003     # 手续费率
SLIPPAGE=0.0001            # 滑点
```

## 💡 使用建议

1. **首次使用**：运行 `python scripts/setup.py` 初始化
2. **导入关注股票**：编辑 `scripts/stock_list.txt` 批量导入
3. **每日更新**：设置定时任务自动更新收盘数据
4. **定期计算指标**：数据更新后计算技术指标
5. **健康检查**：定期运行 `scheduler/monitor.py` 检查数据质量

## 🐛 常见问题

### 1. AKShare请求失败
- 检查网络连接
- 增加请求间隔 `AKSHARE_REQUEST_DELAY=1.0`
- 稍后重试（可能是数据源临时问题）

### 2. 数据库锁定
SQLite不支持并发写入，确保只有一个进程在写入数据

### 3. 内存不足
- 分批导入股票数据
- 减少同时处理的股票数量
- 使用PostgreSQL替代SQLite（大数据量时）

## 📚 技术栈

- **数据库**: SQLite (默认) / PostgreSQL (可选)
- **数据采集**: AKShare (免费)
- **ORM**: SQLAlchemy
- **数据处理**: Pandas, NumPy
- **技术指标**: 自定义实现 (MA, MACD, KDJ, RSI, Bollinger, ATR等)
- **Web界面**: Streamlit, Plotly
- **定时任务**: APScheduler
- **日志**: Loguru

## 📝 后续开发方向

- [ ] 添加更多数据源 (Tushare, Yahoo Finance)
- [ ] 机器学习预测模型
- [ ] 更多技术指标和策略
- [ ] 实时行情推送
- [ ] 移动端适配
- [ ] 多因子选股模型
