# 🚀 部署指南

本指南说明如何将项目上传到GitHub并进行跨平台部署。

---

## 📤 上传到 GitHub

### 1. 初始化Git仓库

```bash
cd f:\Dev\FinanceReport\stock_db

# 初始化仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: Stock database system with multi-factor analysis"
```

### 2. 创建GitHub仓库

在GitHub上创建新仓库（不要初始化README），然后：

```bash
# 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/stock_db.git

# 推送
git branch -M main
git push -u origin main
```

### 3. 保护敏感信息

确保以下文件已在 `.gitignore` 中：
```
.env
.env.local
*.sqlite
*.sqlite3
*.db
data/
logs/
```

---

## 🖥️ 本地开发环境

### Windows

```powershell
# PowerShell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 或使用 Makefile (需要安装 mingw32-make 或 nmake)
make install
make init
```

### macOS

```bash
# 安装Homebrew (如未安装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装Python
brew install python@3.11

# 设置环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 使用 Makefile
make install
make init
```

### Linux (Ubuntu/Debian)

```bash
# 安装依赖
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv make

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 使用 Makefile
make install
make init
```

---

## 🗄️ 数据库配置

### 场景1: 个人使用 (SQLite)

```bash
# 默认配置，无需修改
# 数据库将存储在 ./data/stock_db.sqlite
cp .env.example .env
python scripts/setup.py
```

### 场景2: 团队共享 (PostgreSQL)

#### 使用Docker (推荐)

```bash
# 1. 配置环境变量
cat > .env << EOF
DATABASE_URL=postgresql://stock_user:stock_pass@localhost:5432/stock_db
DB_USER=stock_user
DB_PASSWORD=your_secure_password
DB_NAME=stock_db
EOF

# 2. 启动PostgreSQL
docker-compose --profile postgres up -d db

# 3. 等待数据库启动
sleep 5

# 4. 初始化数据库
python scripts/db_migrate.py migrate
python scripts/db_migrate.py upgrade
```

#### 使用云服务 (AWS RDS / Azure PostgreSQL / 阿里云RDS)

```bash
# 编辑 .env
DATABASE_URL=postgresql://username:password@your-db-host:5432/stock_db

# 测试连接
python -c "from config.database import check_database_connection; print(check_database_connection())"
```

### 场景3: 企业环境 (MySQL)

```bash
# 安装驱动
pip install pymysql

# 配置 .env
DATABASE_URL=mysql://username:password@localhost:3306/stock_db

# 初始化
python scripts/db_migrate.py migrate
python scripts/db_migrate.py upgrade
```

---

## 🐳 Docker部署

### 本地Docker

```bash
# 构建镜像
docker build -t stock-db .

# 运行容器
docker run -d \
  --name stock_db \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env \
  stock-db

# 查看日志
docker logs -f stock_db
```

### Docker Compose (完整环境)

```bash
# 启动所有服务
docker-compose up -d

# 仅启动Web界面 (使用SQLite)
docker-compose up -d app

# 启动Web + PostgreSQL
docker-compose --profile postgres up -d

# 启动完整环境 (Web + PostgreSQL + 定时任务)
docker-compose --profile postgres --profile scheduler up -d
```

### GitHub Container Registry

GitHub Actions会自动构建并推送Docker镜像。

```bash
# 拉取镜像
docker pull ghcr.io/YOUR_USERNAME/stock_db:latest

# 运行
docker run -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  ghcr.io/YOUR_USERNAME/stock_db:latest
```

---

## ☁️ 云部署

### 阿里云 ECS / 腾讯云 CVM

```bash
# 1. 连接服务器
ssh root@your-server-ip

# 2. 安装Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 3. 安装Docker Compose
pip3 install docker-compose

# 4. 克隆项目
git clone https://github.com/YOUR_USERNAME/stock_db.git
cd stock_db

# 5. 配置环境变量
cp .env.example .env
vim .env  # 修改配置

# 6. 启动
docker-compose --profile postgres --profile scheduler up -d

# 7. 配置Nginx反向代理 (可选)
```

### AWS EC2

```bash
# 使用Amazon Linux 2
sudo yum update -y
sudo amazon-linux-extras install docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# 安装docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 后续步骤同上
```

### Heroku (使用PostgreSQL)

```bash
# 安装Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# 登录
heroku login

# 创建应用
heroku create your-stock-db

# 添加PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# 推送代码
git push heroku main

# 运行迁移
heroku run python scripts/db_migrate.py upgrade
```

---

## 🔒 安全配置检查清单

上传前确保：

- [ ] `.env` 文件在 `.gitignore` 中
- [ ] 数据库密码强度足够
- [ ] 生产环境使用PostgreSQL/MySQL而非SQLite
- [ ] Docker镜像不包含敏感信息
- [ ] GitHub Actions secrets 已配置 (如需)

---

## 🔄 持续集成/部署 (CI/CD)

GitHub Actions已配置：

- **CI**: 每次Push时测试多平台兼容性
- **Docker Publish**: 推送到main分支时自动构建镜像

如需添加更多secrets:

```bash
# 在GitHub仓库 Settings > Secrets and variables > Actions 中添加:
- DOCKER_USERNAME
- DOCKER_PASSWORD
- DB_PASSWORD (用于测试)
```

---

## 📊 监控与维护

### 健康检查

```bash
# 本地
python scheduler/monitor.py

# Docker
docker-compose exec app python scheduler/monitor.py
```

### 数据备份

**SQLite:**
```bash
# 备份
cp data/stock_db.sqlite data/backup_$(date +%Y%m%d).sqlite

# 恢复
cp data/backup_20240101.sqlite data/stock_db.sqlite
```

**PostgreSQL:**
```bash
# 备份
docker-compose exec db pg_dump -U stock_user stock_db > backup_$(date +%Y%m%d).sql

# 恢复
docker-compose exec -T db psql -U stock_user stock_db < backup_20240101.sql
```

---

## 🆘 故障排查

### 数据库连接失败

```bash
# 检查配置
python -c "from config import get_settings; s=get_settings(); print(s.DATABASE_URL)"

# 测试连接
python -c "from config.database import check_database_connection; print(check_database_connection())"
```

### Docker无法启动

```bash
# 查看日志
docker-compose logs app

# 重建镜像
docker-compose build --no-cache

# 清理卷
docker-compose down -v
```

### 跨平台路径问题

项目已使用 `pathlib` 处理路径，通常无需修改。如遇到问题：

```python
from pathlib import Path
from config import get_settings

settings = get_settings()
data_dir = settings.get_data_dir()  # 自动适配各平台
```

---

## 📞 获取帮助

- 查看 [README.md](README.md) 获取详细功能说明
- 查看 [QUICKSTART.md](QUICKSTART.md) 获取快速开始指南
- 提交 Issue: https://github.com/YOUR_USERNAME/stock_db/issues
