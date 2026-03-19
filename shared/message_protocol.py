"""
Stonk - 消息协议定义模块

定义 WebSocket 消息类型和消息工厂函数。
"""

import json
import time
from typing import Dict, Any, Optional
from enum import Enum

# ==================== 消息类型枚举 ====================
class MessageType(Enum):
    """WebSocket 消息类型枚举"""
    
    # 认证相关
    REGISTER = "REGISTER"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    HEARTBEAT = "HEARTBEAT"
    
    # 房间相关
    CREATE_ROOM = "CREATE_ROOM"
    JOIN_ROOM = "JOIN_ROOM"
    LEAVE_ROOM = "LEAVE_ROOM"
    DESTROY_ROOM = "DESTROY_ROOM"
    ROOM_LIST = "ROOM_LIST"
    ROOM_UPDATE = "ROOM_UPDATE"
    
    # 交易相关
    PLACE_ORDER = "PLACE_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    MODIFY_ORDER = "MODIFY_ORDER"
    ORDER_UPDATE = "ORDER_UPDATE"
    PRICE_UPDATE = "PRICE_UPDATE"
    TRADE_EXECUTE = "TRADE_EXECUTE"
    ASSET_UPDATE = "ASSET_UPDATE"
    
    # 步进相关
    STEP_START = "STEP_START"
    STEP_FORWARD = "STEP_FORWARD"
    STEP_COMPLETE = "STEP_COMPLETE"
    STEP_BROADCAST = "STEP_BROADCAST"
    DECISION_START = "DECISION_START"
    USER_READY = "USER_READY"
    FAST_FORWARD_START = "FAST_FORWARD_START"
    FAST_FORWARD_STOP = "FAST_FORWARD_STOP"
    STEP_READY_UPDATE = "STEP_READY_UPDATE"   # 用户就绪状态广播
    
    # 数据更新
    TRADE_EXECUTED = "TRADE_EXECUTED"
    ACCOUNT_UPDATE = "ACCOUNT_UPDATE"
    
    # 管理员命令
    ADMIN_PUBLISH_NEWS = "ADMIN_PUBLISH_NEWS"
    ADMIN_PUBLISH_REPORT = "ADMIN_PUBLISH_REPORT"
    ADMIN_DESTROY_ROOM = "ADMIN_DESTROY_ROOM"
    ADMIN_KICK_USER = "ADMIN_KICK_USER"
    ADMIN_STEP_FORWARD = "ADMIN_STEP_FORWARD"
    ADMIN_FAST_FORWARD = "ADMIN_FAST_FORWARD"
    ADMIN_PAUSE = "ADMIN_PAUSE"
    ADMIN_RESUME = "ADMIN_RESUME"
    
    # 全局机器人池管理
    ADMIN_CREATE_ROBOT = "ADMIN_CREATE_ROBOT"
    ADMIN_UPDATE_ROBOT = "ADMIN_UPDATE_ROBOT"
    ADMIN_DELETE_ROBOT = "ADMIN_DELETE_ROBOT"
    ADMIN_LIST_ROBOTS = "ADMIN_LIST_ROBOTS"
    ADMIN_SET_ROBOT_STRATEGY = "ADMIN_SET_ROBOT_STRATEGY"
    
    # 房间机器人池管理
    ADMIN_ADD_ROBOT_TO_ROOM = "ADMIN_ADD_ROBOT_TO_ROOM"
    ADMIN_REMOVE_ROBOT_FROM_ROOM = "ADMIN_REMOVE_ROBOT_FROM_ROOM"
    ADMIN_LIST_ROOM_ROBOTS = "ADMIN_LIST_ROOM_ROBOTS"
    
    # 管理员股票管理
    ADMIN_CREATE_STOCK = "ADMIN_CREATE_STOCK"
    ADMIN_UPDATE_STOCK = "ADMIN_UPDATE_STOCK"
    ADMIN_DELETE_STOCK = "ADMIN_DELETE_STOCK"
    ADMIN_LIST_STOCKS = "ADMIN_LIST_STOCKS"
    ADMIN_ADD_STOCK_TO_ROOM = "ADMIN_ADD_STOCK_TO_ROOM"
    ADMIN_REMOVE_STOCK_FROM_ROOM = "ADMIN_REMOVE_STOCK_FROM_ROOM"
    ADMIN_LIST_ROOM_STOCKS = "ADMIN_LIST_ROOM_STOCKS"
    
    # 参与者管理
    ADMIN_LIST_ROOM_PARTICIPANTS = "ADMIN_LIST_ROOM_PARTICIPANTS"
    ROOM_PARTICIPANT_LIST = "ROOM_PARTICIPANT_LIST"
    
    # 操作日志
    OPERATION_LOG = "OPERATION_LOG"
    ADMIN_GET_OPERATION_LOG = "ADMIN_GET_OPERATION_LOG"
    
    # 数据列表响应
    STOCK_LIST = "STOCK_LIST"
    ROOM_STOCK_LIST = "ROOM_STOCK_LIST"
    ROBOT_LIST = "ROBOT_LIST"
    ROOM_ROBOT_LIST = "ROOM_ROBOT_LIST"
    
    # 广播相关
    NEWS_BROADCAST = "NEWS_BROADCAST"
    REPORT_BROADCAST = "REPORT_BROADCAST"
    
    # 通用相关
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


def create_message(
    message_type: MessageType,
    data: Dict[str, Any],
    room_id: Optional[str] = None,
    timestamp: Optional[float] = None
) -> str:
    """
    创建 WebSocket 消息 JSON 字符串。
    
    Args:
        message_type: 消息类型
        data: 消息数据字典
        room_id: 房间 ID（可选）
        timestamp: 时间戳（可选，默认为当前时间）
    
    Returns:
        JSON 字符串格式的消息
    """
    if timestamp is None:
        timestamp = time.time()
    
    message = {
        "type": message_type.value,
        "data": data,
        "timestamp": timestamp
    }
    
    if room_id is not None:
        message["room_id"] = room_id
    
    return json.dumps(message)


def parse_message(message_json: str) -> Dict[str, Any]:
    """
    解析 WebSocket 消息 JSON 字符串。
    
    Args:
        message_json: JSON 字符串格式的消息
    
    Returns:
        解析后的消息字典，包含 type、data、timestamp、room_id（可选）
    
    Raises:
        json.JSONDecodeError: JSON 解析失败
        ValueError: 消息格式不正确
    """
    try:
        message = json.loads(message_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    # 验证必需字段
    required_fields = ["type", "data", "timestamp"]
    for field in required_fields:
        if field not in message:
            raise ValueError(f"Missing required field: {field}")
    
    # 验证消息类型是否存在
    try:
        MessageType[message["type"]]
    except KeyError:
        raise ValueError(f"Unknown message type: {message['type']}")
    
    return message


def validate_message(message: Dict[str, Any]) -> bool:
    """
    验证消息是否符合协议规范。
    
    Args:
        message: 消息字典
    
    Returns:
        是否有效
    """
    required_fields = ["type", "data", "timestamp"]
    if not all(field in message for field in required_fields):
        return False
    
    if not isinstance(message["data"], dict):
        return False
    
    if not isinstance(message["timestamp"], (int, float)):
        return False
    
    try:
        MessageType[message["type"]]
    except KeyError:
        return False
    
    return True
