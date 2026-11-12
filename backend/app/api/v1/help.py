"""
智慧学伴帮助中心 API
提供帮助文章、FAQ、反馈等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.schemas.common import APIResponse, PaginationParams

router = APIRouter()


# ==================== 内置数据 ====================

HELP_CATEGORIES = [
    {"id": "getting-started", "name": "入门指南", "icon": "Guide", "article_count": 3},
    {"id": "graph", "name": "知识图谱", "icon": "Share", "article_count": 2},
    {"id": "ai", "name": "AI 助手", "icon": "ChatDotRound", "article_count": 2},
    {"id": "classroom", "name": "课堂互动", "icon": "Monitor", "article_count": 2},
    {"id": "notes", "name": "智能笔记", "icon": "EditPen", "article_count": 2},
    {"id": "account", "name": "账号与安全", "icon": "Lock", "article_count": 2},
]

HELP_ARTICLES = [
    {"id": 1, "title": "如何开始使用智慧学伴", "category": "getting-started", "content": "智慧学伴是一个智慧教学平台，支持知识图谱浏览、AI助手对话、课堂互动等功能。注册后选择角色即可开始。", "sort_order": 1},
    {"id": 2, "title": "场景模式有什么区别", "category": "getting-started", "content": "智慧学伴提供四种场景：课堂模式（教师主导）、自习模式（自主学习）、考试模式（限时答题）、讨论模式（协作交流）。", "sort_order": 2},
    {"id": 3, "title": "如何上传资源", "category": "getting-started", "content": "在资源页面点击上传按钮，支持 PDF/Word/PPT 等格式，系统会自动解析内容并建立索引。", "sort_order": 3},
    {"id": 4, "title": "知识图谱如何使用", "category": "graph", "content": "进入知识图谱广场选择学科，点击节点查看详情，可浏览关联关系、认知目标、推荐节点等。", "sort_order": 1},
    {"id": 5, "title": "如何创建知识节点", "category": "graph", "content": "在图谱详情页点击创建节点，填写名称和学科分类，可选填描述和认知水平。", "sort_order": 2},
    {"id": 6, "title": "AI 助手有哪些类型", "category": "ai", "content": "智慧学伴提供9类专业智能体：知识问答、作业辅导、测验出题、文件解析、备课、学伴、诊断、课堂管理、心理支持。", "sort_order": 1},
    {"id": 7, "title": "如何与AI流式对话", "category": "ai", "content": "在AI助手页面创建会话，输入问题后系统会实时流式返回回答，支持追问和多轮对话。", "sort_order": 2},
    {"id": 8, "title": "如何加入课堂", "category": "classroom", "content": "输入教师提供的课堂加入码即可加入，支持举手、投票、弹幕等互动方式。", "sort_order": 1},
    {"id": 9, "title": "课堂投票如何使用", "category": "classroom", "content": "教师在课堂中发起投票，学生实时参与，结果即时统计展示。", "sort_order": 2},
    {"id": 10, "title": "智能笔记如何使用", "category": "notes", "content": "创建笔记后可使用AI增强功能：自动摘要、知识点提取、图谱关联推荐。支持Markdown编辑和版本历史。", "sort_order": 1},
    {"id": 11, "title": "笔记如何加密", "category": "notes", "content": "在笔记编辑器中选择加密模式，系统将使用AES-256-CBC端到端加密保护内容。", "sort_order": 2},
    {"id": 12, "title": "如何修改密码", "category": "account", "content": "进入个人设置→安全中心→修改密码，需验证当前密码。", "sort_order": 1},
    {"id": 13, "title": "如何管理权限", "category": "account", "content": "管理员可在后台权限管理页面查看和编辑角色权限，支持学生/教师/助教/管理员四种角色。", "sort_order": 2},
]

FAQ_ITEMS = [
    {"id": 1, "question": "智慧学伴支持哪些学科？", "answer": "目前支持数学、物理、化学、生物、计算机科学、语文、英语、历史、地理、政治、体育、艺术共12个学科。", "category": "getting-started"},
    {"id": 2, "question": "AI 回答的准确度如何？", "answer": "AI回答基于知识图谱和RAG检索增强生成，准确度较高。建议结合教材和教师指导进行学习。", "category": "ai"},
    {"id": 3, "question": "数据是否安全？", "answer": "所有数据采用多租户隔离存储，敏感数据加密保护，符合数据治理和隐私保护要求。", "category": "account"},
    {"id": 4, "question": "课堂最多支持多少人？", "answer": "默认单课堂最大100人，超过80人时系统自动降级为HTTP轮询模式以保证性能。", "category": "classroom"},
    {"id": 5, "question": "支持离线使用吗？", "answer": "支持PWA离线模式，可缓存已浏览的内容和笔记，离线编辑的内容会在恢复网络后自动同步。", "category": "getting-started"},
]


class FeedbackCreate(BaseModel):
    """反馈创建Schema"""
    type: str = Field(..., description="反馈类型: bug/feature/question/other")
    title: str = Field(..., min_length=1, max_length=200, description="反馈标题")
    content: str = Field(..., min_length=1, max_length=2000, description="反馈内容")
    contact: Optional[str] = Field(None, max_length=100, description="联系方式")


@router.get("/articles", summary="获取帮助文章列表")
async def list_articles(
    pagination: PaginationParams = Depends(),
    category: Optional[str] = Query(None, description="分类筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
) -> APIResponse:
    """获取帮助文章列表"""
    articles = HELP_ARTICLES

    if category:
        articles = [a for a in articles if a["category"] == category]
    if search:
        q = search.lower()
        articles = [a for a in articles if q in a["title"].lower() or q in a["content"].lower()]

    total = len(articles)
    start = (pagination.page - 1) * pagination.page_size
    end = start + pagination.page_size
    items = articles[start:end]

    return APIResponse(data={"items": items, "total": total, "page": pagination.page, "page_size": pagination.page_size})


@router.get("/articles/{article_id}", summary="获取文章详情")
async def get_article(article_id: int) -> APIResponse:
    """获取帮助文章详情"""
    for article in HELP_ARTICLES:
        if article["id"] == article_id:
            return APIResponse(data=article)
    return APIResponse(code=40400, message="文章不存在", data=None)


@router.get("/faq", summary="获取FAQ")
async def list_faq(
    category: Optional[str] = Query(None, description="分类筛选"),
) -> APIResponse:
    """获取常见问题列表"""
    items = FAQ_ITEMS
    if category:
        items = [f for f in items if f["category"] == category]
    return APIResponse(data=items)


@router.post("/feedback", summary="提交反馈")
async def submit_feedback(body: FeedbackCreate) -> APIResponse:
    """提交用户反馈"""
    import structlog
    logger = structlog.get_logger()
    logger.info("user_feedback_received", type=body.type, title=body.title)
    return APIResponse(message="反馈提交成功，感谢您的建议！")


@router.get("/categories", summary="获取帮助分类")
async def list_categories() -> APIResponse:
    """获取帮助文章分类列表"""
    return APIResponse(data=HELP_CATEGORIES)
