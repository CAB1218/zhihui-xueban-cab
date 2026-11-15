#!/bin/bash
# ============================================================
# 智慧学伴 阿里云 ECS 一键部署脚本
# 用法：在服务器上执行：
#   curl -fsSL https://raw.githubusercontent.com/CAG1218/ai4edu/main/deploy/deploy.sh | bash
# 或：
#   wget -qO- https://raw.githubusercontent.com/CAG1218/ai4edu/main/deploy/deploy.sh | bash
# ============================================================

set -e

echo "=============================================="
echo "  智慧学伴 云服务器部署脚本"
echo "  公网 IP: ${PUBLIC_IP:-$(curl -s ifconfig.me)}"
echo "=============================================="
echo ""

# ---- 颜色定义 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR="/opt/ai4edu"

# ========================================
# 第 1 步：系统检查与基础工具安装
# ========================================
echo ""
echo ">>> [1/6] 系统环境准备..."

# 检查 root 权限
if [ "$(id -u)" -ne 0 ]; then
    err "请用 root 用户运行此脚本（sudo bash deploy.sh）"
    exit 1
fi

# 更新系统
info "更新系统包..."
yum update -y -q 2>/dev/null || apt update -y -q 2>/dev/null

# 安装基础工具
info "安装基础工具..."
if command -v yum &>/dev/null; then
    yum install -y -q git curl wget unzip jq docker-compose-plugin 2>/dev/null || true
else
    apt install -y -q git curl wget unzip jq 2>/dev/null || true
fi

ok "系统环境准备完成"

# ========================================
# 第 2 步：Docker 检查
# ========================================
echo ""
echo ">>> [2/6] Docker 环境检查..."

if ! command -v docker &>/dev/null; then
    warn "Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    ok "Docker 已安装并启动"
else
    ok "Docker 已就绪: $(docker --version)"
fi

# 检查 Docker Compose 插件
if ! docker compose version &>/dev/null; then
    warn "Docker Compose 未安装，正在安装..."
    # 兼容旧版 compose 命令
    if ! command -v docker-compose &>/dev/null; then
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        ok "docker-compose 已安装（独立版）"
    fi
else
    ok "Docker Compose 已就绪"
fi

# 将当前用户加入 docker 组
USER_HOME=$(eval echo ~${SUDO_USER:-$USER})
if [ "$SUDO_USER" ] && ! groups "$SUDO_USER" 2>/dev/null | grep -q '\bdocker\b'; then
    usermod -aG docker "$SUDO_USER"
    info "用户 $SUDO_USER 已加入 docker 组"
fi

# ========================================
# 第 3 步：克隆代码仓库
# ========================================
echo ""
echo ">>> [3/6] 克隆 智慧学伴 代码..."

if [ -d "$PROJECT_DIR" ]; then
    warn "项目目录已存在，更新代码..."
    cd "$PROJECT_DIR"
    git pull origin main
    ok "代码已更新到最新版本"
else
    info "从 GitHub 克隆代码..."
    git clone https://github.com/CAG1218/ai4edu.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    ok "代码克隆完成"
fi

# ========================================
# 第 4 步：生成生产环境 .env 配置
# ========================================
echo ""
echo ">>> [4/6] 配置生产环境变量..."

cd "$PROJECT_DIR/backend"

if [ -f ".env" ]; then
    warn ".env 文件已存在，备份为 .env.bak ..."
    cp .env .env.bak.$(date +%s)
fi

# 生成随机密钥
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

cat > .env << ENVEOF
# 智慧学伴 后端环境变量 — 生产环境（自动生成）
APP_NAME=ai4edu
APP_ENV=production
DEBUG=false
SECRET_KEY=${SECRET_KEY}
API_V1_PREFIX=/api/v1

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ai4edu
POSTGRES_USER=ai4edu
POSTGRES_PASSWORD=ai4edu_prod_password_2024

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j_prod_password_2024

# ClickHouse
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=clickhouse_prod_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=ai4edu
MINIO_SECURE=false

# Elasticsearch
ELASTICSEARCH_HOST=http://elasticsearch:9200

# JWT
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS — 开发期允许所有来源，生产环境请收紧
CORS_ORIGINS=["*"]

# OpenAI / AI 配置（按需填写）
OPENAI_API_KEY=
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
ENVEOF

ok ".env 配置文件已生成"

# ========================================
# 第 5 步：启动所有容器
# ========================================
echo ""
echo ">>> [5/6] 启动 Docker 容器（首次需要拉取镜像，约 3~8 分钟）..."

cd "$PROJECT_DIR/deploy"

# 先拉取镜像
info "拉取 Docker 镜像（PostgreSQL / Neo4j / Redis / MinIO / Elasticsearch / ClickHouse）..."
docker compose pull --ignore-pull-failures 2>/dev/null || true

# 构建并启动
info "构建后端镜像并启动所有服务..."
docker compose up -d --build

# 等待关键服务健康
info "等待服务启动..."
sleep 15

# 显示状态
echo ""
docker compose ps

ok "Docker 服务已启动！"

# ========================================
# 第 6 步：初始化数据 + 健康检查
# ========================================
echo ""
echo ">>> [6/6] 数据初始化与健康检查..."

cd "$PROJECT_DIR"

# 运行种子数据脚本（如果存在）
if [ -f "backend/scripts/seed_data.py" ]; then
    info "导入种子数据..."
    docker exec ai4edu-backend python scripts/seed_data.py 2>/dev/null && \
        ok "种子数据已导入" || warn "种子数据跳过（可稍后手动执行）"
fi

if [ -f "backend/scripts/seed_notes_resources.py" ]; then
    info "导入笔记和资源数据..."
    docker exec ai4edu-backend python scripts/seed_notes_resources.py 2>/dev/null && \
        ok "笔记/资源数据已导入" || warn "笔记/资源数据跳过"
fi

# 健康检查
echo ""
echo "=============================================="
echo "  健康检查"
echo "=============================================="

BACKEND_URL="http://localhost:8000"
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/docs" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    info "等待后端启动... ($RETRY_COUNT/$MAX_RETRIES) [HTTP $HTTP_CODE]"
    sleep 10
done

if [ "$HTTP_CODE" = "200" ]; then
    echo ""
    ok "后端 API 正常运行！"
else
    err "后端 API 启动超时，请手动检查：docker logs ai4edu-backend"
fi

# ========================================
# 完成！显示访问信息
# ========================================
echo ""
echo "=============================================="
echo "  ✅ 智慧学伴 部署完成！"
echo "=============================================="
echo ""
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "<你的公网IP>")
echo "  后端 API 文档：  http://${PUBLIC_IP}:8000/docs"
echo "  后端 API 地址：  http://${PUBLIC_IP}:8000/api/v1/"
echo "  Neo4j 控制台：   http://${PUBLIC_IP}:7474"
echo "  MinIO 控制台：   http://${PUBLIC_IP}:9003"
echo "  Elasticsearch： http://${PUBLIC_IP}:9200"
echo ""
echo "  默认账号：      admin@ai4edu.com"
echo "  默认密码：      admin123"
echo ""
echo "=============================================="
echo "  常用管理命令"
echo "=============================================="
echo "  查看日志：       docker logs -f ai4edu-backend"
echo "  重启服务：       cd $PROJECT_DIR/deploy && docker compose restart"
echo "  停止服务：       cd $PROJECT_DIR/deploy && docker compose down"
echo "  进入后端容器：   docker exec -it ai4edu-backend bash"
echo "  查看容器状态：   docker ps"
echo "=============================================="
