"""
Stonk - WebSocket 客户端模块

异步 WebSocket 客户端，用于与服务器通信。
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
import websockets
from websockets.client import WebSocketClientProtocol

from shared.message_protocol import MessageType, create_message, parse_message
from shared.utils import get_timestamp
from client.config import SERVER_ADDRESS, SERVER_PORT_NUM, RECONNECT_INTERVAL, RECONNECT_MAX_TRIES, HEARTBEAT_TIMEOUT

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket 客户端类"""
    
    def __init__(self):
        """初始化客户端"""
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected = False
        self.user_id: Optional[str] = None
        self.token: Optional[str] = None
        self.room_id: Optional[str] = None
        
        # 消息处理回调
        self.message_handlers: Dict[str, Callable] = {}
        
        # 事件
        self.connection_event = asyncio.Event()
        self.last_heartbeat = get_timestamp()
    
    async def connect(self, host: str = SERVER_ADDRESS, port: int = SERVER_PORT_NUM) -> bool:
        """
        连接到服务器。
        
        Args:
            host: 服务器地址
            port: 服务器端口
        
        Returns:
            连接是否成功
        """
        retry_count = 0
        
        while retry_count < RECONNECT_MAX_TRIES:
            try:
                logger.info(f"Connecting to ws://{host}:{port}...")
                self.websocket = await websockets.connect(f"ws://{host}:{port}")
                self.connected = True
                self.connection_event.set()
                logger.info("Connected to server")
                
                # 启动消息接收任务
                asyncio.create_task(self._receive_messages())
                asyncio.create_task(self._heartbeat_task())
                
                return True
            
            except Exception as e:
                retry_count += 1
                logger.warning(f"Connection failed (attempt {retry_count}/{RECONNECT_MAX_TRIES}): {e}")
                
                if retry_count < RECONNECT_MAX_TRIES:
                    await asyncio.sleep(RECONNECT_INTERVAL)
        
        logger.error("Failed to connect to server after multiple attempts")
        return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        self.connected = False
        self.connection_event.clear()
        logger.info("Disconnected from server")
    
    async def send_message(self, message_type: MessageType, data: Dict[str, Any], 
                          room_id: Optional[str] = None) -> bool:
        """
        发送消息。
        
        Args:
            message_type: 消息类型
            data: 消息数据
            room_id: 房间 ID（可选）
        
        Returns:
            发送是否成功
        """
        if not self.connected or not self.websocket:
            logger.error("Not connected to server")
            return False
        
        try:
            message = create_message(message_type, data, room_id)
            await self.websocket.send(message)
            return True
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.connected = False
            return False
    
    async def _receive_messages(self) -> None:
        """接收并处理来自服务器的消息"""
        try:
            async for message_str in self.websocket:
                try:
                    message = parse_message(message_str)
                    message_type = MessageType[message["type"]]
                    data = message["data"]
                    
                    # 更新心跳
                    self.last_heartbeat = get_timestamp()
                    
                    # 调用相应的处理器
                    handler_key = message_type.value
                    if handler_key in self.message_handlers:
                        callback = self.message_handlers[handler_key]
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            self.connected = False
    
    async def _heartbeat_task(self) -> None:
        """心跳保活任务"""
        while self.connected:
            try:
                await asyncio.sleep(HEARTBEAT_TIMEOUT / 2)  # 每半个超时时间发送一次心跳
                
                if self.connected:
                    await self.send_message(MessageType.HEARTBEAT, {})
            
            except Exception as e:
                logger.error(f"Error in heartbeat task: {e}")
    
    def register_message_handler(self, message_type, callback: Callable) -> None:
        """
        注册消息处理器。
        
        Args:
            message_type: 消息类型（MessageType 枚举或字符串均可）
            callback: 处理函数
        """
        if isinstance(message_type, MessageType):
            key = message_type.value
        else:
            key = str(message_type)
        self.message_handlers[key] = callback
    
    # ==================== Auth Methods ====================
    
    async def register(self, username: str, password: str) -> bool:
        """
        注册账户。
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            注册是否成功
        """
        success_event = asyncio.Event()
        result = {"success": False}
        
        def handle_response(data: Dict[str, Any]) -> None:
            result["success"] = True
            self.user_id = data.get("user_id")
            self.token = data.get("token")
            success_event.set()
        
        def handle_error(data: Dict[str, Any]) -> None:
            logger.error(f"Registration error: {data.get('error')}")
            success_event.set()
        
        # 临时注册处理器
        self.message_handlers["SUCCESS"] = handle_response
        self.message_handlers["ERROR"] = handle_error
        
        await self.send_message(MessageType.REGISTER, {"username": username, "password": password})
        
        # 等待响应
        try:
            await asyncio.wait_for(success_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Registration timeout")
        
        return result["success"]
    
    # ==================== Trading Methods ====================
    
    async def place_order(self, stock_code: str, side: str, quantity: int, price: float) -> Optional[str]:
        """
        下单。
        
        Args:
            stock_code: 股票代码
            side: 买卖方向 ("buy" or "sell")
            quantity: 数量
            price: 价格
        
        Returns:
            订单 ID
        """
        order_event = asyncio.Event()
        result = {"order_id": None}
        
        def handle_response(data: Dict[str, Any]) -> None:
            result["order_id"] = data.get("order_id")
            logger.info(f"Order placed: {result['order_id']}")
            order_event.set()
        
        def handle_error(data: Dict[str, Any]) -> None:
            logger.error(f"Place order error: {data.get('error')}")
            order_event.set()
        
        # 临时注册处理器
        self.message_handlers["SUCCESS"] = handle_response
        self.message_handlers["ERROR"] = handle_error
        
        await self.send_message(MessageType.PLACE_ORDER, {
            "stock_code": stock_code,
            "side": side,
            "quantity": quantity,
            "price": price
        })
        
        # 等待响应
        try:
            await asyncio.wait_for(order_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Place order timeout")
        
        return result["order_id"]
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        取消订单。
        
        Args:
            order_id: 订单 ID
        
        Returns:
            取消是否成功
        """
        cancel_event = asyncio.Event()
        result = {"success": False}
        
        def handle_response(data: Dict[str, Any]) -> None:
            result["success"] = True
            logger.info(f"Order cancelled: {order_id}")
            cancel_event.set()
        
        def handle_error(data: Dict[str, Any]) -> None:
            logger.error(f"Cancel order error: {data.get('error')}")
            cancel_event.set()
        
        # 临时注册处理器
        self.message_handlers["SUCCESS"] = handle_response
        self.message_handlers["ERROR"] = handle_error
        
        await self.send_message(MessageType.CANCEL_ORDER, {"order_id": order_id})
        
        # 等待响应
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Cancel order timeout")
        
        return result["success"]

    async def modify_order(self, order_id: str, new_quantity: Optional[int] = None,
                           new_price: Optional[float] = None) -> bool:
        """
        修改订单。

        Args:
            order_id: 订单 ID
            new_quantity: 新数量（None 表示不修改）
            new_price: 新价格（None 表示不修改）

        Returns:
            修改是否成功
        """
        modify_event = asyncio.Event()
        result = {"success": False}

        def handle_response(data: Dict[str, Any]) -> None:
            result["success"] = True
            logger.info(f"Order modified: {order_id}")
            modify_event.set()

        def handle_error(data: Dict[str, Any]) -> None:
            logger.error(f"Modify order error: {data.get('error')}")
            modify_event.set()

        # 临时注册处理器
        self.message_handlers["SUCCESS"] = handle_response
        self.message_handlers["ERROR"] = handle_error

        payload: Dict[str, Any] = {"order_id": order_id}
        if new_quantity is not None:
            payload["new_quantity"] = new_quantity
        if new_price is not None:
            payload["new_price"] = new_price

        await self.send_message(MessageType.MODIFY_ORDER, payload)

        # 等待响应
        try:
            await asyncio.wait_for(modify_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Modify order timeout")

        return result["success"]
    
    async def mark_ready(self) -> bool:
        """
        标记用户就绪（步进控制）。
        
        Returns:
            标记是否成功
        """
        await self.send_message(MessageType.USER_READY, {})
        return True

    async def login(self, username: str, password: str) -> bool:
        """
        登录。
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            登录是否成功
        """
        success_event = asyncio.Event()
        result = {"success": False}
        
        def handle_response(data: Dict[str, Any]) -> None:
            result["success"] = True
            self.user_id = data.get("user_id")
            self.token = data.get("token")
            logger.info(f"Logged in as {data.get('username')}")
            success_event.set()
        
        def handle_error(data: Dict[str, Any]) -> None:
            logger.error(f"Login error: {data.get('error')}")
            success_event.set()
        
        # 临时注册处理器
        self.message_handlers["SUCCESS"] = handle_response
        self.message_handlers["ERROR"] = handle_error
        
        await self.send_message(MessageType.LOGIN, {"username": username, "password": password})
        
        # 等待响应
        try:
            await asyncio.wait_for(success_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Login timeout")
        
        return result["success"]
    
    async def logout(self) -> bool:
        """
        登出。
        
        Returns:
            登出是否成功
        """
        await self.send_message(MessageType.LOGOUT, {"token": self.token})
        self.user_id = None
        self.token = None
        self.room_id = None
        return True
    
    # ==================== Room Methods ====================
    
    async def get_room_list(self) -> Optional[list]:
        """
        获取房间列表。
        
        Returns:
            房间列表
        """
        room_list_event = asyncio.Event()
        result = {"rooms": None}
        
        def handle_room_list(data: Dict[str, Any]) -> None:
            result["rooms"] = data.get("rooms", [])
            room_list_event.set()
        
        # 临时注册处理器
        self.message_handlers["ROOM_LIST"] = handle_room_list
        
        await self.send_message(MessageType.ROOM_LIST, {})
        
        # 等待响应
        try:
            await asyncio.wait_for(room_list_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Get room list timeout")
        
        return result["rooms"]
    
    async def create_room(self, name: str, step_mode: str, initial_capital: float = 100000) -> Optional[str]:
        """
        创建房间。
        
        Args:
            name: 房间名称
            step_mode: 步进模式
            initial_capital: 初始资金
        
        Returns:
            房间 ID
        """
        room_id_event = asyncio.Event()
        result = {"room_id": None}
        
        def handle_response(data: Dict[str, Any]) -> None:
            result["room_id"] = data.get("room_id")
            room_id_event.set()
        
        def handle_error(data: Dict[str, Any]) -> None:
            logger.error(f"Create room error: {data.get('error')}")
            room_id_event.set()
        
        # 临时注册处理器
        self.message_handlers["SUCCESS"] = handle_response
        self.message_handlers["ERROR"] = handle_error
        
        await self.send_message(MessageType.CREATE_ROOM, {
            "name": name,
            "step_mode": step_mode,
            "initial_capital": initial_capital
        })
        
        # 等待响应
        try:
            await asyncio.wait_for(room_id_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Create room timeout")
        
        return result["room_id"]
    
    async def join_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        """
        加入房间。
        
        Args:
            room_id: 房间 ID
        
        Returns:
            成功时返回包含 room_id、name、step_mode 的字典，失败返回 None
        """
        join_event = asyncio.Event()
        result = {"success": False, "room_id": None, "name": "", "step_mode": "day"}
        
        def handle_response(data: Dict[str, Any]) -> None:
            result["success"] = True
            result["room_id"] = data.get("room_id")
            result["name"] = data.get("name", "")
            result["step_mode"] = data.get("step_mode", "day")
            result["stocks"] = data.get("stocks", [])
            result["account"] = data.get("account", {})
            self.room_id = data.get("room_id")
            logger.info(f"Joined room {self.room_id}")
            join_event.set()
        
        def handle_error(data: Dict[str, Any]) -> None:
            logger.error(f"Join room error: {data.get('error')}")
            join_event.set()
        
        # 临时注册处理器
        self.message_handlers["SUCCESS"] = handle_response
        self.message_handlers["ERROR"] = handle_error
        
        await self.send_message(MessageType.JOIN_ROOM, {"room_id": room_id})
        
        # 等待响应
        try:
            await asyncio.wait_for(join_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Join room timeout")
        
        if result["success"]:
            return {
                "room_id": result["room_id"],
                "name": result["name"],
                "step_mode": result["step_mode"],
                "stocks": result["stocks"],
                "account": result["account"]
            }
        return None
    
    async def leave_room(self, room_id: str) -> bool:
        """
        离开房间。
        
        Args:
            room_id: 房间 ID
        
        Returns:
            离开是否成功
        """
        leave_event = asyncio.Event()
        result = {"success": False}
        
        def handle_response(data: Dict[str, Any]) -> None:
            result["success"] = True
            self.room_id = None
            logger.info("Left room")
            leave_event.set()
        
        def handle_error(data: Dict[str, Any]) -> None:
            logger.error(f"Leave room error: {data.get('error')}")
            leave_event.set()
        
        # 临时注册处理器
        self.message_handlers["SUCCESS"] = handle_response
        self.message_handlers["ERROR"] = handle_error
        
        await self.send_message(MessageType.LEAVE_ROOM, {"room_id": room_id})
        
        # 等待响应
        try:
            await asyncio.wait_for(leave_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Leave room timeout")
        
        return result["success"]
