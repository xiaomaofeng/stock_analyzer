# 股票分析系统 - 桌面应用

基于 PySide6 开发的跨平台桌面应用，支持 Windows 和 macOS。

## 特性

- 🖥️ 原生桌面应用，无需浏览器
- 📊 实时K线图（PyQtGraph）
- 🔍 股票数据查询与自动获取
- 📈 技术指标计算与显示
- 📉 趋势分析与风险评估
- 💾 数据导出（CSV）
- 🌐 跨平台支持（Windows/macOS）

## 快速开始

### 1. 安装依赖

```bash
# 在项目根目录
cd F:\Dev\FinanceReport\stock_db

# 安装桌面应用依赖
pip install -r desktop/requirements.txt
```

### 2. 运行桌面应用

```bash
python desktop/main.py
```

### 3. 打包成可执行文件

#### Windows (.exe)

```bash
cd desktop
python build.py --platform windows
```

输出: `dist/windows/股票分析系统.exe`

#### macOS (.app/.dmg)

```bash
cd desktop
python build.py --platform macos
```

输出: `dist/macos/StockAnalyzer.app`

## 项目结构

```
desktop/
├── main.py           # 主程序入口
├── build.py          # 打包脚本
├── requirements.txt  # 桌面应用依赖
└── README.md         # 本文件
```

## 开发说明

### 复用的模块

桌面应用完全复用现有的业务逻辑：

- `collectors/` - 数据采集（AKShare）
- `processors/` - 指标计算
- `analysis/` - 趋势分析、风险指标
- `database/` - 数据存储（SQLite）
- `config/` - 配置管理

### UI 框架

- **PySide6**: Qt for Python，跨平台GUI
- **PyQtGraph**: 高性能图表库
- **QThread**: 后台数据获取，不阻塞UI

### 打包配置

使用 PyInstaller 打包：

- `--windowed`: 无控制台窗口
- `--onefile`: 单文件可执行
- `--add-data`: 包含数据库文件

## 注意事项

1. **首次运行**会自动创建数据库
2. **数据存储**在应用目录的 `data/` 文件夹
3. **网络连接**需要访问 AKShare 获取实时数据

## 待优化

- [ ] 更美观的K线图（支持蜡烛图样式）
- [ ] 多股票对比功能
- [ ] 回测功能集成
- [ ] 自动更新机制
