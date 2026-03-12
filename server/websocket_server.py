"""
Stonk - WebSocket 服务器主程序

实现异步 WebSocket 服务器，处理客户端连接、消息分发、房间管理等。
"""

import sys
import os

# 确保项目根目录在 sys.path 中，支持直接运行此文件
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, List
import time
import websockets
# websockets 14+ 使用 ServerConnection 替代已废弃的 WebSocketServerProtocol
try:
    from websockets.server import ServerConnection as WebSocketServerProtocol
except ImportError:
    from websockets.legacy.server import WebSocketServerProtocol

from shared.message_protocol import MessageType, create_message, parse_message
from shared.utils import generate_id, get_timestamp
from shared.constants import SERVER_HEARTBEAT_INTERVAL
from server.models import DatabaseManager
from server.config import HOST, PORT, HEARTBEAT_INTERVAL, CLIENT_HEARTBEAT_TIMEOUT
from server.price_engine import PriceEngine
from server.trade_manager import TradeManager, OrderSide
from server.step_controller import StepController, StepConfig, StepMode
from server.strategy_engine import StrategyEngine, StrategyType
from server.admin_tools import AdminTools

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
        
        # 房间引擎管理
        self.price_engines: Dict[str, PriceEngine] = {}  # 房间 ID -> 价格引擎
        self.trade_managers: Dict[str, TradeManager] = {}  # 房间 ID -> 交易管理器
        self.step_controllers: Dict[str, StepController] = {}  # 房间 ID -> 步进控制器
        self.strategy_engines: Dict[str, StrategyEngine] = {}  # 房间 ID -> 策略引擎
        
        # 管理员工具
        self.admin_tools: Optional[AdminTools] = None
        
    async def initialize(self) -> None:
        """初始化服务器"""
        await self.db.initialize()
        
        # 预加载所有股票到价格引擎
        stocks = await self.db.list_stocks()
        self.default_stocks = [stock["code"] for stock in stocks]
        
        # 初始化管理员工具（在房间引擎创建后）
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
    
    async def handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """
        处理客户端连接。
        
        Args:
            websocket: WebSocket 连接
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
            elif message_type == MessageType.PLACE_ORDER:
                await self.handle_place_order(websocket, data)
            elif message_type == MessageType.CANCEL_ORDER:
                await self.handle_cancel_order(websocket, data)
            elif message_type == MessageType.USER_READY:
                await self.handle_user_ready(websocket, data)
            elif message_type == MessageType.STEP_FORWARD:
                await self.handle_step_forward(websocket, data)
            # 管理员命令
            elif message_type == MessageType.ADMIN_PUBLISH_NEWS:
                await self.handle_admin_publish_news(websocket, data)
            elif message_type == MessageType.ADMIN_PUBLISH_REPORT:
                await self.handle_admin_publish_report(websocket, data)
            elif message_type == MessageType.ADMIN_STOCK_INTERVENTION:
                await self.handle_admin_stock_intervention(websocket, data)
            elif message_type == MessageType.ADMIN_DESTROY_ROOM:
                await self.handle_admin_destroy_room(websocket, data)
            elif message_type == MessageType.ADMIN_STEP_FORWARD:
                await self.handle_admin_step_forward(websocket, data)
            elif message_type == MessageType.ADMIN_FAST_FORWARD:
                await self.handle_admin_fast_forward(websocket, data)
            elif message_type == MessageType.ADMIN_PAUSE:
                await self.handle_admin_pause(websocket, data)
            elif message_type == MessageType.ADMIN_RESUME:
                await self.handle_admin_resume(websocket, data)
            # 股票管理命令
            elif message_type == MessageType.ADMIN_CREATE_STOCK:
                await self.handle_admin_create_stock(websocket, data)
            elif message_type == MessageType.ADMIN_UPDATE_STOCK:
                await self.handle_admin_update_stock(websocket, data)
            elif message_type == MessageType.ADMIN_DELETE_STOCK:
                await self.handle_admin_delete_stock(websocket, data)
            elif message_type == MessageType.ADMIN_LIST_STOCKS:
                await self.handle_admin_list_stocks(websocket, data)
            elif message_type == MessageType.ADMIN_ADD_STOCK_TO_ROOM:
                await self.handle_admin_add_stock_to_room(websocket, data)
            elif message_type == MessageType.ADMIN_REMOVE_STOCK_FROM_ROOM:
                await self.handle_admin_remove_stock_from_room(websocket, data)
            elif message_type == MessageType.ADMIN_LIST_ROOM_STOCKS:
                await self.handle_admin_list_room_stocks(websocket, data)
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
        stocks = data.get("stocks", [])  # 股票池
        
        if not name or not step_mode:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room name or step mode"}))
            return
        
        room_id = await self.db.create_room(name, step_mode, initial_capital)
        if room_id:
            self.room_users[room_id] = set()
            
            # 初始化房间引擎
            await self._initialize_room_engines(room_id, stocks)
            
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
                    "name": room["name"],
                    "step_mode": room["step_mode"],
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
    
    # ==================== Trading Handlers ====================
    
    async def handle_place_order(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理下单请求"""
        if websocket not in self.clients:
            return
        
        user_id = self.clients[websocket].get("user_id")
        room_id = self.clients[websocket].get("room_id")
        
        if not user_id or not room_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Not in a room"}))
            return
        
        stock_code = data.get("stock_code")
        side = data.get("side")  # "buy" or "sell"
        quantity = data.get("quantity")
        price = data.get("price")
        
        if not all([stock_code, side, quantity, price]):
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing order parameters"}))
            return
        
        # 获取交易管理器
        trade_manager = self.trade_managers.get(room_id)
        if not trade_manager:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Room not initialized"}))
            return
        
        # 下单（同步方法，转换 side 为 OrderSide 枚举）
        try:
            order_side = OrderSide(side)
        except ValueError:
            await websocket.send(create_message(MessageType.ERROR, {"error": f"Invalid side: {side}"}))
            return
        
        order = trade_manager.place_order(user_id, stock_code, order_side, int(quantity), float(price))
        if order:
            response = create_message(MessageType.SUCCESS, {
                "message": "Order placed successfully",
                "order_id": order.id
            }, room_id)
            await websocket.send(response)
            logger.info(f"User {user_id} placed order {order.id} in room {room_id}")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to place order"}))
    
    async def handle_cancel_order(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理取消订单请求"""
        if websocket not in self.clients:
            return
        
        user_id = self.clients[websocket].get("user_id")
        room_id = self.clients[websocket].get("room_id")
        order_id = data.get("order_id")
        
        if not user_id or not room_id or not order_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Invalid request"}))
            return
        
        trade_manager = self.trade_managers.get(room_id)
        if not trade_manager:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Room not initialized"}))
            return
        
        success = trade_manager.cancel_order(order_id)
        if success:
            response = create_message(MessageType.SUCCESS, {"message": "Order cancelled"}, room_id)
            await websocket.send(response)
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to cancel order"}))
    
    async def handle_user_ready(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理用户就绪信号"""
        if websocket not in self.clients:
            return
        
        user_id = self.clients[websocket].get("user_id")
        room_id = self.clients[websocket].get("room_id")
        
        if not user_id or not room_id:
            return
        
        step_controller = self.step_controllers.get(room_id)
        if not step_controller:
            return
        
        # 标记用户就绪（使用正确的 API）
        await step_controller.user_ready(room_id, user_id)
    
    async def handle_step_forward(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理步进请求（管理员）"""
        room_id = data.get("room_id")
        
        if not room_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id"}))
            return
        
        step_controller = self.step_controllers.get(room_id)
        if not step_controller:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Room not initialized"}))
            return
        
        # 触发步进（使用正确的 API）
        await step_controller.start_step(room_id)
        
        # 广播进入决策期
        await self.broadcast_to_room(room_id, create_message(
            MessageType.DECISION_START,
            {"message": "Decision period started"},
            room_id
        ))
    
    # ==================== Admin Handlers ====================
    
    async def _ensure_admin_tools(self):
        """确保管理员工具已初始化"""
        if self.admin_tools is None:
            self.admin_tools = AdminTools(
                db=self.db,
                price_engines=self.price_engines,
                trade_managers=self.trade_managers,
                step_controllers=self.step_controllers,
                strategy_engines=self.strategy_engines
            )
    
    async def handle_admin_publish_news(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理发布新闻请求"""
        room_id = data.get("room_id")
        title = data.get("title")
        content = data.get("content")
        sentiment = data.get("sentiment", "neutral")
        affected_stocks = data.get("affected_stocks")
        
        if not room_id or not title or not content:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing required fields"}))
            return
        
        await self._ensure_admin_tools()
        result = await self.admin_tools.publish_news(room_id, title, content, sentiment, affected_stocks)
        
        if result:
            # 广播新闻
            await self.broadcast_to_room(room_id, result["broadcast_msg"])
            
            response = create_message(MessageType.SUCCESS, {
                "message": "News published successfully",
                "news_id": result["news_id"]
            })
            await websocket.send(response)
            logger.info(f"News published in room {room_id}: {title}")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to publish news"}))
    
    async def handle_admin_publish_report(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理发布财报请求"""
        room_id = data.get("room_id")
        stock_code = data.get("stock_code")
        pe_ratio = data.get("pe_ratio")
        roe = data.get("roe")
        net_income = data.get("net_income")
        revenue = data.get("revenue")
        manager_weight = data.get("manager_weight", 1.0)
        
        if not room_id or not stock_code:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing required fields"}))
            return
        
        await self._ensure_admin_tools()
        result = await self.admin_tools.publish_report(
            room_id, stock_code, pe_ratio, roe, net_income, revenue, manager_weight
        )
        
        if result:
            # 广播财报
            await self.broadcast_to_room(room_id, result["broadcast_msg"])
            
            response = create_message(MessageType.SUCCESS, {
                "message": "Report published successfully",
                "report_id": result["report_id"]
            })
            await websocket.send(response)
            logger.info(f"Report published in room {room_id} for {stock_code}")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to publish report"}))
    
    async def handle_admin_stock_intervention(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理股票干预请求"""
        room_id = data.get("room_id")
        stock_code = data.get("stock_code")
        intervention_type = data.get("type")
        
        if not room_id or not stock_code:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing required fields"}))
            return
        
        await self._ensure_admin_tools()
        
        success = False
        if intervention_type == "params":
            volatility = data.get("volatility")
            drift = data.get("drift")
            model = data.get("model")
            success = self.admin_tools.intervene_stock_params(
                room_id, stock_code, volatility, drift, model
            )
        elif intervention_type == "price":
            price = data.get("price")
            if price is not None:
                success = self.admin_tools.set_stock_price(room_id, stock_code, price)
        
        if success:
            response = create_message(MessageType.SUCCESS, {"message": "Stock intervention successful"})
            await websocket.send(response)
            logger.info(f"Stock intervention in room {room_id} for {stock_code}")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to intervene stock"}))
    
    async def handle_admin_destroy_room(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理销毁房间请求"""
        room_id = data.get("room_id")
        
        if not room_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id"}))
            return
        
        await self._ensure_admin_tools()
        success = await self.admin_tools.destroy_room(room_id)
        
        if success:
            response = create_message(MessageType.SUCCESS, {"message": "Room destroyed successfully"})
            await websocket.send(response)
            logger.info(f"Room {room_id} destroyed")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to destroy room"}))
    
    async def handle_admin_step_forward(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理管理员步进请求"""
        room_id = data.get("room_id")
        
        if not room_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id"}))
            return
        
        await self._ensure_admin_tools()
        success = await self.admin_tools.admin_step_forward(room_id)
        
        if success:
            # 广播进入决策期
            await self.broadcast_to_room(room_id, create_message(
                MessageType.DECISION_START,
                {"message": "Admin triggered step"},
                room_id
            ))
            response = create_message(MessageType.SUCCESS, {"message": "Step triggered"})
            await websocket.send(response)
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to trigger step"}))
    
    async def handle_admin_fast_forward(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理管理员快进请求"""
        room_id = data.get("room_id")
        start = data.get("start", True)
        speed = data.get("speed", 1.0)
        
        if not room_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id"}))
            return
        
        await self._ensure_admin_tools()
        success = await self.admin_tools.admin_fast_forward(room_id, speed, start)
        
        if success:
            msg_type = MessageType.FAST_FORWARD_START if start else MessageType.FAST_FORWARD_STOP
            await self.broadcast_to_room(room_id, create_message(
                msg_type,
                {"speed": speed},
                room_id
            ))
            response = create_message(MessageType.SUCCESS, {"message": f"Fast forward {'started' if start else 'stopped'}"})
            await websocket.send(response)
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to toggle fast forward"}))
    
    async def handle_admin_pause(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理管理员暂停请求"""
        room_id = data.get("room_id")
        
        if not room_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id"}))
            return
        
        await self._ensure_admin_tools()
        success = await self.admin_tools.admin_pause(room_id)
        
        if success:
            response = create_message(MessageType.SUCCESS, {"message": "Room paused"})
            await websocket.send(response)
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to pause room"}))
    
    async def handle_admin_resume(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理管理员恢复请求"""
        room_id = data.get("room_id")
        
        if not room_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id"}))
            return
        
        await self._ensure_admin_tools()
        success = await self.admin_tools.admin_resume(room_id)
        
        if success:
            response = create_message(MessageType.SUCCESS, {"message": "Room resumed"})
            await websocket.send(response)
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to resume room"}))
    
    # ==================== Stock Management Handlers ====================
    
    async def handle_admin_create_stock(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理创建股票请求"""
        code = data.get("code")
        name = data.get("name")
        initial_price = data.get("initial_price", 100.0)
        issued_shares = data.get("issued_shares", 1000000)
        description = data.get("description", "")
        
        if not code or not name:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing code or name"}))
            return
        
        await self._ensure_admin_tools()
        result = await self.admin_tools.create_stock(code, name, initial_price, issued_shares, description)
        
        if result:
            response = create_message(MessageType.SUCCESS, {
                "message": "Stock created successfully",
                "stock": result
            })
            await websocket.send(response)
            logger.info(f"Stock {code} created")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to create stock"}))
    
    async def handle_admin_update_stock(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理更新股票请求"""
        stock_id = data.get("stock_id")
        
        if not stock_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing stock_id"}))
            return
        
        await self._ensure_admin_tools()
        success = await self.admin_tools.update_stock(
            stock_id,
            code=data.get("code"),
            name=data.get("name"),
            initial_price=data.get("initial_price"),
            issued_shares=data.get("issued_shares"),
            description=data.get("description")
        )
        
        if success:
            response = create_message(MessageType.SUCCESS, {"message": "Stock updated successfully"})
            await websocket.send(response)
            logger.info(f"Stock {stock_id} updated")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to update stock"}))
    
    async def handle_admin_delete_stock(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理删除股票请求"""
        stock_id = data.get("stock_id")
        
        if not stock_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing stock_id"}))
            return
        
        await self._ensure_admin_tools()
        success = await self.admin_tools.delete_stock(stock_id)
        
        if success:
            response = create_message(MessageType.SUCCESS, {"message": "Stock deleted successfully"})
            await websocket.send(response)
            logger.info(f"Stock {stock_id} deleted")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to delete stock"}))
    
    async def handle_admin_list_stocks(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理列出股票请求"""
        await self._ensure_admin_tools()
        stocks = await self.admin_tools.list_stocks()
        
        response = create_message(MessageType.STOCK_LIST, {"stocks": stocks})
        await websocket.send(response)
    
    async def handle_admin_add_stock_to_room(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理添加股票到房间请求"""
        room_id = data.get("room_id")
        stock_code = data.get("stock_code")
        current_price = data.get("current_price", 100.0)
        
        if not room_id or not stock_code:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id or stock_code"}))
            return
        
        await self._ensure_admin_tools()
        success = await self.admin_tools.add_stock_to_room(room_id, stock_code, current_price)
        
        if success:
            response = create_message(MessageType.SUCCESS, {"message": "Stock added to room successfully"})
            await websocket.send(response)
            logger.info(f"Stock {stock_code} added to room {room_id}")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to add stock to room"}))
    
    async def handle_admin_remove_stock_from_room(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理从房间移除股票请求"""
        room_id = data.get("room_id")
        stock_code = data.get("stock_code")
        
        if not room_id or not stock_code:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id or stock_code"}))
            return
        
        await self._ensure_admin_tools()
        success = await self.admin_tools.remove_stock_from_room(room_id, stock_code)
        
        if success:
            response = create_message(MessageType.SUCCESS, {"message": "Stock removed from room successfully"})
            await websocket.send(response)
            logger.info(f"Stock {stock_code} removed from room {room_id}")
        else:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Failed to remove stock from room"}))
    
    async def handle_admin_list_room_stocks(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """处理列出房间股票请求"""
        room_id = data.get("room_id")
        
        if not room_id:
            await websocket.send(create_message(MessageType.ERROR, {"error": "Missing room_id"}))
            return
        
        await self._ensure_admin_tools()
        stocks = await self.admin_tools.list_room_stocks(room_id)
        
        response = create_message(MessageType.ROOM_STOCK_LIST, {"stocks": stocks, "room_id": room_id})
        await websocket.send(response)
    
    # ==================== Room Engine Management ====================
    
    async def _initialize_room_engines(self, room_id: str, stocks: List[str]) -> None:
        """初始化房间引擎"""
        # 初始化价格引擎
        price_engine = PriceEngine()
        
        # 添加默认股票或指定股票
        stock_list = stocks if stocks else self.default_stocks
        if not stock_list:
            # 如果没有股票，添加一些默认股票
            stock_list = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
            
        for stock_code in stock_list:
            price_engine.add_stock(code=stock_code, name=stock_code, initial_price=100.0)
        self.price_engines[room_id] = price_engine
        
        # 初始化交易管理器（无参数）
        trade_manager = TradeManager()
        self.trade_managers[room_id] = trade_manager
        
        # 初始化步进控制器
        step_controller = StepController()
        room_info = await self.db.get_room(room_id)
        step_mode_str = room_info.get("step_mode", "day") if room_info else "day"
        # 将字符串模式转换为 StepConfig 对象
        try:
            step_mode = StepMode(step_mode_str)
        except ValueError:
            step_mode = StepMode.DAY
        step_config = StepConfig(mode=step_mode)
        step_controller.create_room(room_id, step_config)
        self.step_controllers[room_id] = step_controller
        
        logger.info(f"Engines initialized for room {room_id} with stocks: {stock_list}")
    
    async def _execute_step(self, room_id: str) -> None:
        """执行步进"""
        price_engine = self.price_engines.get(room_id)
        trade_manager = self.trade_managers.get(room_id)
        
        if not all([price_engine, trade_manager]):
            logger.error(f"Missing engines for room {room_id}")
            return
        
        try:
            # 1. 生成新价格（使用 batch_generate）
            new_prices = price_engine.batch_generate()
            
            # 2. 对每支股票分别撮合交易
            all_trades = []
            for stock_code, market_price in new_prices.items():
                trades = trade_manager.match_orders(stock_code, market_price)
                if trades:
                    all_trades.extend([{
                        "stock_code": t.stock_code,
                        "buyer_id": t.buyer_id,
                        "seller_id": t.seller_id,
                        "price": t.price,
                        "quantity": t.quantity
                    } for t in trades])
            
            # 3. 广播更新
            await self._broadcast_step_update(room_id, new_prices, all_trades)
            
            logger.info(f"Step executed for room {room_id}")
        
        except Exception as e:
            logger.error(f"Error executing step for room {room_id}: {e}")
    
    async def _broadcast_step_update(self, room_id: str, prices: Dict[str, float], trades: List[Dict]) -> None:
        """广播步进更新"""
        # 广播价格更新
        price_message = create_message(MessageType.PRICE_UPDATE, {
            "prices": prices,
            "timestamp": get_timestamp()
        }, room_id)
        await self.broadcast_to_room(room_id, price_message)
        
        # 广播交易记录
        if trades:
            trade_message = create_message(MessageType.TRADE_EXECUTED, {
                "trades": trades
            }, room_id)
            await self.broadcast_to_room(room_id, trade_message)
        
        # 更新每个用户的账户信息
        trade_manager = self.trade_managers.get(room_id)
        if trade_manager:
            for user_id in self.room_users.get(room_id, set()):
                # get_account_summary 需要 initial_capital 参数，从数据库获取
                room_info = await self.db.get_room(room_id)
                initial_capital = room_info.get("initial_capital", 100000.0) if room_info else 100000.0
                account = trade_manager.get_account_summary(user_id, prices, initial_capital)
                if account and user_id in self.user_connections:
                    websocket = self.user_connections[user_id]
                    account_message = create_message(MessageType.ACCOUNT_UPDATE, account, room_id)
                    try:
                        await websocket.send(account_message)
                    except Exception as e:
                        logger.error(f"Error sending account update to {user_id}: {e}")
    
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
