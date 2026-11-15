"""
智慧学伴 课堂WebSocket处理器
处理：加入/离开课堂、举手、投票、弹幕、问答
"""
import json
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.websocket.server import ws_manager

logger = logging.getLogger(__name__)


class ClassroomHandler:
    """课堂WebSocket消息处理器"""

    async def handle_connection(
        self,
        websocket: WebSocket,
        classroom_id: int,
        user_id: int,
        user_role: str = "student",
    ) -> None:
        """
        处理课堂WebSocket连接

        Args:
            websocket: WebSocket连接
            classroom_id: 课堂ID
            user_id: 用户ID
            user_role: 用户角色
        """
        room_id = f"classroom_{classroom_id}"

        # 建立连接
        await ws_manager.connect(websocket, user_id)
        await ws_manager.join_room(
            user_id=user_id,
            room_id=room_id,
            metadata={
                "classroom_id": classroom_id,
                "type": "classroom",
            },
        )

        # 发送欢迎消息
        await ws_manager.send_personal(
            user_id=user_id,
            message={
                "type": "connected",
                "classroom_id": classroom_id,
                "member_count": ws_manager.get_room_member_count(room_id),
            },
        )

        try:
            while True:
                data = await websocket.receive_json()
                await self._handle_message(user_id, room_id, classroom_id, user_role, data)
        except WebSocketDisconnect:
            await ws_manager.leave_room(user_id=user_id, room_id=room_id)
            ws_manager.disconnect(user_id)
        except Exception as e:
            logger.error(f"课堂WebSocket异常: classroom_id={classroom_id}, user_id={user_id}, error={e}")
            await ws_manager.leave_room(user_id=user_id, room_id=room_id)
            ws_manager.disconnect(user_id)

    async def _handle_message(
        self,
        user_id: int,
        room_id: str,
        classroom_id: int,
        user_role: str,
        data: Dict[str, Any],
    ) -> None:
        """
        处理课堂消息

        Args:
            user_id: 发送者ID
            room_id: 房间ID
            classroom_id: 课堂ID
            user_role: 用户角色
            data: 消息数据
        """
        msg_type = data.get("type", "")

        handlers = {
            "raise_hand": self._handle_raise_hand,
            "lower_hand": self._handle_lower_hand,
            "vote": self._handle_vote,
            "danmaku": self._handle_danmaku,
            "question": self._handle_question,
            "answer": self._handle_answer,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(user_id, room_id, classroom_id, user_role, data)
        else:
            logger.warning(f"未知的课堂消息类型: {msg_type}")

    async def _handle_raise_hand(
        self,
        user_id: int,
        room_id: str,
        classroom_id: int,
        user_role: str,
        data: Dict[str, Any],
    ) -> None:
        """处理举手"""
        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "hand_raised",
                "user_id": user_id,
                "classroom_id": classroom_id,
            },
        )

    async def _handle_lower_hand(
        self,
        user_id: int,
        room_id: str,
        classroom_id: int,
        user_role: str,
        data: Dict[str, Any],
    ) -> None:
        """处理放下手"""
        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "hand_lowered",
                "user_id": user_id,
                "classroom_id": classroom_id,
            },
        )

    async def _handle_vote(
        self,
        user_id: int,
        room_id: str,
        classroom_id: int,
        user_role: str,
        data: Dict[str, Any],
    ) -> None:
        """处理投票"""
        poll_id = data.get("poll_id")
        selected = data.get("selected_options", [])

        # 通知教师有新投票
        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "vote_cast",
                "poll_id": poll_id,
                "user_id": user_id,
                "classroom_id": classroom_id,
            },
        )

        # 确认投票成功
        await ws_manager.send_personal(
            user_id=user_id,
            message={
                "type": "vote_confirmed",
                "poll_id": poll_id,
            },
        )

    async def _handle_danmaku(
        self,
        user_id: int,
        room_id: str,
        classroom_id: int,
        user_role: str,
        data: Dict[str, Any],
    ) -> None:
        """处理弹幕"""
        content = data.get("content", "")
        color = data.get("color", "#FFFFFF")

        if not content or len(content) > 200:
            return

        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "danmaku",
                "user_id": user_id,
                "content": content,
                "color": color,
                "classroom_id": classroom_id,
            },
        )

    async def _handle_question(
        self,
        user_id: int,
        room_id: str,
        classroom_id: int,
        user_role: str,
        data: Dict[str, Any],
    ) -> None:
        """处理学生提问"""
        content = data.get("content", "")

        if not content:
            return

        # 通知教师有新问题
        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "student_question",
                "user_id": user_id,
                "content": content,
                "classroom_id": classroom_id,
            },
        )

    async def _handle_answer(
        self,
        user_id: int,
        room_id: str,
        classroom_id: int,
        user_role: str,
        data: Dict[str, Any],
    ) -> None:
        """处理教师回答"""
        if user_role not in ("teacher", "assistant", "super_admin"):
            return

        target_user_id = data.get("target_user_id")
        content = data.get("content", "")

        if not content:
            return

        if target_user_id:
            # 定向回答
            await ws_manager.send_personal(
                user_id=target_user_id,
                message={
                    "type": "teacher_answer",
                    "user_id": user_id,
                    "content": content,
                    "classroom_id": classroom_id,
                },
            )

        # 广播给所有人
        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "teacher_answer",
                "user_id": user_id,
                "content": content,
                "target_user_id": target_user_id,
                "classroom_id": classroom_id,
            },
        )


# 全局单例
classroom_handler = ClassroomHandler()
