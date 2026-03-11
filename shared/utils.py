"""
Stonk - 工具函数模块

提供密码加密、ID生成等通用工具函数。
"""

import hashlib
import secrets
import uuid
import time
from typing import Tuple

# ==================== 密码相关函数 ====================

def generate_salt(length: int = 32) -> str:
    """
    生成随机 Salt。
    
    Args:
        length: Salt 长度（字节数）
    
    Returns:
        十六进制格式的 Salt 字符串
    """
    return secrets.token_hex(length)


def hash_password(password: str, salt: str) -> str:
    """
    使用 SHA-256 + Salt 加密密码。
    
    Args:
        password: 明文密码
        salt: Salt 字符串（十六进制格式）
    
    Returns:
        加密后的密码哈希值（十六进制格式）
    """
    salted_password = password + salt
    return hashlib.sha256(salted_password.encode()).hexdigest()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """
    验证密码是否正确。
    
    Args:
        password: 待验证的明文密码
        salt: 存储的 Salt
        password_hash: 存储的密码哈希值
    
    Returns:
        密码是否正确
    """
    computed_hash = hash_password(password, salt)
    return computed_hash == password_hash


def create_password_entry(password: str) -> Tuple[str, str]:
    """
    创建密码条目（Salt + Hash）。
    
    Args:
        password: 明文密码
    
    Returns:
        (salt, password_hash) 元组
    """
    salt = generate_salt()
    password_hash = hash_password(password, salt)
    return salt, password_hash


# ==================== ID 生成函数 ====================

def generate_id() -> str:
    """
    生成唯一 UUID（作为用户 ID、房间 ID、订单 ID 等）。
    
    Returns:
        UUID 字符串（不含连字符）
    """
    return uuid.uuid4().hex


def generate_user_id() -> str:
    """
    生成用户 ID。
    
    Returns:
        用户 ID 字符串
    """
    return f"user_{generate_id()[:12]}"


def generate_room_id() -> str:
    """
    生成房间 ID。
    
    Returns:
        房间 ID 字符串
    """
    return f"room_{generate_id()[:12]}"


def generate_robot_id() -> str:
    """
    生成机器人 ID。
    
    Returns:
        机器人 ID 字符串
    """
    return f"robot_{generate_id()[:12]}"


def generate_order_id() -> str:
    """
    生成订单 ID。
    
    Returns:
        订单 ID 字符串
    """
    return f"order_{generate_id()[:12]}"


# ==================== 时间戳函数 ====================

def get_timestamp() -> float:
    """
    获取当前 Unix 时间戳（秒）。
    
    Returns:
        当前时间戳
    """
    return time.time()


def timestamp_to_datetime_str(timestamp: float) -> str:
    """
    将 Unix 时间戳转换为可读的日期时间字符串。
    
    Args:
        timestamp: Unix 时间戳
    
    Returns:
        格式为 YYYY-MM-DD HH:MM:SS 的字符串
    """
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
