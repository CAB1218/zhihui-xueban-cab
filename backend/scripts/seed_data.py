"""
AI4Edu 初始数据填充脚本
创建默认租户、管理员、4 角色、40 权限、角色-权限映射
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.security import hash_password
from app.database import Base, async_session_factory, engine
from app.models.tenant import Tenant
from app.models.user import User
from app.models.scene import Scene
from app.models.permission import Role, Permission, RolePermission

# 场景默认数据
DEFAULT_SCENES = [
    {
        "scene_type": "classroom",
        "name": "课堂模式",
        "name_en": "Classroom",
        "icon": "school",
        "primary_color": "#1976D2",
        "description": "专注课堂学习，跟随教师节奏",
        "layout_config": '{"sidebar":true,"widgets":["schedule","announcement","quick_notes","ai_chat"]}',
        "feature_flags": '{"live_qa":true,"poll":true,"hand_raise":true,"group_work":true}',
        "default_widgets": '["schedule","announcement","quick_notes","ai_chat"]',
        "ai_prompt_template": "你是一位课堂学习助手，帮助学生理解课堂内容，解答疑问。",
        "sort_order": 1,
    },
    {
        "scene_type": "self_study",
        "name": "自习模式",
        "name_en": "Self Study",
        "icon": "menu_book",
        "primary_color": "#388E3C",
        "description": "自主学习，按自己节奏学习",
        "layout_config": '{"sidebar":true,"widgets":["knowledge_graph","notes","flash_card","ai_chat"]}',
        "feature_flags": '{"ai_tutor":true,"spaced_repetition":true,"note_link":true,"mind_map":true}',
        "default_widgets": '["knowledge_graph","notes","flash_card","ai_chat"]',
        "ai_prompt_template": "你是一位自习辅导助手，引导学生自主学习，提供学习建议和方法。",
        "sort_order": 2,
    },
    {
        "scene_type": "exam",
        "name": "考前模式",
        "name_en": "Exam Prep",
        "icon": "quiz",
        "primary_color": "#F57C00",
        "description": "考前冲刺，集中复习备考",
        "layout_config": '{"sidebar":true,"widgets":["practice","wrong_notes","countdown","ai_chat"]}',
        "feature_flags": '{"mock_exam":true,"wrong_review":true,"timer":true,"stats":true}',
        "default_widgets": '["practice","wrong_notes","countdown","ai_chat"]',
        "ai_prompt_template": "你是一位考前辅导助手，帮助学生高效复习，提供做题技巧和知识点梳理。",
        "sort_order": 3,
    },
    {
        "scene_type": "discussion",
        "name": "讨论模式",
        "name_en": "Discussion",
        "icon": "forum",
        "primary_color": "#7B1FA2",
        "description": "小组讨论，协作学习",
        "layout_config": '{"sidebar":true,"widgets":["chat","whiteboard","shared_notes","ai_chat"]}',
        "feature_flags": '{"group_chat":true,"whiteboard":true,"shared_doc":true,"vote":true}',
        "default_widgets": '["chat","whiteboard","shared_notes","ai_chat"]',
        "ai_prompt_template": "你是一位讨论助教，帮助小组成员深入讨论，引导思考方向。",
        "sort_order": 4,
    },
]

# 4 个默认角色
DEFAULT_ROLES = [
    {"name": "super_admin", "display_name": "超级管理员", "description": "系统最高权限，可管理所有功能", "is_system": True},
    {"name": "admin", "display_name": "管理员", "description": "租户管理员，管理本租户下的用户和内容", "is_system": True},
    {"name": "teacher", "display_name": "教师", "description": "教师角色，可管理课程、资源、学生", "is_system": True},
    {"name": "student", "display_name": "学生", "description": "学生角色，可学习、做笔记、参与讨论", "is_system": True},
]

# 示例课程（classrooms/growth 等模块依赖 courses 外键，缺数据会直接 500）
DEFAULT_COURSES = [
    {
        "name": "高等数学（上）",
        "code": "MATH101",
        "subject": "math",
        "grade": "大一",
        "semester": "2026-fall",
        "description": "函数、极限、导数与积分，配套数学知识图谱。",
    },
    {
        "name": "大学物理",
        "code": "PHYS101",
        "subject": "physics",
        "grade": "大一",
        "semester": "2026-fall",
        "description": "力学、电磁学基础，配套物理知识图谱。",
    },
    {
        "name": "数据结构",
        "code": "CS201",
        "subject": "cs",
        "grade": "大二",
        "semester": "2026-fall",
        "description": "线性表、树、图与常用算法。",
    },
    {
        "name": "线性代数",
        "code": "MATH201",
        "subject": "math",
        "grade": "大一",
        "semester": "2026-fall",
        "description": "矩阵、行列式、向量空间与线性变换。",
    },
]

# 40 个权限定义（8 个模块，每模块 5 个）
DEFAULT_PERMISSIONS = [
    # ---- 认证模块 (auth) ----
    {"name": "auth:login", "display_name": "登录", "module": "auth", "description": "用户登录系统"},
    {"name": "auth:logout", "display_name": "登出", "module": "auth", "description": "用户登出系统"},
    {"name": "auth:refresh", "display_name": "刷新Token", "module": "auth", "description": "刷新访问令牌"},
    {"name": "auth:password_change", "display_name": "修改密码", "module": "auth", "description": "修改自己的密码"},
    {"name": "auth:password_reset", "display_name": "重置密码", "module": "auth", "description": "管理员重置用户密码"},

    # ---- 用户模块 (user) ----
    {"name": "user:list", "display_name": "查看用户列表", "module": "user", "description": "查看用户列表和详情"},
    {"name": "user:create", "display_name": "创建用户", "module": "user", "description": "创建新用户"},
    {"name": "user:update", "display_name": "更新用户", "module": "user", "description": "更新用户信息"},
    {"name": "user:delete", "display_name": "删除用户", "module": "user", "description": "删除用户"},
    {"name": "user:export", "display_name": "导出用户", "module": "user", "description": "导出用户数据"},

    # ---- 课程模块 (course) ----
    {"name": "course:list", "display_name": "查看课程", "module": "course", "description": "查看课程列表"},
    {"name": "course:create", "display_name": "创建课程", "module": "course", "description": "创建新课程"},
    {"name": "course:update", "display_name": "更新课程", "module": "course", "description": "更新课程信息"},
    {"name": "course:delete", "display_name": "删除课程", "module": "course", "description": "删除课程"},
    {"name": "course:enroll", "display_name": "加入课程", "module": "course", "description": "加入课程学习"},

    # ---- 资源模块 (resource) ----
    {"name": "resource:list", "display_name": "查看资源", "module": "resource", "description": "查看资源列表"},
    {"name": "resource:upload", "display_name": "上传资源", "module": "resource", "description": "上传学习资源"},
    {"name": "resource:download", "display_name": "下载资源", "module": "resource", "description": "下载学习资源"},
    {"name": "resource:delete", "display_name": "删除资源", "module": "resource", "description": "删除资源"},
    {"name": "resource:audit", "display_name": "审核资源", "module": "resource", "description": "审核资源内容"},

    # ---- 知识图谱模块 (knowledge) ----
    {"name": "knowledge:view", "display_name": "查看图谱", "module": "knowledge", "description": "查看知识图谱"},
    {"name": "knowledge:edit", "display_name": "编辑图谱", "module": "knowledge", "description": "编辑知识图谱节点"},
    {"name": "knowledge:delete", "display_name": "删除图谱", "module": "knowledge", "description": "删除知识图谱"},
    {"name": "knowledge:import", "display_name": "导入图谱", "module": "knowledge", "description": "导入知识图谱数据"},
    {"name": "knowledge:export", "display_name": "导出图谱", "module": "knowledge", "description": "导出知识图谱数据"},

    # ---- 笔记模块 (note) ----
    {"name": "note:list", "display_name": "查看笔记", "module": "note", "description": "查看笔记列表"},
    {"name": "note:create", "display_name": "创建笔记", "module": "note", "description": "创建新笔记"},
    {"name": "note:update", "display_name": "更新笔记", "module": "note", "description": "更新笔记内容"},
    {"name": "note:delete", "display_name": "删除笔记", "module": "note", "description": "删除笔记"},
    {"name": "note:share", "display_name": "分享笔记", "module": "note", "description": "分享笔记给他人"},

    # ---- AI 模块 (ai) ----
    {"name": "ai:chat", "display_name": "AI对话", "module": "ai", "description": "使用 AI 对话功能"},
    {"name": "ai:diagnose", "display_name": "学习诊断", "module": "ai", "description": "使用 AI 学习诊断"},
    {"name": "ai:generate", "display_name": "AI生成", "module": "ai", "description": "使用 AI 生成内容"},
    {"name": "ai:config", "display_name": "AI配置", "module": "ai", "description": "配置 AI 参数和模板"},
    {"name": "ai:history", "display_name": "AI历史", "module": "ai", "description": "查看 AI 对话历史"},

    # ---- 系统管理模块 (system) ----
    {"name": "system:dashboard", "display_name": "系统面板", "module": "system", "description": "查看系统仪表盘"},
    {"name": "system:settings", "display_name": "系统设置", "module": "system", "description": "修改系统设置"},
    {"name": "system:logs", "display_name": "系统日志", "module": "system", "description": "查看系统日志"},
    {"name": "system:backup", "display_name": "系统备份", "module": "system", "description": "系统数据备份"},
    {"name": "system:monitor", "display_name": "系统监控", "module": "system", "description": "查看系统运行状态"},
]

# 角色-权限映射（角色名 -> 权限名列表）
ROLE_PERMISSION_MAP = {
    "super_admin": [p["name"] for p in DEFAULT_PERMISSIONS],  # 所有权限
    "admin": [
        "auth:login", "auth:logout", "auth:refresh", "auth:password_change", "auth:password_reset",
        "user:list", "user:create", "user:update", "user:export",
        "course:list", "course:create", "course:update", "course:enroll",
        "resource:list", "resource:upload", "resource:download", "resource:audit",
        "knowledge:view", "knowledge:edit", "knowledge:import", "knowledge:export",
        "note:list", "note:create", "note:update", "note:delete", "note:share",
        "ai:chat", "ai:diagnose", "ai:generate", "ai:history",
        "system:dashboard", "system:logs", "system:monitor",
    ],
    "teacher": [
        "auth:login", "auth:logout", "auth:refresh", "auth:password_change",
        "user:list",
        "course:list", "course:create", "course:update", "course:enroll",
        "resource:list", "resource:upload", "resource:download",
        "knowledge:view", "knowledge:edit", "knowledge:import", "knowledge:export",
        "note:list", "note:create", "note:update", "note:delete", "note:share",
        "ai:chat", "ai:diagnose", "ai:generate", "ai:history",
    ],
    "student": [
        "auth:login", "auth:logout", "auth:refresh", "auth:password_change",
        "course:list", "course:enroll",
        "resource:list", "resource:download",
        "knowledge:view",
        "note:list", "note:create", "note:update", "note:delete", "note:share",
        "ai:chat", "ai:diagnose", "ai:history",
    ],
}


async def seed_data():
    """执行数据填充"""

    print("开始数据填充...")

    # 创建所有表（仅 PostgreSQL 表，跳过 ClickHouse 等外部数据库的表）
    print("创建数据库表...")
    try:
        postgres_tables = [
            table for table in Base.metadata.sorted_tables if table.schema is None
        ]
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, tables=postgres_tables)
        print("数据库表创建完成")
    except Exception as e:
        err_msg = str(e).lower()
        if "clickhouse" in err_msg or "schema" in err_msg:
            print(f"[WARN] 跳过非 PostgreSQL 表创建（{type(e).__name__}），继续初始化数据...")
        else:
            raise
    print("数据库表就绪")

    async with async_session_factory() as session:
        from sqlalchemy.future import select

        # 1. 创建默认租户
        print("创建默认租户...")
        result = await session.execute(select(Tenant).where(Tenant.slug == "default"))
        existing_tenant = result.scalars().first()

        if not existing_tenant:
            tenant = Tenant(
                name="默认租户",
                slug="default",
                schema_name="tenant_1",
                domain=None,
                plan="enterprise",
                max_users=9999,
                max_storage_mb=102400,
                settings="{}",
                is_active=True,
            )
            session.add(tenant)
            await session.flush()
            tenant_id = tenant.id
            print(f"默认租户已创建，ID: {tenant_id}")
        else:
            tenant_id = existing_tenant.id
            print(f"默认租户已存在，ID: {tenant_id}")

        # 2. 创建超级管理员
        print("创建超级管理员...")
        result = await session.execute(select(User).where(User.email == "admin@ai4edu.com"))
        existing_admin = result.scalars().first()

        if not existing_admin:
            admin = User(
                tenant_id=tenant_id,
                email="admin@ai4edu.com",
                password_hash=hash_password("admin123"),
                nickname="超级管理员",
                role="super_admin",
                default_scene="classroom",
                locale="zh-CN",
                onboarding_completed=True,
                is_active=True,
            )
            session.add(admin)
            print("超级管理员已创建 (admin@ai4edu.com / admin123)")
        else:
            print("超级管理员已存在")

        # 3. 创建场景数据
        print("创建场景数据...")
        for scene_data in DEFAULT_SCENES:
            result = await session.execute(
                select(Scene).where(Scene.scene_type == scene_data["scene_type"])
            )
            existing_scene = result.scalars().first()
            if not existing_scene:
                scene = Scene(**scene_data)
                session.add(scene)
                print(f"场景 '{scene_data['name']}' 已创建")
            else:
                # 更新已有场景的配置
                for key, value in scene_data.items():
                    if key != "scene_type":
                        setattr(existing_scene, key, value)
                print(f"场景 '{scene_data['name']}' 已更新")

        # 4. 创建角色
        print("创建默认角色...")
        role_map = {}  # name -> Role object
        for role_data in DEFAULT_ROLES:
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            existing_role = result.scalars().first()
            if not existing_role:
                role = Role(**role_data)
                session.add(role)
                await session.flush()
                role_map[role_data["name"]] = role
                print(f"角色 '{role_data['display_name']}' 已创建")
            else:
                role_map[role_data["name"]] = existing_role
                print(f"角色 '{role_data['display_name']}' 已存在")

        # 5. 创建权限
        print("创建权限数据...")
        perm_map = {}  # name -> Permission object
        for perm_data in DEFAULT_PERMISSIONS:
            result = await session.execute(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            existing_perm = result.scalars().first()
            if not existing_perm:
                perm = Permission(**perm_data)
                session.add(perm)
                await session.flush()
                perm_map[perm_data["name"]] = perm
            else:
                perm_map[perm_data["name"]] = existing_perm
        print(f"权限数据就绪，共 {len(perm_map)} 项")

        # 6. 创建角色-权限映射
        print("创建角色-权限映射...")
        rp_count = 0
        for role_name, perm_names in ROLE_PERMISSION_MAP.items():
            role = role_map.get(role_name)
            if not role:
                continue

            # 获取已有映射
            existing_rp = await session.execute(
                select(RolePermission.permission_id).where(RolePermission.role_id == role.id)
            )
            existing_perm_ids = {row[0] for row in existing_rp.all()}

            for perm_name in perm_names:
                perm = perm_map.get(perm_name)
                if perm and perm.id not in existing_perm_ids:
                    rp = RolePermission(role_id=role.id, permission_id=perm.id)
                    session.add(rp)
                    rp_count += 1

        print(f"角色-权限映射已创建，新增 {rp_count} 条")

        # 7. 创建示例课程（课堂互动 / 教师工作台依赖 courses，缺数据会外键失败）
        print("创建示例课程...")
        from app.models.course import Course

        result = await session.execute(select(User).where(User.email == "admin@ai4edu.com"))
        teacher_user = result.scalars().first()
        teacher_id = teacher_user.id if teacher_user else 1

        for course_data in DEFAULT_COURSES:
            result = await session.execute(
                select(Course).where(Course.code == course_data["code"])
            )
            if result.scalars().first():
                print(f"课程 '{course_data['name']}' 已存在")
                continue
            session.add(
                Course(
                    tenant_id=tenant_id,
                    teacher_id=teacher_id,
                    is_active=True,
                    **course_data,
                )
            )
            print(f"课程 '{course_data['name']}' 已创建")

        await session.commit()

    print("数据填充完成！")


if __name__ == "__main__":
    asyncio.run(seed_data())
