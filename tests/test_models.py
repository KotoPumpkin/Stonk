"""
Stonk - 数据模型单元测试

测试数据库操作和数据模型。
"""

import asyncio
import unittest
from server.models import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """数据库管理器测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.db = DatabaseManager(":memory:")
    
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        asyncio.run(cls.db.close())
    
    def setUp(self):
        """测试初始化"""
        asyncio.run(self.db.initialize())
    
    def test_register_user(self):
        """测试用户注册"""
        async def async_test():
            user_id = await self.db.register_user("testuser", "password123")
            self.assertIsNotNone(user_id)
            self.assertTrue(user_id.startswith("user_"))
        
        asyncio.run(async_test())
    
    def test_verify_user(self):
        """测试用户验证"""
        async def async_test():
            # 先注册
            await self.db.register_user("testuser2", "password123")
            
            # 验证正确密码
            user_info = await self.db.verify_user("testuser2", "password123")
            self.assertIsNotNone(user_info)
            self.assertEqual(user_info["username"], "testuser2")
            
            # 验证错误密码
            user_info = await self.db.verify_user("testuser2", "wrongpassword")
            self.assertIsNone(user_info)
            
            # 验证不存在的用户
            user_info = await self.db.verify_user("nonexistent", "password123")
            self.assertIsNone(user_info)
        
        asyncio.run(async_test())
    
    def test_create_room(self):
        """测试创建房间"""
        async def async_test():
            room_id = await self.db.create_room("Test Room", "day", 100000)
            self.assertIsNotNone(room_id)
            self.assertTrue(room_id.startswith("room_"))
            
            # 验证房间信息
            room = await self.db.get_room(room_id)
            self.assertIsNotNone(room)
            self.assertEqual(room["name"], "Test Room")
            self.assertEqual(room["step_mode"], "day")
            self.assertEqual(room["initial_capital"], 100000)
        
        asyncio.run(async_test())
    
    def test_list_rooms(self):
        """测试列出房间"""
        async def async_test():
            # 创建几个房间
            room_id1 = await self.db.create_room("Room 1", "day", 100000)
            room_id2 = await self.db.create_room("Room 2", "hour", 50000)
            
            # 列出房间
            rooms = await self.db.list_rooms()
            self.assertGreaterEqual(len(rooms), 2)
            
            # 检查房间内容
            room_names = [r["name"] for r in rooms]
            self.assertIn("Room 1", room_names)
            self.assertIn("Room 2", room_names)
        
        asyncio.run(async_test())
    
    def test_create_stock(self):
        """测试创建股票"""
        async def async_test():
            stock_id = await self.db.create_stock("600000", "浦发银行", 10.5, 1000000, "中国银行")
            self.assertIsNotNone(stock_id)
            
            # 验证股票信息
            stock = await self.db.get_stock(stock_id)
            self.assertIsNotNone(stock)
            self.assertEqual(stock["code"], "600000")
            self.assertEqual(stock["name"], "浦发银行")
            self.assertEqual(stock["initial_price"], 10.5)
        
        asyncio.run(async_test())
    
    def test_session_management(self):
        """测试会话管理"""
        async def async_test():
            # 创建用户
            user_id = await self.db.register_user("sessiontest", "password123")
            
            # 创建会话
            token = "test_token_12345"
            success = await self.db.create_session(user_id, token)
            self.assertTrue(success)
            
            # 验证会话
            verified_user_id = await self.db.verify_session(token)
            self.assertEqual(verified_user_id, user_id)
            
            # 删除会话
            success = await self.db.delete_session(token)
            self.assertTrue(success)
            
            # 验证已删除
            verified_user_id = await self.db.verify_session(token)
            self.assertIsNone(verified_user_id)
        
        asyncio.run(async_test())


if __name__ == "__main__":
    unittest.main()
