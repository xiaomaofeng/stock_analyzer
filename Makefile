# Makefile - 跨平台命令简化
# 适用于 Windows (使用 nmake 或 mingw32-make) / Mac / Linux

.PHONY: help install init db-update migrate test run-web run-scheduler docker-build docker-run clean

PYTHON := python
PIP := pip

help:
	@echo "股票数据库系统 - 可用命令:"
	@echo ""
	@echo "  make install         - 安装依赖"
	@echo "  make init            - 初始化项目"
	@echo "  make db-init         - 初始化数据库"
	@echo "  make db-migrate      - 数据库迁移"
	@echo "  make db-upgrade      - 升级数据库"
	@echo "  make test            - 运行测试"
	@echo "  make run-web         - 启动Web界面"
	@echo "  make run-scheduler   - 启动定时任务"
	@echo "  make import-stock    - 导入示例股票"
	@echo "  make calc-indicators - 计算技术指标"
	@echo "  make docker-build    - 构建Docker镜像"
	@echo "  make docker-run      - 运行Docker容器"
	@echo "  make clean           - 清理缓存文件"

install:
	$(PIP) install -r requirements.txt

init: install
	$(PYTHON) scripts/setup.py

db-init:
	$(PYTHON) scripts/init_db.py

db-migrate:
	alembic revision --autogenerate -m "$(msg)"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

test:
	pytest tests/ -v || true

run-web:
	cd web && streamlit run app.py

run-scheduler:
	$(PYTHON) scheduler/jobs.py

import-stock:
	$(PYTHON) scripts/import_stock_data.py --batch --file scripts/stock_list.txt --start 2023-01-01

calc-indicators:
	$(PYTHON) scripts/calc_indicators.py --all

daily-update:
	$(PYTHON) scripts/daily_update.py

docker-build:
	docker build -t stock-db .

docker-run:
	docker run -p 8501:8501 -v $(PWD)/data:/app/data stock-db

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf build/ dist/ *.egg-info/
