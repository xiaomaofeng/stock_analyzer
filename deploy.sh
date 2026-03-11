#!/bin/bash
# =============================================================================
# 股票分析系统 - 自动化部署脚本 (Linux/macOS)
# =============================================================================
# 使用方法:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# 该脚本会自动完成:
# 1. 检查 Docker 环境
# 2. 创建配置文件
# 3. 拉取/构建镜像
# 4. 启动所有服务
# 5. 自动导入 159892 等股票数据
# 6. 计算技术指标
# 7. 启动 Web 服务
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker
check_docker() {
    log_info "检查 Docker 环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        log_info "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        log_info "安装指南: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # 检查 Docker 是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未启动，请先启动 Docker"
        exit 1
    fi
    
    log_success "Docker 环境正常"
}

# 创建环境变量文件
setup_env() {
    log_info "配置环境变量..."
    
    if [ ! -f ".env" ]; then
        cp .env.deploy .env
        log_warning "已创建默认配置文件 .env"
        log_warning "建议修改默认密码: DB_PASSWORD"
    else
        log_info "配置文件 .env 已存在"
    fi
}

# 创建必要目录
setup_dirs() {
    log_info "创建必要目录..."
    mkdir -p data logs init-scripts
    log_success "目录创建完成"
}

# 部署服务
deploy() {
    log_info "开始部署股票分析系统..."
    log_info "包含股票: 159892(恒生互联网ETF) 等"
    
    # 拉取最新镜像
    log_info "拉取 Docker 镜像..."
    docker-compose -f docker-compose.prod.yml pull
    
    # 构建镜像
    log_info "构建应用镜像..."
    docker-compose -f docker-compose.prod.yml build
    
    # 启动服务
    log_info "启动服务..."
    docker-compose -f docker-compose.prod.yml up -d
    
    log_success "服务已启动"
}

# 等待服务就绪
wait_for_ready() {
    log_info "等待服务初始化..."
    
    # 等待数据库
    log_info "等待数据库就绪..."
    for i in {1..30}; do
        if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U stock_user &> /dev/null; then
            log_success "数据库已就绪"
            break
        fi
        sleep 2
        echo -n "."
    done
    
    # 等待数据初始化
    log_info "等待数据初始化完成（这可能需要几分钟）..."
    echo "正在导入 159892 等股票数据并计算指标..."
    
    # 等待 data-init 服务完成
    for i in {1..60}; do
        status=$(docker-compose -f docker-compose.prod.yml ps -q data-init | xargs docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "running")
        if [ "$status" = "exited" ]; then
            exit_code=$(docker-compose -f docker-compose.prod.yml ps -q data-init | xargs docker inspect -f '{{.State.ExitCode}}' 2>/dev/null || echo "1")
            if [ "$exit_code" = "0" ]; then
                log_success "数据初始化完成"
                return 0
            else
                log_error "数据初始化失败"
                return 1
            fi
        fi
        sleep 5
        echo -n "."
    done
    
    log_warning "等待超时，但服务可能仍在运行"
    return 0
}

# 显示访问信息
show_access_info() {
    echo ""
    echo "==================================================================="
    echo "                     🎉 部署成功！                                 "
    echo "==================================================================="
    echo ""
    echo "📊 股票分析系统已启动，包含以下股票数据："
    echo "   - 159892 (恒生互联网ETF)"
    echo "   - 000001 (平安银行)"
    echo "   - 000333 (美的集团)"
    echo "   - 600519 (贵州茅台)"
    echo "   - 等共 15 只股票"
    echo ""
    echo "🌐 访问地址:"
    echo "   Web界面: http://localhost:8501"
    echo ""
    echo "🗄️  数据库信息:"
    echo "   地址: localhost:5432"
    echo "   数据库: stock_db"
    echo "   用户名: stock_user"
    echo ""
    echo "📋 常用命令:"
    echo "   查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "   停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "   重启服务: docker-compose -f docker-compose.prod.yml restart"
    echo ""
    echo "⚠️  安全提示:"
    echo "   生产环境请修改默认密码！"
    echo "   编辑 .env 文件修改 DB_PASSWORD"
    echo ""
    echo "==================================================================="
}

# 主函数
main() {
    echo "==================================================================="
    echo "          股票分析系统 - 自动化部署脚本"
    echo "==================================================================="
    echo ""
    
    check_docker
    setup_env
    setup_dirs
    deploy
    
    if wait_for_ready; then
        show_access_info
    else
        log_error "部署可能出现问题，请检查日志"
        docker-compose -f docker-compose.prod.yml logs
        exit 1
    fi
}

# 执行主函数
main "$@"
