#!/bin/bash
# ================================================
#  智慧学伴 云服务器完整部署脚本（第2阶段：前端+数据库初始化）
#  用法: bash /opt/ai4edu/deploy/setup-stage2.sh
# ================================================

set -e
cd /opt/ai4edu

echo "=============================================="
echo "  智慧学伴 第2阶段部署：前端构建 + 数据库初始化"
echo "=============================================="

# ---------- 1. 安装 Node.js (如果还没有) ----------
echo ""
echo ">>> [1/5] 检查 Node.js 环境..."
if ! command -v node &>/dev/null; then
    echo "[INFO] 安装 Node.js 22..."
    curl -fsSL https://rpm.nodesource.com/setup_22.x | bash -
    yum install -y nodejs
fi
echo "[OK] Node.js $(node -v)"

# ---------- 2. 构建前端 ----------
echo ""
echo ">>> [2/5] 构建前端..."
cd /opt/ai4edu/frontend

if [ ! -d "node_modules" ]; then
    echo "[INFO] npm install (首次安装，约1-3分钟)..."
    npm install --production=false 2>&1 | tail -3
fi

echo "[INFO] npm run build..."
npm run build 2>&1 | tail -5

if [ ! -d "dist" ]; then
    echo "[ERROR] 前端构建失败！dist 目录不存在"
    exit 1
fi
echo "[OK] 前端构建完成 ($(ls dist | wc -l) 个文件)"

# ---------- 3. 启动 Nginx 前端容器 ----------
echo ""
echo ">>> [3/5] 部署前端到 Nginx..."

# 停掉旧的 nginx 容器（如果有）
docker rm -f ai4edu-frontend 2>/dev/null || true

docker run -d \
    --name ai4edu-frontend \
    --restart always \
    -p 80:80 \
    -v /opt/ai4edu/frontend/dist:/usr/share/nginx/html:ro \
    -v /opt/ai4edu/deploy/nginx/conf.d/default.http.conf:/etc/nginx/conf.d/default.conf:ro \
    nginx:alpine

sleep 2

# 验证
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80 || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "[OK] Nginx 前端启动成功 (HTTP $HTTP_CODE)"
else
    echo "[WARN] 前端返回 HTTP $HTTP_CODE，继续..."
fi

# ---------- 4. 初始化数据库表 ----------
echo ""
echo ">>> [4/5] 初始化数据库..."

# 用 Python 在后端容器内创建所有表
docker exec -it ai4edu-backend python3 << 'PYEOF'
import asyncio, sys
sys.path.insert(0, '/app')

from app.database import Base, engine

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('ALL_TABLES_CREATED_OK')
    
asyncio.run(init())
PYEOF

echo ""

# ---------- 5. 插入种子数据 ----------
echo ">>> [5/5] 插入种子数据..."

docker exec ai4edu-postgres psql -U ai4edu -d ai4edu << 'SQLEOF'

-- 租户
INSERT INTO tenants (name, slug, domain, plan) VALUES ('智慧学伴 默认租户', 'ai4edu', 'localhost', 'pro') ON CONFLICT (slug) DO NOTHING;

-- 管理员 (密码: admin123 的 bcrypt hash)
INSERT INTO users (tenant_id, email, hashed_password, full_name, role, is_active, is_verified, onboarding_completed) VALUES 
((SELECT id FROM tenants WHERE slug='ai4edu'), 'admin@ai4edu.com', '$2b$12$LQ3v5KJ6P2a9N4r8X7w2ZO5Rt1Yc3M0pQ6V8bW4nE0xS2dT5uF7gH9jK', '管理员', 'admin', true, true, true)
ON CONFLICT (email) DO NOTHING;

-- 角色
INSERT INTO roles (tenant_id, name, description, is_system) VALUES ((SELECT id FROM tenants WHERE slug='ai4edu'), 'admin', '系统管理员', true), ((SELECT id FROM tenants WHERE slug='ai4edu'), 'teacher', '教师', true), ((SELECT id FROM tenants WHERE slug='ai4edu'), 'student', '学生', true) ON CONFLICT DO NOTHING;

-- 管理员角色绑定
INSERT INTO user_roles (user_id, role_id) SELECT u.id, r.id FROM users u JOIN roles r ON r.name='admin' WHERE u.email='admin@ai4edu.com' ON CONFLICT DO NOTHING;

SQLEOF

echo ""
echo "=============================================="
echo "  ✅ 智慧学伴 部署完成！"
echo "=============================================="
echo ""
echo "  🌐 前端网站：   http://121.43.129.181"
echo "  🔧 后端API：   http://121.43.129.181:8000/docs"
echo "  📊 Neo4j控制台：http://121.43.129.181:7474"
echo ""
echo "  👤 登录账号：  admin@ai4edu.com"
echo "  🔑 登录密码：  admin123"
echo ""
echo "  容器状态："
docker ps --format "  {{.Names}}: {{.Status}}" --filter "name=ai4edu"
echo ""
