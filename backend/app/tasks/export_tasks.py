"""
智慧学伴 对话导出 Celery 任务
异步执行会话导出（Markdown / PDF），上传到 MinIO。

任务流程:
1. 从 DB 读取 AgentExport 记录（status=pending）
2. 标记 status=processing
3. 调用 AgentExportService.generate_and_upload()
4. 更新 status=completed + file_key + file_size
5. 异常 → status=failed + error_msg
"""
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.export_tasks.export_session_task")
def export_session_task(export_id: int) -> dict:
    """对话导出 Celery 任务

    在 Celery worker（同步进程）中执行：
    - 使用同步 DB session
    - 调用 AgentExportService.generate_and_upload()
    - 该方法内部使用 get_sync_session() 获取同步会话

    Args:
        export_id: AgentExport 记录 ID

    Returns:
        {"export_id": int, "status": str, "file_key": str | None}
    """
    logger.info("开始执行导出任务: export_id=%s", export_id)

    try:
        from app.services.agent_export_service import AgentExportService

        # AgentExportService.generate_and_upload 内部使用同步 session
        # 传入 db=None，因为 generate_and_upload 内部会创建同步 session
        service = AgentExportService(db=None)  # type: ignore

        export_record = service.generate_and_upload_sync(export_id)

        result = {
            "export_id": export_record.id,
            "status": export_record.status,
            "file_key": export_record.file_key,
        }

        if export_record.status == "completed":
            logger.info(
                "导出任务完成: export_id=%s, file_key=%s",
                export_id,
                export_record.file_key,
            )
        else:
            logger.warning(
                "导出任务未完成: export_id=%s, status=%s, error=%s",
                export_id,
                export_record.status,
                export_record.error_msg,
            )

        return result

    except Exception as e:
        logger.error("导出任务异常 export_id=%s: %s", export_id, e, exc_info=True)
        return {
            "export_id": export_id,
            "status": "failed",
            "file_key": None,
            "error": str(e)[:500],
        }
