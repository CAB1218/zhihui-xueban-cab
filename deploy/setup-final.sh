#!/bin/bash
# ================================================
#  智慧学伴 一键完成部署脚本
#  功能：建表 + 种子数据 + 前端构建 + Nginx部署
#  用法：bash setup-final.sh
# ================================================
set -e

PROJECT_DIR="/opt/ai4edu"

echo "=============================================="
echo "  智慧学伴 一键部署 - 建表/数据/前端/Nginx"
echo "=============================================="

# ============ Step 1: 创建数据库表 ============
echo ""
echo ">>> [1/4] 创建数据库表..."

# 确保后端容器在运行
if ! docker ps --format '{{.Names}}' | grep -q 'ai4edu-backend'; then
    echo "[ERROR] 后端容器未运行！请先启动 docker compose"
    exit 1
fi

# 把 scripts 目录复制进容器（seed脚本需要）
docker cp ${PROJECT_DIR}/backend/scripts ai4edu-backend:/app/scripts 2>/dev/null || true

# 用 Python ORM 自动建表（最可靠的方式）
docker exec ai4edu-backend python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from app.models import *  # noqa - 导入所有模型确保 Base.metadata 包含全部表
from app.database import Base, engine

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('=== ALL TABLES CREATED ===')

asyncio.run(init())
"

# 验证表数量
TABLE_COUNT=$(docker exec ai4edu-postgres psql -U ai4edu -d ai4edu -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d ' ')
echo "[OK] PostgreSQL 已创建 ${TABLE_COUNT} 个表"

# ============ Step 2: 插入种子数据 ============
echo ""
echo ">>> [2/4] 插入种子数据..."

# 运行主种子脚本（租户/用户/角色/权限/场景）
docker exec ai4edu-backend python3 /app/scripts/seed_data.py

echo "[OK] 核心种子数据已插入"

# ============ Step 3: 构建前端 ============
echo ""
echo ">>> [3/4] 构建前端..."

# 安装 Node.js（如果没有）
if ! command -v node &>/dev/null; then
    echo "[INFO] 安装 Node.js 22.x..."
    curl -fsSL https://rpm.nodesource.com/setup_22.x | bash -
    yum install -y nodejs
fi
echo "[OK] Node.js $(node -v), npm $(npm -v)"

cd ${PROJECT_DIR}/frontend

# npm install（如果 node_modules 不存在）
if [ ! -d "node_modules" ]; then
    echo "[INFO] 安装前端依赖（约2-3分钟）..."
    npm install 2>&1 | tail -3
fi

# npm run build
echo "[INFO] 编译前端..."
npm run build 2>&1 | tail -5

if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
    echo "[ERROR] 前端构建失败！dist/index.html 不存在"
    exit 1
fi
echo "[OK] 前端构建完成 ($(find dist -type f | wc -l) 个文件)"

# ============ Step 4: 启动 Nginx 前端容器 ============
echo ""
echo ">>> [4/4] 启动 Nginx 容器..."

# 确保 nginx 配置文件存在
NGINX_CONF="${PROJECT_DIR}/deploy/nginx/conf.d/default.http.conf"
if [ ! -f "$NGINX_CONF" ]; then
    echo "[WARN] nginx 配置不存在，在线生成..."
    mkdir -p ${PROJECT_DIR}/deploy/nginx/conf.d
    cat > $NGINX_CONF << 'NGINXEOF'
upstream backend {
    server backend:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    client_max_body_size 100M;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }

    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 7d;
        add_header Cache-Control "public";
        try_files $uri =404;
    }

    location ~ /\. {
        deny all;
    }
}
NGINXEOF
fi

# 停掉旧前端容器
docker rm -f ai4edu-frontend 2>/dev/null || true

# 启动 Nginx 容器（加入 ai4edu-network 以便与 backend 通信）
docker run -d \
    --name ai4edu-frontend \
    --restart always \
    --network deploy_ai4edu-network \
    -p 80:80 \
    -v ${PROJECT_DIR}/frontend/dist:/usr/share/nginx/html:ro \
    -v ${NGINX_CONF}:/etc/nginx/conf.d/default.conf:ro \
    nginx:alpine

sleep 3

# 验证
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80)
echo "[OK] Nginx 返回 HTTP $HTTP_CODE"

# ============ 完成 ============
echo ""
echo "=============================================="
echo "  智慧学伴 部署完成！"
echo "=============================================="
echo ""
echo "  前端网站： http://121.43.129.181"
echo "  后端API：  http://121.43.129.181/api/v1/health"
echo ""
echo "  登录账号： admin@ai4edu.com"
echo "  登录密码： admin123"
echo ""
echo "  容器状态："
docker ps --format "  {{.Names}}: {{.Status}}" --filter "name=ai4edu"
echo ""
echo "  数据库表：${TABLE_COUNT} 个"
echo "=============================================="
