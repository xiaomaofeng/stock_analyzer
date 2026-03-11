# 股票分析系统 - 桌面应用版本

## 概述

本项目现在支持两种运行模式：
1. **Web 版本**（Streamlit）- 适合快速原型和远程访问
2. **桌面版本**（PySide6）- 原生应用，更好的用户体验

## 桌面应用优势

| 特性 | Web (Streamlit) | 桌面 (PySide6) |
|------|----------------|---------------|
| 启动速度 | 较慢（需启动server） | 快（原生应用） |
| 离线使用 | ❌ | ✅ |
| 数据安全 | 数据在本地 | 数据在本地 |
| 打包分发 | 困难 | ✅ exe/dmg |
| 用户体验 | 浏览器限制 | 原生菜单/快捷键 |
| 图表性能 | 一般 | 优秀（PyQtGraph） |

## 快速切换指南

### 从 Web 迁移到桌面

**复用的代码（100%兼容）：**
- `collectors/` - 数据采集层
- `processors/` - 指标计算层
- `analysis/` - 分析层
- `database/` - 数据模型和存储
- `config/` - 配置管理
- `backtest/` - 回测引擎

**需要重写的代码：**
- `web/` → `desktop/main.py` （UI层）

### 运行桌面版本

```bash
# 1. 安装桌面依赖
pip install PySide6 pyqtgraph

# 2. 运行
cd F:\Dev\FinanceReport\stock_db
python desktop/main.py
```

### 打包分发

```bash
cd desktop

# Windows
python build.py --platform windows
# 输出: dist/windows/股票分析系统.exe

# macOS
python build.py --platform macos
# 输出: dist/macos/StockAnalyzer.app
```

## 技术架构对比

### Web 版本架构
```
用户 → 浏览器 → Streamlit Server → 业务逻辑 → SQLite
```

### 桌面版本架构
```
用户 → PySide6 (Qt) → 业务逻辑 → SQLite
        ↓
    PyQtGraph (图表)
```

## 开发建议

1. **原型阶段**: 使用 Web 版本快速验证
2. **生产阶段**: 使用桌面版本打包分发
3. **维护策略**: 保持业务逻辑一致，只维护 UI 层

## 下一步

可以进一步开发：
- 回测功能界面
- 多股票监控面板
- 实时行情推送
- 自定义指标公式
