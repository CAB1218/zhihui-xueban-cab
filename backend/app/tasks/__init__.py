"""
智慧学伴 Celery Tasks 包初始化
自动导入并注册以下任务模块:
- extraction_tasks: OCR/ASR 提取任务
- export_tasks: 对话导出任务
- health_check: 模型健康检查任务
"""
from app.tasks import extraction_tasks
from app.tasks import export_tasks
from app.tasks import health_check
