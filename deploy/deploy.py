"""
智慧学伴 生产部署脚本
一键构建镜像、初始化数据、启动服务
"""
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DEPLOY_DIR = PROJECT_ROOT / "deploy"


def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """执行 shell 命令"""
    print(f"🔧 {cmd}")
    return subprocess.run(cmd, shell=True, check=check)


def build_images():
    """构建 Docker 镜像"""
    print("\n📦 Step 1: 构建 Docker 镜像...")

    # 构建后端镜像
    run(
        f"docker build -f {DEPLOY_DIR}/Dockerfile.backend "
        f"-t ai4edu/backend:latest {PROJECT_ROOT}/backend"
    )

    # 构建前端镜像
    run(
        f"docker build -f {DEPLOY_DIR}/Dockerfile.frontend "
        f"-t ai4edu/frontend:latest {PROJECT_ROOT}/frontend"
    )

    print("✅ 镜像构建完成")


def start_services():
    """启动所有服务"""
    print("\n🚀 Step 2: 启动服务...")

    run(
        f"docker compose -f {DEPLOY_DIR}/docker-compose.prod.yml "
        f"up -d"
    )

    print("⏳ 等待服务启动...")
    time.sleep(15)


def check_health():
    """健康检查"""
    print("\n🏥 Step 3: 健康检查...")

    services = {
        "后端": "http://localhost:8000/health",
        "前端": "http://localhost/health",
        "ClickHouse": "http://localhost:8123/?query=SELECT%201",
        "Elasticsearch": "http://localhost:9200/_cluster/health",
    }

    all_ok = True
    for name, url in services.items():
        result = run(f"curl -sf {url} -o /dev/null", check=False)
        status = "✅" if result.returncode == 0 else "❌"
        print(f"  {status} {name}: {url}")
        if result.returncode != 0:
            all_ok = False

    if all_ok:
        print("\n🎉 所有服务运行正常！")
    else:
        print("\n⚠️ 部分服务未就绪，请检查日志")


def init_infra():
    """初始化基础设施"""
    print("\n🏗️ Step 4: 初始化基础设施...")

    run(
        f"docker exec ai4edu-backend "
        f"python scripts/init_infra.py"
    )

    print("✅ 基础设施初始化完成")


def main():
    """主流程"""
    print("=" * 60)
    print("🚀 智慧学伴 生产部署")
    print("=" * 60)

    steps = [
        ("构建镜像", build_images),
        ("启动服务", start_services),
        ("健康检查", check_health),
        ("初始化基础设施", init_infra),
    ]

    for step_name, step_fn in steps:
        try:
            step_fn()
        except subprocess.CalledProcessError as e:
            print(f"\n❌ 步骤失败: {step_name}")
            print(f"   错误: {e}")
            print(f"\n💡 排查建议:")
            print(f"   docker compose -f {DEPLOY_DIR}/docker-compose.prod.yml logs")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 部署完成！")
    print("=" * 60)
    print("\n📋 访问地址:")
    print("  前端:    https://localhost")
    print("  后端API: https://localhost/api/v1/docs")
    print("  MinIO:   http://localhost:9001")
    print("  Grafana: http://localhost:3001")
    print("  Prometheus: http://localhost:9090")


if __name__ == "__main__":
    main()
