# 🚀 自动化部署指南

一键部署股票分析系统，部署完成后直接通过网页访问真实数据分析。

## 📋 部署方式选择

| 方式 | 难度 | 适用场景 | 数据持久化 |
|------|------|----------|------------|
| **Docker Compose** | ⭐ 最简单 | 单机部署，快速体验 | Docker Volume |
| **云服务器部署** | ⭐⭐ 中等 | 公网访问，团队协作 | 云盘/云数据库 |
| **GitHub Actions自动部署** | ⭐⭐⭐ 高级 | CI/CD，自动更新 | 服务器存储 |

---

## 🐳 方式一：Docker Compose 一键部署（推荐）

### 前置要求
- Docker Desktop 安装完成
- 系统：Windows 10+/macOS/Linux

### 部署步骤

#### Windows (PowerShell)
```powershell
# 1. 克隆仓库
git clone https://github.com/xiaomaofeng/stock_analyzer.git
cd stock_analyzer

# 2. 一键部署（右键 PowerShell 运行）
.\deploy.ps1

# 或使用参数
.\deploy.ps1 -Reset  # 重置并重新部署
```

#### macOS / Linux (Terminal)
```bash
# 1. 克隆仓库
git clone https://github.com/xiaomaofeng/stock_analyzer.git
cd stock_analyzer

# 2. 一键部署
chmod +x deploy.sh
./deploy.sh

# 或使用参数
./deploy.sh
```

### 部署过程说明

脚本会自动执行：
1. ✅ 检查 Docker 环境
2. ✅ 创建 `.env` 配置文件
3. ✅ 启动 PostgreSQL 数据库
4. ✅ **自动导入 159892 等 15 只股票的真实数据**
5. ✅ **自动计算 MACD/KDJ/RSI 等技术指标**
6. ✅ 启动 Web 服务
7. ✅ 启动定时更新任务

### 访问系统

部署完成后，打开浏览器访问：
```
http://localhost:8501
```

你将看到：
- 📊 159892 (恒生互联网ETF) 的完整分析
- 📈 K线图、技术指标图表
- 🎯 多因子策略评分
- 📋 其他股票数据

### 停止服务

```bash
# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 停止并删除数据（谨慎使用）
docker-compose -f docker-compose.prod.yml down -v
```

---

## ☁️ 方式二：云服务器部署

### 购买云服务器

推荐：阿里云 ECS / 腾讯云 CVM / AWS EC2
- 配置：2核4G 起步
- 系统：Ubuntu 22.04 LTS
- 带宽：3-5Mbps

### 部署步骤

```bash
# 1. SSH 登录服务器
ssh root@your-server-ip

# 2. 安装 Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 3. 安装 Docker Compose
pip3 install docker-compose

# 4. 下载项目
mkdir -p /opt/stock_db
cd /opt/stock_db
wget https://github.com/xiaomaofeng/stock_analyzer/archive/refs/heads/main.zip
unzip main.zip
mv stock_analyzer-main/* .

# 5. 配置环境变量
cp .env.deploy .env
# 编辑 .env 修改密码: vim .env

# 6. 部署
chmod +x deploy.sh
./deploy.sh

# 7. 配置防火墙（开放8501端口）
# 阿里云/腾讯云控制台配置安全组
```

### 配置域名访问（可选）

```bash
# 安装 Nginx
apt-get install nginx

# 创建配置文件
cat > /etc/nginx/sites-available/stock_db << 'EOF'
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

ln -s /etc/nginx/sites-available/stock_db /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# 配置 SSL（使用 Certbot）
apt-get install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

---

## 🔄 方式三：GitHub Actions 自动部署

### 配置 Secrets

在 GitHub 仓库 Settings > Secrets and variables > Actions 中添加：

```
SSH_HOST          # 服务器IP或域名
SSH_USER          # SSH用户名 (如 root)
SSH_KEY           # SSH私钥 (cat ~/.ssh/id_rsa)
SSH_PORT          # SSH端口 (默认22)
DB_PASSWORD       # 数据库密码
```

### 自动部署流程

1. 每次推送到 `main` 分支，自动构建 Docker 镜像
2. 镜像推送到 GitHub Container Registry
3. 自动 SSH 登录服务器执行部署

### 手动触发部署

在 GitHub Actions 页面点击 "Run workflow" 手动触发。

---

## 📊 部署后初始数据

部署完成后，系统自动导入以下股票数据：

| 代码 | 名称 | 类型 |
|------|------|------|
| **159892** | 华夏恒生互联网ETF | ETF |
| 000001 | 平安银行 | A股 |
| 000002 | 万科A | A股 |
| 000333 | 美的集团 | A股 |
| 000858 | 五粮液 | A股 |
| 002415 | 海康威视 | A股 |
| 002594 | 比亚迪 | A股 |
| 300750 | 宁德时代 | A股 |
| 600000 | 浦发银行 | A股 |
| 600036 | 招商银行 | A股 |
| 600276 | 恒瑞医药 | A股 |
| 600519 | 贵州茅台 | A股 |
| 601318 | 中国平安 | A股 |
| 601888 | 中国中免 | A股 |
| 603288 | 海天味业 | A股 |

**数据范围**：最近 1 年的历史数据  
**更新频率**：每日自动更新

---

## 🔧 配置说明

### 修改初始股票列表

编辑 `docker-compose.prod.yml`：

```yaml
environment:
  - INIT_STOCKS=159892,000001,000333  # 修改为你想要的股票代码
```

### 修改数据库密码

编辑 `.env` 文件：

```bash
DB_PASSWORD=YourStrongPassword123!
```

### 修改访问端口

编辑 `.env` 文件：

```bash
WEB_PORT=8080  # 改为想要的端口
```

---

## 🛠️ 故障排查

### 问题1：端口被占用

```bash
# 查看端口占用
lsof -i :8501

# 修改端口后重新部署
# 编辑 .env: WEB_PORT=8502
./deploy.sh
```

### 问题2：数据初始化失败

```bash
# 查看日志
docker-compose -f docker-compose.prod.yml logs data-init

# 手动重新导入
docker-compose -f docker-compose.prod.yml run --rm data-init
```

### 问题3：AKShare 数据获取失败

检查网络连接，或使用代理：

```bash
# 编辑 .env 增加延迟
AKSHARE_REQUEST_DELAY=2.0
```

### 问题4：内存不足

增加 Docker 内存限制：

```yaml
# docker-compose.prod.yml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 2G
```

---

## 🔒 安全建议

1. **修改默认密码**：部署后立即修改 `DB_PASSWORD`
2. **使用防火墙**：只开放必要的端口（8501, 5432）
3. **HTTPS**：生产环境使用 Nginx + SSL
4. **定期备份**：备份 PostgreSQL 数据卷

---

## 📞 获取帮助

- 查看日志：`docker-compose -f docker-compose.prod.yml logs -f`
- 重启服务：`docker-compose -f docker-compose.prod.yml restart`
- 提交 Issue：https://github.com/xiaomaofeng/stock_analyzer/issues
