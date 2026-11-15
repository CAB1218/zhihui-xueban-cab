"""
智慧学伴 WebSocket服务器管理器
维护连接池、房间管理、广播
"""
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket连接管理器

    管理所有WebSocket连接，支持房间（课堂）分组和广播。
    """

    def __init__(self) -> None:
        # 活跃连接：user_id -> WebSocket
        self._connections: Dict[int, WebSocket] = {}
        # 房间成员：room_id -> Set[user_id]
        self._rooms: Dict[str, Set[int]] = defaultdict(set)
        # 用户所在房间：user_id -> Set[room_id]
        self._user_rooms: Dict[int, Set[str]] = defaultdict(set)
        # 房间元数据
        self._room_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """
        接受新的WebSocket连接

        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID
        """
        await websocket.accept()
        self._connections[user_id] = websocket
        logger.info(f"WebSocket连接建立: user_id={user_id}")

    def disconnect(self, user_id: int) -> None:
        """
        断开WebSocket连接

        Args:
            user_id: 用户ID
        """
        self._connections.pop(user_id, None)

        # 从所有房间移除
        rooms = self._user_rooms.pop(user_id, set())
        for room_id in rooms:
            self._rooms[room_id].discard(user_id)
            if not self._rooms[room_id]:
                self._rooms.pop(room_id, None)
                self._room_metadata.pop(room_id, None)

        logger.info(f"WebSocket连接断开: user_id={user_id}")

    async def join_room(self, user_id: int, room_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        将用户加入房间

        Args:
            user_id: 用户ID
            room_id: 房间ID
            metadata: 房间元数据（首次创建时设置）
        """
        self._rooms[room_id].add(user_id)
        self._user_rooms[user_id].add(room_id)

        if metadata and room_id not in self._room_metadata:
            self._room_metadata[room_id] = metadata

        # 通知房间内其他成员
        await self.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "user_joined",
                "user_id": user_id,
                "member_count": len(self._rooms[room_id]),
            },
            exclude_user=user_id,
        )

        logger.info(f"用户 {user_id} 加入房间 {room_id}，当前成员数: {len(self._rooms[room_id])}")

    async def leave_room(self, user_id: int, room_id: str) -> None:
        """
        将用户从房间移除

        Args:
            user_id: 用户ID
            room_id: 房间ID
        """
        self._rooms[room_id].discard(user_id)
        self._user_rooms[user_id].discard(room_id)

        # 通知房间内其他成员
        await self.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "user_left",
                "user_id": user_id,
                "member_count": len(self._rooms[room_id]),
            },
        )

        # 如果房间为空，清理
        if not self._rooms[room_id]:
            self._rooms.pop(room_id, None)
            self._room_metadata.pop(room_id, None)

        logger.info(f"用户 {user_id} 离开房间 {room_id}")

    async def send_personal(self, user_id: int, message: Dict[str, Any]) -> bool:
        """
        向指定用户发送消息

        Args:
            user_id: 目标用户ID
            message: 消息内容

        Returns:
            是否发送成功
        """
        websocket = self._connections.get(user_id)
        if websocket is None:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: user_id={user_id}, error={e}")
            self.disconnect(user_id)
            return False

    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude_user: Optional[int] = None,
    ) -> int:
        """
        向房间内所有成员广播消息

        Args:
            room_id: 房间ID
            message: 消息内容
            exclude_user: 排除的用户ID

        Returns:
            成功发送的消息数量
        """
        members = self._rooms.get(room_id, set())
        sent_count = 0

        for user_id in members:
            if exclude_user and user_id == exclude_user:
                continue
            if await self.send_personal(user_id, message):
                sent_count += 1

        return sent_count

    async def broadcast_all(self, message: Dict[str, Any]) -> int:
        """
        向所有连接的用户广播消息

        Args:
            message: 消息内容

        Returns:
            成功发送的消息数量
        """
        sent_count = 0
        for user_id in list(self._connections.keys()):
            if await self.send_personal(user_id, message):
                sent_count += 1
        return sent_count

    def get_room_members(self, room_id: str) -> List[int]:
        """获取房间成员列表"""
        return list(self._rooms.get(room_id, set()))

    def get_room_member_count(self, room_id: str) -> int:
        """获取房间成员数量"""
        return len(self._rooms.get(room_id, set()))

    def get_user_rooms(self, user_id: int) -> List[str]:
        """获取用户所在房间列表"""
        return list(self._user_rooms.get(user_id, set()))

    def is_user_in_room(self, user_id: int, room_id: str) -> bool:
        """判断用户是否在指定房间"""
        return user_id in self._rooms.get(room_id, set())

    def get_room_metadata(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取房间元数据"""
        return self._room_metadata.get(room_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            "total_connections": len(self._connections),
            "total_rooms": len(self._rooms),
            "rooms": {
                room_id: len(members)
                for room_id, members in self._rooms.items()
            },
        }


# 全局单例
ws_manager = ConnectionManager()
