# =============================================================================
# 股票分析系统 - 自动化部署脚本 (Windows PowerShell)
# =============================================================================
# 使用方法:
#   右键 "使用 PowerShell 运行" 或 PowerShell 中执行: .\deploy.ps1
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

param(
    [switch]$SkipBuild,
    [switch]$Reset
)

# 设置编码
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 颜色函数
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Blue }
function Write-Success { param($Message) Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host "[WARNING] $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

# 检查 Docker
function Test-Docker {
    Write-Info "检查 Docker 环境..."
    
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
        Write-Error "Docker 未安装"
        Write-Info "请访问 https://docs.docker.com/desktop/install/windows-install/ 下载安装"
        exit 1
    }
    
    $compose = Get-Command docker-compose -ErrorAction SilentlyContinue
    if (-not $compose) {
        Write-Error "Docker Compose 未安装"
        Write-Info "请安装 Docker Desktop（已包含 Compose）"
        exit 1
    }
    
    # 检查 Docker 是否运行
    try {
        $null = docker info 2>$null
    } catch {
        Write-Error "Docker 服务未启动"
        Write-Info "请启动 Docker Desktop"
        exit 1
    }
    
    Write-Success "Docker 环境正常"
}

# 设置环境变量
function Set-Environment {
    Write-Info "配置环境变量..."
    
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.deploy" ".env"
        Write-Warning "已创建默认配置文件 .env"
        Write-Warning "建议修改默认密码: DB_PASSWORD"
    } else {
        Write-Info "配置文件 .env 已存在"
    }
}

# 创建目录
function Set-Directories {
    Write-Info "创建必要目录..."
    New-Item -ItemType Directory -Force -Path "data" | Out-Null
    New-Item -ItemType Directory -Force -Path "logs" | Out-Null
    New-Item -ItemType Directory -Force -Path "init-scripts" | Out-Null
    Write-Success "目录创建完成"
}

# 部署
function Start-Deployment {
    Write-Info "开始部署股票分析系统..."
    Write-Info "包含股票: 159892(恒生互联网ETF) 等"
    
    if ($Reset) {
        Write-Warning "重置模式: 将删除现有数据！"
        docker-compose -f docker-compose.prod.yml down -v
    }
    
    if (-not $SkipBuild) {
        Write-Info "构建应用镜像..."
        docker-compose -f docker-compose.prod.yml build
    }
    
    Write-Info "启动服务..."
    docker-compose -f docker-compose.prod.yml up -d
    
    Write-Success "服务已启动"
}

# 等待就绪
function Wait-ForReady {
    Write-Info "等待服务初始化..."
    Write-Info "正在导入 159892 等股票数据并计算指标..."
    Write-Info "这可能需要 3-5 分钟，请耐心等待..."
    
    $maxAttempts = 60
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        $attempt++
        
        # 检查 data-init 容器状态
        $container = docker-compose -f docker-compose.prod.yml ps -q data-init
        if ($container) {
            $status = docker inspect -f '{{.State.Status}}' $container 2>$null
            if ($status -eq "exited") {
                $exitCode = docker inspect -f '{{.State.ExitCode}}' $container 2>$null
                if ($exitCode -eq "0") {
                    Write-Success "数据初始化完成"
                    return $true
                } else {
                    Write-Error "数据初始化失败"
                    return $false
                }
            }
        }
        
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 5
    }
    
    Write-Warning "等待超时，但服务可能仍在运行"
    return $true
}

# 显示访问信息
function Show-AccessInfo {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*"} | Select-Object -First 1).IPAddress
    if (-not $ip) { $ip = "localhost" }
    
    Write-Host ""
    Write-Host "===================================================================" -ForegroundColor Cyan
    Write-Host "                     部署成功！                                    " -ForegroundColor Green
    Write-Host "===================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "股票分析系统已启动，包含以下股票数据："
    Write-Host "   - 159892 (恒生互联网ETF)" -ForegroundColor Yellow
    Write-Host "   - 000001 (平安银行)" -ForegroundColor Yellow
    Write-Host "   - 000333 (美的集团)" -ForegroundColor Yellow
    Write-Host "   - 600519 (贵州茅台)" -ForegroundColor Yellow
    Write-Host "   - 等共 15 只股票" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "访问地址:" -ForegroundColor Green
    Write-Host "   本机访问: http://localhost:8501" -ForegroundColor Cyan
    Write-Host "   局域网访问: http://${ip}:8501" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "数据库信息:" -ForegroundColor Green
    Write-Host "   地址: localhost:5432" -ForegroundColor Gray
    Write-Host "   数据库: stock_db" -ForegroundColor Gray
    Write-Host "   用户名: stock_user" -ForegroundColor Gray
    Write-Host ""
    Write-Host "常用命令:" -ForegroundColor Green
    Write-Host "   查看日志: docker-compose -f docker-compose.prod.yml logs -f" -ForegroundColor Gray
    Write-Host "   停止服务: docker-compose -f docker-compose.prod.yml down" -ForegroundColor Gray
    Write-Host "   重启服务: docker-compose -f docker-compose.prod.yml restart" -ForegroundColor Gray
    Write-Host ""
    Write-Host "安全提示:" -ForegroundColor Yellow
    Write-Host "   生产环境请修改默认密码！" -ForegroundColor Red
    Write-Host "   编辑 .env 文件修改 DB_PASSWORD" -ForegroundColor Gray
    Write-Host ""
    Write-Host "===================================================================" -ForegroundColor Cyan
}

# 主函数
function Main {
    Write-Host "===================================================================" -ForegroundColor Cyan
    Write-Host "          股票分析系统 - 自动化部署脚本" -ForegroundColor White
    Write-Host "===================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    Test-Docker
    Set-Environment
    Set-Directories
    Start-Deployment
    
    if (Wait-ForReady) {
        Show-AccessInfo
        
        # 尝试自动打开浏览器
        Start-Process "http://localhost:8501"
    } else {
        Write-Error "部署可能出现问题，请检查日志"
        docker-compose -f docker-compose.prod.yml logs
    }
}

# 执行
Main
