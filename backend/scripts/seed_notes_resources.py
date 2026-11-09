"""
为笔记和资源模块补充种子数据
使用 pg8000（纯 Python PG 驱动）直接连接 PostgreSQL
"""
import pg8000
import json
import os
from datetime import datetime, timezone

# DB config — 优先读环境变量，容器内由 docker-compose 注入（POSTGRES_HOST=postgres）
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "ai4edu"),
    "user": os.getenv("POSTGRES_USER", "ai4edu"),
    "password": os.getenv("POSTGRES_PASSWORD", "ai4edu_password"),
}

def get_conn():
    return pg8000.connect(**DB_CONFIG)

def fetch_one(conn, sql):
    cursor = conn.cursor()
    cursor.execute(sql)
    row = cursor.fetchone()
    cursor.close()
    return row

def fetch_all(conn, sql):
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    cursor.close()
    return [dict(zip(cols, r)) for r in rows]

def main():
    conn = get_conn()
    print("=== AI4Edu 笔记&资源种子数据 ===\n")

    # 1. 获取 tenant / user / course
    tenants = fetch_all(conn, "SELECT id, name FROM tenants LIMIT 5")
    print(f"租户: {[(t['id'], t['name']) for t in tenants]}")

    if not tenants:
        print("!! 没有租户数据，请先运行 seed_data.py")
        return

    tenant_id = tenants[0]["id"]
    print(f"使用 tenant_id = {tenant_id}\n")

    # 字段名: email, nickname, role
    users = fetch_all(conn, f"SELECT id, email, nickname, role FROM users WHERE tenant_id = {tenant_id} LIMIT 10")
    print(f"用户: {[(u['id'], u['nickname'] or u['email'], u['role']) for u in users]}")

    if not users:
        print("!! 没有用户数据")
        return

    admin_user    = next((u for u in users if u["role"] == "admin"), users[0])
    teacher_user  = next((u for u in users if u["role"] == "teacher"), users[0])
    student_user  = next((u for u in users if u["role"] == "student"), users[0])
    print(f"管理员: {admin_user['nickname'] or admin_user['email']}({admin_user['id']})")
    print(f"教师:   {teacher_user['nickname'] or teacher_user['email']}({teacher_user['id']})")
    print(f"学生:   {student_user['nickname'] or student_user['email']}({student_user['id']})\n")

    courses = fetch_all(conn, f"SELECT id, name FROM courses WHERE tenant_id = {tenant_id} LIMIT 10")
    print(f"课程: {[(c['id'], c['name']) for c in courses]}")
    course_id = courses[0]["id"] if courses else None
    print(f"使用 course_id = {course_id}\n")

    now = datetime.now(timezone.utc)

    # 2. 插入笔记种子数据
    print("--- 插入笔记种子数据 ---")
    notes_data = [
        {
            "tenant_id": tenant_id,
            "title": "一元二次方程知识点总结",
            "content": "<h2>一元二次方程</h2><p>一般形式：<code>ax² + bx + c = 0</code></p><p>求根公式：<code>x = (-b ± √(b²-4ac)) / 2a</code></p><h3>判别式的意义</h3><ul><li>Δ > 0：两个不等实根</li><li>Δ = 0：两个相等实根</li><li>Δ < 0：无实根</li></ul>",
            "content_plain": "一元二次方程 一般形式：ax²+bx+c=0 求根公式：x=(-b±√(b²-4ac))/2a 判别式意义：Δ>0两个不等实根 Δ=0两个相等实根 Δ<0无实根",
            "note_type": "personal",
            "course_id": course_id,
            "owner_id": student_user["id"],
            "tags": json.dumps(["数学", "一元二次方程", "期末复习"]),
            "ai_enhanced": False,
            "word_count": 120,
            "version": 1,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        },
        {
            "tenant_id": tenant_id,
            "title": "牛顿运动定律笔记",
            "content": "<h2>牛顿三大运动定律</h2><h3>第一定律（惯性定律）</h3><p>物体在没有外力作用时，保持静止或匀速直线运动状态。</p><h3>第二定律（加速度定律）</h3><p><code>F = ma</code></p><h3>第三定律（作用与反作用）</h3><p>两个物体之间的作用力和反作用力，大小相等，方向相反。</p>",
            "content_plain": "牛顿三大运动定律 第一定律惯性定律 第二定律F=ma 第三定律作用与反作用",
            "note_type": "course",
            "course_id": course_id,
            "owner_id": student_user["id"],
            "tags": json.dumps(["物理", "牛顿定律", "力学"]),
            "ai_enhanced": True,
            "word_count": 200,
            "version": 1,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        },
        {
            "tenant_id": tenant_id,
            "title": "AI 辅助生成的：二次函数图像性质",
            "content": "<h2>二次函数图像性质（AI增强）</h2><p>AI已为你补充以下内容：</p><h3>开口方向</h3><ul><li>a > 0：开口向上，有最小值</li><li>a < 0：开口向下，有最大值</li></ul><h3>顶点坐标</h3><p>顶点：<code>(-b/2a, (4ac-b²)/4a)</code></p>",
            "content_plain": "二次函数图像性质 AI增强 开口方向 a>0向上 a<0向下 顶点坐标(-b/2a,(4ac-b²)/4a)",
            "note_type": "ai_generated",
            "course_id": course_id,
            "owner_id": student_user["id"],
            "tags": json.dumps(["数学", "二次函数", "AI辅助"]),
            "ai_enhanced": True,
            "word_count": 180,
            "version": 1,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        },
        {
            "tenant_id": tenant_id,
            "title": "教师备课笔记：光的折射",
            "content": "<h2>光的折射</h2><p>光从一种介质进入另一种介质时，传播方向发生改变的现象。</p><h3>折射定律</h3><ol><li>入射光线、折射光线和法线在同一平面内</li><li>折射光线和入射光线分居法线两侧</li><li><code>n₁sinθ₁ = n₂sinθ₂</code>（斯涅尔定律）</li></ol>",
            "content_plain": "光的折射 折射定律 斯涅尔定律 n₁sinθ₁=n₂sinθ₂",
            "note_type": "course",
            "course_id": course_id,
            "owner_id": teacher_user["id"],
            "tags": json.dumps(["物理", "光学", "备课"]),
            "ai_enhanced": False,
            "word_count": 150,
            "version": 1,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        },
        {
            "tenant_id": tenant_id,
            "title": "期末复习计划",
            "content": "<h2>期末复习计划</h2><ol><li>数学：复习二次函数、一元二次方程</li><li>物理：复习牛顿定律、光的折射</li><li>化学：复习化学反应方程式</li></ol><p><strong>目标：</strong>每科平均85分以上</p>",
            "content_plain": "期末复习计划 数学二次函数一元二次方程 物理牛顿定律光的折射 化学",
            "note_type": "personal",
            "course_id": None,
            "owner_id": student_user["id"],
            "tags": json.dumps(["复习计划", "期末"]),
            "ai_enhanced": False,
            "word_count": 100,
            "version": 1,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        },
    ]

    note_ids = []
    cursor = conn.cursor()
    for note in notes_data:
        existing = fetch_one(conn, f"SELECT id FROM notes WHERE title = '{note['title']}' AND tenant_id = {tenant_id}")
        if existing:
            print(f"  跳过（已存在）: {note['title']}")
            note_ids.append(existing[0])
            continue

        cursor.execute(
            """INSERT INTO notes
               (tenant_id, title, content, content_plain, note_type, course_id, owner_id,
                tags, ai_enhanced, word_count, version, is_deleted, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (note["tenant_id"], note["title"], note["content"], note["content_plain"],
             note["note_type"], note["course_id"], note["owner_id"],
             note["tags"], note["ai_enhanced"], note["word_count"],
             note["version"], note["is_deleted"], note["created_at"], note["updated_at"])
        )
        note_id = cursor.fetchone()[0]
        conn.commit()
        note_ids.append(note_id)
        print(f"  [OK] {note['title']} (id={note_id})")
    cursor.close()

    print(f"\n共 {len(note_ids)} 条笔记")

    # 3. 插入资源种子数据
    print("\n--- 插入资源种子数据 ---")
    resources_data = [
        {
            "tenant_id": tenant_id,
            "title": "一元二次方程讲义.pdf",
            "description": "涵盖一元二次方程的定义、解法（配方法、公式法、因式分解法）和典型例题",
            "resource_type": "pdf",
            "mime_type": "application/pdf",
            "file_size": 2048000,
            "file_key": "resources/math/quadratic_equation.pdf",
            "url": "/api/v1/resources/download/math/quadratic_equation.pdf",
            "thumbnail_url": None,
            "course_id": course_id,
            "uploader_id": teacher_user["id"],
            "download_count": 15,
            "view_count": 42,
            "tags": json.dumps(["数学", "一元二次方程", "讲义"]),
            "metadata_json": json.dumps({"page_count": 12, "author": "张老师"}),
            "is_public": True,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "tenant_id": tenant_id,
            "title": "牛顿定律教学视频.mp4",
            "description": "详细讲解牛顿三大运动定律，配有实验演示和习题讲解",
            "resource_type": "video",
            "mime_type": "video/mp4",
            "file_size": 52428800,
            "file_key": "resources/physics/newton_laws.mp4",
            "url": "/api/v1/resources/download/physics/newton_laws.mp4",
            "thumbnail_url": "/api/v1/resources/thumbnail/physics/newton_laws.jpg",
            "course_id": course_id,
            "uploader_id": teacher_user["id"],
            "download_count": 8,
            "view_count": 67,
            "tags": json.dumps(["物理", "牛顿定律", "教学视频"]),
            "metadata_json": json.dumps({"duration": 1800, "resolution": "1080p"}),
            "is_public": True,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "tenant_id": tenant_id,
            "title": "期末考试复习提纲.docx",
            "description": "数学、物理、化学三科期末考试重点知识复习提纲",
            "resource_type": "docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "file_size": 512000,
            "file_key": "resources/review/final_review.docx",
            "url": "/api/v1/resources/download/review/final_review.docx",
            "thumbnail_url": None,
            "course_id": None,
            "uploader_id": student_user["id"],
            "download_count": 23,
            "view_count": 55,
            "tags": json.dumps(["复习", "期末考试", "提纲"]),
            "metadata_json": json.dumps({"page_count": 8}),
            "is_public": True,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "tenant_id": tenant_id,
            "title": "二次函数图像交互课件.pptx",
            "description": "交互式 PowerPoint 课件，包含二次函数图像动态演示",
            "resource_type": "pptx",
            "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "file_size": 8192000,
            "file_key": "resources/math/quadratic_function.pptx",
            "url": "/api/v1/resources/download/math/quadratic_function.pptx",
            "thumbnail_url": "/api/v1/resources/thumbnail/math/quadratic_function.jpg",
            "course_id": course_id,
            "uploader_id": teacher_user["id"],
            "download_count": 12,
            "view_count": 38,
            "tags": json.dumps(["数学", "二次函数", "课件"]),
            "metadata_json": json.dumps({"slide_count": 25}),
            "is_public": True,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "tenant_id": tenant_id,
            "title": "光的折射实验指导.pdf",
            "description": "学生分组实验指导书，包含实验目的、器材、步骤和数据处理方法",
            "resource_type": "pdf",
            "mime_type": "application/pdf",
            "file_size": 1536000,
            "file_key": "resources/physics/light_refraction.pdf",
            "url": "/api/v1/resources/download/physics/light_refraction.pdf",
            "thumbnail_url": None,
            "course_id": course_id,
            "uploader_id": teacher_user["id"],
            "download_count": 6,
            "view_count": 18,
            "tags": json.dumps(["物理", "光学", "实验"]),
            "metadata_json": json.dumps({"page_count": 8, "experiment_duration": "45min"}),
            "is_public": True,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]

    resource_ids = []
    cursor = conn.cursor()
    for res in resources_data:
        existing = fetch_one(conn, f"SELECT id FROM resources WHERE title = '{res['title']}' AND tenant_id = {tenant_id}")
        if existing:
            print(f"  跳过（已存在）: {res['title']}")
            resource_ids.append(existing[0])
            continue

        cursor.execute(
            """INSERT INTO resources
               (tenant_id, title, description, resource_type, mime_type, file_size,
                file_key, url, thumbnail_url, course_id, uploader_id,
                download_count, view_count, tags, metadata_json,
                is_public, is_active, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (res["tenant_id"], res["title"], res["description"], res["resource_type"],
             res["mime_type"], res["file_size"], res["file_key"], res["url"],
             res["thumbnail_url"], res["course_id"], res["uploader_id"],
             res["download_count"], res["view_count"], res["tags"], res["metadata_json"],
             res["is_public"], res["is_active"], res["created_at"], res["updated_at"])
        )
        res_id = cursor.fetchone()[0]
        conn.commit()
        resource_ids.append(res_id)
        print(f"  [OK] {res['title']} (id={res_id})")
    cursor.close()

    print(f"\n共 {len(resource_ids)} 条资源")

    # 4. 验证
    note_count    = fetch_one(conn, f"SELECT COUNT(*) FROM notes WHERE tenant_id = {tenant_id}")[0]
    resource_count = fetch_one(conn, f"SELECT COUNT(*) FROM resources WHERE tenant_id = {tenant_id}")[0]
    print(f"\n租户 {tenant_id} 笔记总数: {note_count}")
    print(f"租户 {tenant_id} 资源总数: {resource_count}")
    print("\n=== 种子数据插入完成 ===")

    conn.close()

if __name__ == "__main__":
    main()
