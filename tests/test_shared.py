"""
Stonk - 共享模块单元测试

测试工具函数、消息协议等共享模块。
"""

import unittest
import json
from shared.utils import (
    generate_salt, hash_password, verify_password, create_password_entry,
    generate_id, generate_user_id, generate_room_id, generate_robot_id,
    generate_order_id, get_timestamp, timestamp_to_datetime_str
)
from shared.message_protocol import MessageType, create_message, parse_message, validate_message


class TestUtils(unittest.TestCase):
    """工具函数测试"""
    
    def test_generate_salt(self):
        """测试盐生成"""
        salt1 = generate_salt()
        salt2 = generate_salt()
        
        # 验证盐长度和唯一性
        self.assertEqual(len(salt1), 64)  # 32 字节 = 64 个十六进制字符
        self.assertEqual(len(salt2), 64)
        self.assertNotEqual(salt1, salt2)
    
    def test_password_hashing(self):
        """测试密码哈希"""
        password = "mypassword123"
        salt = generate_salt()
        
        # 哈希密码
        hash1 = hash_password(password, salt)
        hash2 = hash_password(password, salt)
        
        # 相同密码和盐应该产生相同哈希
        self.assertEqual(hash1, hash2)
        
        # 不同盐应该产生不同哈希
        salt2 = generate_salt()
        hash3 = hash_password(password, salt2)
        self.assertNotEqual(hash1, hash3)
    
    def test_verify_password(self):
        """测试密码验证"""
        password = "mypassword123"
        salt = generate_salt()
        password_hash = hash_password(password, salt)
        
        # 验证正确密码
        self.assertTrue(verify_password(password, salt, password_hash))
        
        # 验证错误密码
        self.assertFalse(verify_password("wrongpassword", salt, password_hash))
    
    def test_create_password_entry(self):
        """测试创建密码条目"""
        password = "mypassword123"
        salt, password_hash = create_password_entry(password)
        
        # 验证
        self.assertTrue(verify_password(password, salt, password_hash))
        self.assertFalse(verify_password("wrongpassword", salt, password_hash))
    
    def test_generate_id(self):
        """测试 ID 生成"""
        id1 = generate_id()
        id2 = generate_id()
        
        # 验证格式和唯一性
        self.assertEqual(len(id1), 32)  # UUID hex = 32 字符
        self.assertEqual(len(id2), 32)
        self.assertNotEqual(id1, id2)
    
    def test_generate_user_id(self):
        """测试用户 ID 生成"""
        user_id = generate_user_id()
        self.assertTrue(user_id.startswith("user_"))
    
    def test_generate_room_id(self):
        """测试房间 ID 生成"""
        room_id = generate_room_id()
        self.assertTrue(room_id.startswith("room_"))
    
    def test_generate_robot_id(self):
        """测试机器人 ID 生成"""
        robot_id = generate_robot_id()
        self.assertTrue(robot_id.startswith("robot_"))
    
    def test_generate_order_id(self):
        """测试订单 ID 生成"""
        order_id = generate_order_id()
        self.assertTrue(order_id.startswith("order_"))
    
    def test_get_timestamp(self):
        """测试时间戳获取"""
        ts1 = get_timestamp()
        ts2 = get_timestamp()
        
        # 验证时间戳是浮点数且递增
        self.assertIsInstance(ts1, float)
        self.assertIsInstance(ts2, float)
        self.assertLessEqual(ts1, ts2)
    
    def test_timestamp_to_datetime_str(self):
        """测试时间戳转换"""
        ts = 1609459200.0  # 2021-01-01 00:00:00
        dt_str = timestamp_to_datetime_str(ts)
        
        # 验证格式
        self.assertIn("2021", dt_str)
        self.assertIn("01", dt_str)


class TestMessageProtocol(unittest.TestCase):
    """消息协议测试"""
    
    def test_create_message(self):
        """测试创建消息"""
        msg = create_message(MessageType.LOGIN, {"username": "test", "password": "pwd"})
        
        # 验证是有效的 JSON
        data = json.loads(msg)
        self.assertEqual(data["type"], "LOGIN")
        self.assertEqual(data["data"]["username"], "test")
        self.assertEqual(data["data"]["password"], "pwd")
        self.assertIn("timestamp", data)
    
    def test_create_message_with_room_id(self):
        """测试创建包含房间 ID 的消息"""
        msg = create_message(
            MessageType.PLACE_ORDER,
            {"stock": "600000", "quantity": 100},
            room_id="room_abc123"
        )
        
        data = json.loads(msg)
        self.assertEqual(data["room_id"], "room_abc123")
    
    def test_parse_message(self):
        """测试解析消息"""
        original_msg = create_message(
            MessageType.LOGIN,
            {"username": "test", "password": "pwd"}
        )
        
        parsed = parse_message(original_msg)
        self.assertEqual(parsed["type"], "LOGIN")
        self.assertEqual(parsed["data"]["username"], "test")
        self.assertIn("timestamp", parsed)
    
    def test_parse_invalid_message(self):
        """测试解析无效消息"""
        with self.assertRaises(ValueError):
            parse_message("invalid json")
    
    def test_parse_missing_fields(self):
        """测试解析缺少字段的消息"""
        invalid_msg = json.dumps({
            "type": "LOGIN"
            # 缺少 data 和 timestamp
        })
        
        with self.assertRaises(ValueError):
            parse_message(invalid_msg)
    
    def test_validate_message(self):
        """测试消息验证"""
        msg = create_message(MessageType.LOGIN, {"username": "test"})
        parsed = json.loads(msg)
        
        # 有效消息
        self.assertTrue(validate_message(parsed))
        
        # 缺少字段
        invalid_msg = {
            "type": "LOGIN",
            "data": {"username": "test"}
            # 缺少 timestamp
        }
        self.assertFalse(validate_message(invalid_msg))
        
        # 无效类型
        invalid_msg = {
            "type": "INVALID_TYPE",
            "data": {},
            "timestamp": 123456
        }
        self.assertFalse(validate_message(invalid_msg))
    
    def test_message_types(self):
        """测试所有消息类型"""
        # 验证所有消息类型都已定义
        self.assertTrue(hasattr(MessageType, "LOGIN"))
        self.assertTrue(hasattr(MessageType, "REGISTER"))
        self.assertTrue(hasattr(MessageType, "HEARTBEAT"))
        self.assertTrue(hasattr(MessageType, "ROOM_LIST"))
        self.assertTrue(hasattr(MessageType, "CREATE_ROOM"))
        self.assertTrue(hasattr(MessageType, "JOIN_ROOM"))
        self.assertTrue(hasattr(MessageType, "ERROR"))
        self.assertTrue(hasattr(MessageType, "SUCCESS"))


if __name__ == "__main__":
    unittest.main()
