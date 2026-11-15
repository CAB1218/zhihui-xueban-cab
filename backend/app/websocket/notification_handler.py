"""
智慧学伴 通知WebSocket处理器
推送实时通知
"""
import json
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.websocket.server import ws_manager

logger = logging.getLogger(__name__)


class NotificationHandler:
    """通知WebSocket处理器"""

    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: int,
    ) -> None:
        """
        处理通知WebSocket连接

        Args:
            websocket: WebSocket连接
            user_id: 用户ID
        """
        room_id = f"notifications_{user_id}"

        await ws_manager.connect(websocket, user_id)
        await ws_manager.join_room(
            user_id=user_id,
            room_id=room_id,
            metadata={"type": "notifications"},
        )

        try:
            while True:
                data = await websocket.receive_json()
                await self._handle_message(user_id, room_id, data)
        except WebSocketDisconnect:
            await ws_manager.leave_room(user_id=user_id, room_id=room_id)
            ws_manager.disconnect(user_id)
        except Exception as e:
            logger.error(f"通知WebSocket异常: user_id={user_id}, error={e}")
            await ws_manager.leave_room(user_id=user_id, room_id=room_id)
            ws_manager.disconnect(user_id)

    async def _handle_message(
        self,
        user_id: int,
        room_id: str,
        data: Dict[str, Any],
    ) -> None:
        """
        处理通知消息

        Args:
            user_id: 用户ID
            room_id: 房间ID
            data: 消息数据
        """
        msg_type = data.get("type", "")

        if msg_type == "mark_read":
            # 客户端确认已读
            notification_id = data.get("notification_id")
            if notification_id:
                await ws_manager.send_personal(
                    user_id=user_id,
                    message={
                        "type": "read_confirmed",
                        "notification_id": notification_id,
                    },
                )

        elif msg_type == "subscribe":
            # 订阅特定通知类型
            notification_types = data.get("notification_types", [])
            await ws_manager.send_personal(
                user_id=user_id,
                message={
                    "type": "subscribed",
                    "notification_types": notification_types,
                },
            )

        elif msg_type == "ping":
            # 心跳
            await ws_manager.send_personal(
                user_id=user_id,
                message={"type": "pong"},
            )

    async def push_notification(
        self,
        user_id: int,
        notification: Dict[str, Any],
    ) -> bool:
        """
        向用户推送实时通知

        Args:
            user_id: 目标用户ID
            notification: 通知内容

        Returns:
            是否推送成功
        """
        message = {
            "type": "notification",
            **notification,
        }
        return await ws_manager.send_personal(user_id=user_id, message=message)

    async def push_to_users(
        self,
        user_ids: list[int],
        notification: Dict[str, Any],
    ) -> int:
        """
        向多个用户推送通知

        Args:
            user_ids: 目标用户ID列表
            notification: 通知内容

        Returns:
            成功推送数量
        """
        sent_count = 0
        for uid in user_ids:
            if await self.push_notification(uid, notification):
                sent_count += 1
        return sent_count


# 全局单例
notification_handler = NotificationHandler()
