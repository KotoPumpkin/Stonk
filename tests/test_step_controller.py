"""
Stonk - 步进控制器单元测试
"""

import unittest
import asyncio
from server.step_controller import (
    StepController, StepMode, RoomState,
    StepConfig, RoomContext
)


class TestStepController(unittest.TestCase):
    """步进控制器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.controller = StepController()
        self.room_id = "test_room"
        self.controller.create_room(self.room_id)
    
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.controller)
        self.assertEqual(len(self.controller.rooms), 1)
        
        room = self.controller.get_room(self.room_id)
        self.assertIsNotNone(room)
        self.assertEqual(room.room_id, self.room_id)
        self.assertEqual(room.step_config.mode, StepMode.DAY)
        self.assertEqual(room.current_step, 0)
        self.assertEqual(room.state, RoomState.IDLE)
    
    def test_create_room_with_config(self):
        """测试使用自定义配置创建房间"""
        config = StepConfig(mode=StepMode.HOUR, decision_timeout=60.0)
        room = self.controller.create_room("room2", step_config=config)
        
        self.assertEqual(room.step_config.mode, StepMode.HOUR)
        self.assertEqual(room.step_config.decision_timeout, 60.0)
    
    def test_delete_room(self):
        """测试删除房间"""
        self.assertTrue(self.controller.delete_room(self.room_id))
        self.assertIsNone(self.controller.get_room(self.room_id))
        
        # 删除不存在的房间
        self.assertFalse(self.controller.delete_room("invalid"))
    
    def test_add_participant(self):
        """测试添加参与者"""
        self.assertTrue(self.controller.add_participant(self.room_id, "user1"))
        
        room = self.controller.get_room(self.room_id)
        self.assertIn("user1", room.participants)
        
        # 添加到不存在的房间
        self.assertFalse(self.controller.add_participant("invalid", "user1"))
    
    def test_remove_participant(self):
        """测试移除参与者"""
        self.controller.add_participant(self.room_id, "user1")
        self.controller.add_participant(self.room_id, "user2")
        
        self.assertTrue(self.controller.remove_participant(self.room_id, "user1"))
        
        room = self.controller.get_room(self.room_id)
        self.assertNotIn("user1", room.participants)
        self.assertIn("user2", room.participants)
        
        # 移除不存在的参与者（不报错）
        self.assertTrue(self.controller.remove_participant(self.room_id, "invalid"))
    
    def test_is_all_ready(self):
        """测试检查是否全部准备就绪"""
        self.controller.add_participant(self.room_id, "user1")
        self.controller.add_participant(self.room_id, "user2")
        
        room = self.controller.get_room(self.room_id)
        
        # 初始时不是全部就绪
        self.assertFalse(room.is_all_ready())
        
        # 标记第一个用户就绪
        room.ready_users.add("user1")
        self.assertFalse(room.is_all_ready())
        
        # 标记第二个用户就绪
        room.ready_users.add("user2")
        self.assertTrue(room.is_all_ready())
    
    def test_reset_ready(self):
        """测试重置就绪状态"""
        self.controller.add_participant(self.room_id, "user1")
        self.controller.add_participant(self.room_id, "user2")
        
        room = self.controller.get_room(self.room_id)
        room.ready_users.add("user1")
        room.ready_users.add("user2")
        
        # 重置状态
        room.reset_ready()
        
        self.assertEqual(len(room.ready_users), 0)
        self.assertFalse(room.is_all_ready())
    
    def test_user_ready(self):
        """测试用户准备就绪（异步）"""
        self.controller.add_participant(self.room_id, "user1")
        self.controller.add_participant(self.room_id, "user2")
        
        # 先开始步进进入决策期
        room = self.controller.get_room(self.room_id)
        room.state = RoomState.DECISION
        
        # 标记 user1 准备就绪
        result = asyncio.run(self.controller.user_ready(self.room_id, "user1"))
        self.assertTrue(result)
        
        room = self.controller.get_room(self.room_id)
        self.assertIn("user1", room.ready_users)
    
    def test_user_ready_wrong_state(self):
        """测试非决策期标记准备就绪"""
        self.controller.add_participant(self.room_id, "user1")
        
        # 房间处于 IDLE 状态，不应该允许标记准备
        result = asyncio.run(self.controller.user_ready(self.room_id, "user1"))
        self.assertFalse(result)
    
    def test_start_step(self):
        """测试开始步进"""
        self.controller.add_participant(self.room_id, "user1")
        
        result = asyncio.run(self.controller.start_step(self.room_id))
        self.assertTrue(result)
        
        room = self.controller.get_room(self.room_id)
        # 房间应该进入决策期
        self.assertEqual(room.state, RoomState.DECISION)
    
    def test_start_step_no_participants(self):
        """测试无参与者时开始步进（直接处理）"""
        # 没有参与者，步进应该直接完成
        result = asyncio.run(self.controller.start_step(self.room_id))
        self.assertTrue(result)
        
        room = self.controller.get_room(self.room_id)
        # 无参与者时直接处理完成，回到 IDLE
        self.assertEqual(room.state, RoomState.IDLE)
        self.assertEqual(room.current_step, 1)
    
    def test_step_forward_day_mode(self):
        """测试天模式步进"""
        # 无参与者，步进直接完成
        result = asyncio.run(self.controller.start_step(self.room_id))
        self.assertTrue(result)
        
        room = self.controller.get_room(self.room_id)
        self.assertEqual(room.current_step, 1)
        # 天模式：虚拟时间应增加 86400 秒
        self.assertGreater(room.virtual_time, 0)
    
    def test_step_forward_hour_mode(self):
        """测试小时模式步进"""
        config = StepConfig(mode=StepMode.HOUR)
        self.controller.create_room("hour_room", step_config=config)
        
        result = asyncio.run(self.controller.start_step("hour_room"))
        self.assertTrue(result)
        
        room = self.controller.get_room("hour_room")
        self.assertEqual(room.current_step, 1)
    
    def test_step_forward_month_mode(self):
        """测试月模式步进"""
        config = StepConfig(mode=StepMode.MONTH)
        self.controller.create_room("month_room", step_config=config)
        
        result = asyncio.run(self.controller.start_step("month_room"))
        self.assertTrue(result)
        
        room = self.controller.get_room("month_room")
        self.assertEqual(room.current_step, 1)
    
    def test_all_ready_triggers_processing(self):
        """测试所有用户就绪后触发处理"""
        self.controller.add_participant(self.room_id, "user1")
        self.controller.add_participant(self.room_id, "user2")
        
        # 开始步进
        asyncio.run(self.controller.start_step(self.room_id))
        
        room = self.controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.DECISION)
        
        # user1 准备就绪
        asyncio.run(self.controller.user_ready(self.room_id, "user1"))
        room = self.controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.DECISION)  # 还没全部就绪
        
        # user2 准备就绪 -> 触发处理
        asyncio.run(self.controller.user_ready(self.room_id, "user2"))
        room = self.controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.IDLE)  # 处理完成回到 IDLE
        self.assertEqual(room.current_step, 1)
    
    def test_start_fast_forward(self):
        """测试启用快进"""
        result = asyncio.run(self.controller.start_fast_forward(self.room_id))
        self.assertTrue(result)
        
        room = self.controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.FAST_FORWARD)
    
    def test_stop_fast_forward(self):
        """测试停止快进"""
        # 先启动快进
        asyncio.run(self.controller.start_fast_forward(self.room_id))
        
        # 停止快进
        result = asyncio.run(self.controller.stop_fast_forward(self.room_id))
        self.assertTrue(result)
        
        room = self.controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.IDLE)
    
    def test_stop_fast_forward_wrong_state(self):
        """测试非快进状态停止快进"""
        result = asyncio.run(self.controller.stop_fast_forward(self.room_id))
        self.assertFalse(result)
    
    def test_pause_room(self):
        """测试暂停房间"""
        result = asyncio.run(self.controller.pause_room(self.room_id))
        self.assertTrue(result)
        
        room = self.controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.PAUSED)
    
    def test_resume_room(self):
        """测试恢复房间"""
        asyncio.run(self.controller.pause_room(self.room_id))
        
        result = asyncio.run(self.controller.resume_room(self.room_id))
        self.assertTrue(result)
        
        room = self.controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.IDLE)
    
    def test_resume_room_wrong_state(self):
        """测试非暂停状态恢复房间"""
        result = asyncio.run(self.controller.resume_room(self.room_id))
        self.assertFalse(result)
    
    def test_get_room_status(self):
        """测试获取房间状态"""
        self.controller.add_participant(self.room_id, "user1")
        self.controller.add_participant(self.room_id, "user2")
        
        status = self.controller.get_room_status(self.room_id)
        
        self.assertIsNotNone(status)
        self.assertIn("room_id", status)
        self.assertIn("state", status)
        self.assertIn("step_mode", status)
        self.assertIn("current_step", status)
        self.assertIn("virtual_time", status)
        self.assertIn("participants_count", status)
        self.assertIn("ready_count", status)
        self.assertIn("is_all_ready", status)
        
        self.assertEqual(status["room_id"], self.room_id)
        self.assertEqual(status["state"], "idle")
        self.assertEqual(status["step_mode"], "day")
        self.assertEqual(status["participants_count"], 2)
        self.assertEqual(status["ready_count"], 0)
        self.assertFalse(status["is_all_ready"])
    
    def test_get_room_status_invalid(self):
        """测试获取不存在房间的状态"""
        status = self.controller.get_room_status("invalid")
        self.assertIsNone(status)
    
    def test_get_all_rooms_status(self):
        """测试获取所有房间状态"""
        self.controller.create_room("room2")
        
        statuses = self.controller.get_all_rooms_status()
        self.assertEqual(len(statuses), 2)
    
    def test_start_step_wrong_state(self):
        """测试非空闲状态开始步进"""
        self.controller.add_participant(self.room_id, "user1")
        
        # 开始步进（进入决策期）
        asyncio.run(self.controller.start_step(self.room_id))
        
        # 再次开始步进应该失败
        result = asyncio.run(self.controller.start_step(self.room_id))
        self.assertFalse(result)
    
    def test_remove_participant_clears_ready(self):
        """测试移除参与者同时清除就绪状态"""
        self.controller.add_participant(self.room_id, "user1")
        self.controller.add_participant(self.room_id, "user2")
        
        room = self.controller.get_room(self.room_id)
        room.state = RoomState.DECISION
        
        # 只标记 user1 就绪（user2 未就绪，不会触发处理）
        asyncio.run(self.controller.user_ready(self.room_id, "user1"))
        self.assertIn("user1", room.ready_users)
        
        # 移除参与者应同时清除就绪状态
        self.controller.remove_participant(self.room_id, "user1")
        self.assertNotIn("user1", room.ready_users)
        self.assertNotIn("user1", room.participants)
    
    def test_virtual_time_calculation(self):
        """测试虚拟时间计算"""
        from datetime import datetime
        base_time = datetime(2024, 1, 1).timestamp()
        
        # 天模式
        asyncio.run(self.controller.start_step(self.room_id))
        room = self.controller.get_room(self.room_id)
        expected_time = base_time + 1 * 86400
        self.assertAlmostEqual(room.virtual_time, expected_time, places=0)
        
        # 再步进一次
        asyncio.run(self.controller.start_step(self.room_id))
        room = self.controller.get_room(self.room_id)
        expected_time = base_time + 2 * 86400
        self.assertAlmostEqual(room.virtual_time, expected_time, places=0)


if __name__ == '__main__':
    unittest.main()
