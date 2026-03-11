"""
Stonk - WebSocket 服务器主程序

实现异步 WebSocket 服务器，处理客户端连接、消息分发、房间管理等。
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
import time
import websockets
from websockets.server import WebSocketServerProtocol

from shared.message_protocol import MessageType, create_message, parse_message
from shared.utils import generate_id, get_timestamp
from shared.constants import SERVER_HEARTBEAT_INTERVAL
from server.models import DatabaseManager
from server.config import HOST, PORT, HEARTBEAT_INTERVAL, CLIENT_HEARTBEAT_TIMEOUT

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StonkWebSocketServer:
    """WebSocket 服务器类"""
    
    def __init__(self, host: str = HOST, port: int = PORT):
        """
        初始化服务器。
        
        Args:
            host: 服务器地址
            port: 服务器端口
        """
        self.host = host
        self.port = port
        self.db = DatabaseManager()
        
        # 连接管理
        self.clients: Dict[WebSocketServerProtocol, Dict[str, Any]] = {}  # 连接 -> 客户端信息
        self.user_connections: Dict[str, WebSocketServerProtocol] = {}  # 用户 ID -> 连接
        self.room_users: Dict[str, Set[str]] = {}  # 房间 ID -> 用户 ID 集合
        self.user_last_heartbeat: Dict[str, float] = {}  # 用户 ID -> 最后心跳时间
        
    async def initialize(self) -> None:
        """初始化服务器"""
        await self.db.initialize()
        logger.info(f"WebSocket server initialized at {self.host}:{self.port}")
    
    async def start(self) -> None:
        """启动服务器"""
        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
                
                # 启动后台任务
                await asyncio.gather(
                    self.heartbeat_monitor_task(),
                )
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """
        处理客户端连接。
        
        Args:
            websocket: WebSocket 连接
            path: 连接路径
        """
        client_id = generate_id()
        self.clients[websocket] = {
            "id": client_id,
            "user_id": None,
            "room_id": None,
            "last_heartbeat": get_timestamp()
        }
        
        logger.info(f"Client {client_id} connected")
        
        try:
            async for message in websocket:
                try:
                    await self.process_message(websocket, message)
                except Exception as e:
                    logger.error(f"Error processing message from {client_id}: {e}")
                    error_msg = create_message(MessageType.ERROR, {"error": str(e)})
                    await websocket.send(error_msg)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        finally:
            await self.cleanup_client(websocket)
    
    async def cleanup_client(self, websocket: WebSocketServerProtocol) -> None:
        """清理断开的客户端"""
        if websocket in self.clients:
            client_info = self.clients[websocket]
            user_id = client_info.get("user_id")
            room_id = client_info.get("room_id")
            
            # 从用户连接映射中删除
            if user_id and user_id in self.user_connections:
                del self.user_connections[user_id]
                if user_id in self.user_last_heartbeat:
                    del self.user_last_heartbeat[user_id]
            
            # 从房间中删除用户
            if room_id and room_id in self.room_users:
                if user_id:
                    self.room_users[room_id].discard(user_id)
            
            del self.clients[websocket]
    
    async def process_message(self, websocket: WebSocketServerProtocol, message_str: str) -> None:
        """处理接收到的消息"""
        try:
            message = parse_message(message_str)
            message_type = MessageType[message["type"]]
            data = message["data"]
            
            # 更新心跳
            if websocket in self.clients:
                self.clients[websocket]["last_heartbeat"] = get_timestamp()
            
            # 路由消息
            if message_type == MessageType.REGISTER:
                await self.handle_register(websocket, data)
            elif message_type == MessageType.LOGIN:
                await self.handle_login(websocket, data)
            elif message_type == MessageType.LOGOUT:
                await self.handle_logout(websocket, data)
            elif message_type == MessageType.HEARTBEAT:
                await self.handle_heartbeat(websocket, data)
            elif message_type == MessageType.ROOM_LIST:
                await self.handle_room_list(websocket, data)
            elif message_type == MessageType.CREATE_ROOM:
                await self.handle_create_room(websocket, data)
            elif message_type == MessageType.JOIN_ROOM:
                await self.handle_join_room(websocket, data)
            elif message_type == MessageType.LEAVE_ROOM:
                await self.handle_leave_room(websocket, data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_msg = create_message(MessageType.ERROR, {"error": str(e)})
            await websocket.send(error_msg)
    
    # ==================== Auth Handlers ====================
    
    async def handle_register(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理注册请求"""
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing username or password"}))
            return
        
        user_id = await self.db.register_user(username, password)
        if user_id:
            # 自动登录
            token = generate_id()
            await self.db.create_session(user_id, token)
            
            if websocket in self.clients:
                self.clients[websocket]["user_id"] = user_id
            self.user_connections[user_id] = websocket
            self.user_last_heartbeat[user_id] = get_timestamp()
            
            response = create_message(MessageType.SUCCESS, {
                "user_id": user_id,
                "username": username,
                "token": token
            })
            await websocket.send(response)
            logger.info(f"User {username} registered and logged in")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Username already exists or registration failed"}))
    
    async def handle_login(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理登录请求"""
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing username or password"}))
            return
        
        user_info = await self.db.verify_user(username, password)
        if user_info:
            user_id = user_info["id"]
            token = generate_id()
            await self.db.create_session(user_id, token)
            
            if websocket in self.clients:
                self.clients[websocket]["user_id"] = user_id
            self.user_connections[user_id] = websocket
            self.user_last_heartbeat[user_id] = get_timestamp()
            
            response = create_message(MessageType.SUCCESS, {
                "user_id": user_id,
                "username": username,
                "token": token
            })
            await websocket.send(response)
            logger.info(f"User {username} logged in")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Invalid username or password"}))
    
    async def handle_logout(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理登出请求"""
        token = data.get("token")
        if token:
            await self.db.delete_session(token)
        
        if websocket in self.clients:
            user_id = self.clients[websocket].get("user_id")
            if user_id and user_id in self.user_connections:
                del self.user_connections[user_id]
                if user_id in self.user_last_heartbeat:
                    del self.user_last_heartbeat[user_id]
            self.clients[websocket]["user_id"] = None
        
        response = create_message(MessageType.SUCCESS, {"message": "Logged out successfully"})
        await websocket.send(response)
        logger.info(f"User logged out")
    
    async def handle_heartbeat(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理心跳"""
        if websocket in self.clients:
            user_id = self.clients[websocket].get("user_id")
            if user_id:
                self.user_last_heartbeat[user_id] = get_timestamp()
        
        response = create_message(MessageType.HEARTBEAT, {"timestamp": get_timestamp()})
        await websocket.send(response)
    
    # ==================== Room Handlers ====================
    
    async def handle_room_list(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理房间列表请求"""
        rooms = await self.db.list_rooms()
        
        # 获取每个房间的用户数
        room_list = []
        for room in rooms:
            room_id = room["id"]
            user_count = len(self.room_users.get(room_id, set()))
            robots = await self.db.list_room_robots(room_id)
            
            room_list.append({
                "id": room_id,
                "name": room["name"],
                "step_mode": room["step_mode"],
                "status": room["status"],
                "user_count": user_count,
                "robot_count": len(robots)
            })
        
        response = create_message(MessageType.ROOM_LIST, {"rooms": room_list})
        await websocket.send(response)
    
    async def handle_create_room(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理创建房间请求"""
        name = data.get("name")
        step_mode = data.get("step_mode")
        initial_capital = data.get("initial_capital", 100000)
        
        if not name or not step_mode:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room name or step mode"}))
            return
        
        room_id = await self.db.create_room(name, step_mode, initial_capital)
        if room_id:
            self.room_users[room_id] = set()
            response = create_message(MessageType.SUCCESS, {"room_id": room_id})
            await websocket.send(response)
            logger.info(f"Room {room_id} created")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to create room"}))
    
    async def handle_join_room(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理加入房间请求"""
        room_id = data.get("room_id")
        
        if not room_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id"}))
            return
        
        room = await self.db.get_room(room_id)
        if not room:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Room not found"}))
            return
        
        if websocket in self.clients:
            user_id = self.clients[websocket].get("user_id")
            if not user_id:
                await websocket.send(create_message(MessageType.ERROR, {"error": "Not authenticated"}))
                return
            
            # 添加用户到房间
            success = await self.db.add_user_to_room(room_id, user_id, room["initial_capital"])
            if success:
                self.clients[websocket]["room_id"] = room_id
                if room_id not in self.room_users:
                    self.room_users[room_id] = set()
                self.room_users[room_id].add(user_id)
                
                response = create_message(MessageType.SUCCESS, {
                    "room_id": room_id,
                    "message": "Joined room successfully"
                }, room_id)
                await websocket.send(response)
                
                # 广播给房间内其他用户
                await self.broadcast_to_room(room_id, create_message(
                    MessageType.ROOM_UPDATE,
                    {"message": f"User {user_id} joined"},
                    room_id
                ), exclude_user=user_id)
                
                logger.info(f"User {user_id} joined room {room_id}")
            else:
                await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to join room"}))
    
    async def handle_leave_room(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理离开房间请求"""
        room_id = data.get("room_id")
        
        if websocket in self.clients:
            user_id = self.clients[websocket].get("user_id")
            
            if user_id and room_id:
                await self.db.remove_user_from_room(room_id, user_id)
                if room_id in self.room_users:
                    self.room_users[room_id].discard(user_id)
                
                self.clients[websocket]["room_id"] = None
                
                response = create_message(MessageType.SUCCESS, {
                    "message": "Left room successfully"
                })
                await websocket.send(response)
                
                # 广播给房间内其他用户
                await self.broadcast_to_room(room_id, create_message(
                    MessageType.ROOM_UPDATE,
                    {"message": f"User {user_id} left"},
                    room_id
                ))
                
                logger.info(f"User {user_id} left room {room_id}")
    
    # ==================== Helper Methods ====================
    
    async def broadcast_to_room(self, room_id: str, message: str, exclude_user: Optional[str] = None) -> None:
        """广播消息到房间内的所有用户"""
        if room_id not in self.room_users:
            return
        
        for user_id in self.room_users[room_id]:
            if exclude_user and user_id == exclude_user:
                continue
            
            if user_id in self.user_connections:
                websocket = self.user_connections[user_id]
                try:
                    await websocket.send(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
    
    async def heartbeat_monitor_task(self) -> None:
        """心跳监测任务，检测断线客户端"""
        while True:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                now = get_timestamp()
                
                # 检查心跳超时
                disconnected_users = []
                for user_id, last_heartbeat in self.user_last_heartbeat.items():
                    if now - last_heartbeat > CLIENT_HEARTBEAT_TIMEOUT:
                        disconnected_users.append(user_id)
                
                # 清理超时用户
                for user_id in disconnected_users:
                    if user_id in self.user_connections:
                        websocket = self.user_connections[user_id]
                        try:
                            await websocket.close()
                        except:
                            pass
                        await self.cleanup_client(websocket)
                        logger.warning(f"User {user_id} disconnected due to heartbeat timeout")
            
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")


async def main():
    """主入口"""
    server = StonkWebSocketServer()
    await server.initialize()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
