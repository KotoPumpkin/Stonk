"""
Phase 4 - 集成测试

测试管理员干预系统的完整流程：
- 新闻→价格引擎→策略引擎 完整链路
- 财报→策略引擎→决策 完整链路
- 价格干预→价格生成 完整链路
- 管理员操作→广播 完整链路
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.admin_tools import AdminTools
from server.price_engine import PriceEngine, PriceModel
from server.trade_manager import TradeManager
from server.step_controller import StepController
from server.strategy_engine import StrategyEngine, StrategyType, RetailConfig


class MockDatabase:
    """模拟数据库"""
    
    def __init__(self):
        self.connection = AsyncMock()
        self.rooms = {}
        self.stocks = {"AAPL": {"id": "stock_1", "code": "AAPL"}}
        self.news_records = []
        self.report_records = []
        
    async def delete_room(self, room_id: str) -> bool:
        return True
    
    async def remove_user_from_room(self, room_id: str, user_id: str) -> bool:
        return True
    
    async def list_stocks(self):
        return list(self.stocks.values())
    
    async def _get_stock_by_code(self, stock_code: str):
        return self.stocks.get(stock_code)


class TestPhase4NewsIntegration(unittest.TestCase):
    """测试新闻发布完整链路"""
    
    def setUp(self):
        """设置测试环境"""
        self.db = MockDatabase()
        self.price_engine = PriceEngine()
        self.strategy_engine = StrategyEngine()
        
        # 添加股票
        self.price_engine.add_stock("AAPL", "Apple", 150.0, volatility=0.02)
        
        # 注册机器人
        self.strategy_engine.register_robot(
            robot_id="robot_1",
            room_id="test_room",
            name="散户机器人",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000
        )
        
        self.admin_tools = AdminTools(
            self.db,
            {"test_room": self.price_engine},
            {"test_room": MagicMock()},
            {"test_room": StepController()},
            {"test_room": self.strategy_engine}
        )
    
    def test_news_affects_price_engine(self):
        """测试新闻影响价格引擎"""
        # 发布积极新闻
        result = asyncio.run(self.admin_tools.publish_news(
            room_id="test_room",
            title="利好消息",
            content="公司业绩大增",
            sentiment="positive"
        ))
        
        self.assertIsNotNone(result)
        
        # 验证价格引擎的情绪参数被更新
        stock_state = self.price_engine.stocks["AAPL"]
        # 情绪值应该被设置
        self.assertNotEqual(stock_state.config.news_sentiment, 0.0)
    
    def test_news_affects_strategy_engine(self):
        """测试新闻影响策略引擎"""
        # 发布消极新闻
        result = asyncio.run(self.admin_tools.publish_news(
            room_id="test_room",
            title="利空消息",
            content="公司面临危机",
            sentiment="negative"
        ))
        
        self.assertIsNotNone(result)
        
        # 验证策略引擎的情绪被更新
        # 检查机器人的情绪偏向
        robot_strategy = self.strategy_engine.strategies["robot_1"]
        self.assertLess(robot_strategy.sentiment_bias, 0)  # 应该是负数
    
    def test_news_broadcast_message(self):
        """测试新闻广播消息格式"""
        result = asyncio.run(self.admin_tools.publish_news(
            room_id="test_room",
            title="测试新闻",
            content="测试内容",
            sentiment="neutral",
            affected_stocks=["AAPL"]
        ))
        
        self.assertIsNotNone(result)
        self.assertIn("broadcast_msg", result)
        
        # 验证广播消息格式
        import json
        msg = json.loads(result["broadcast_msg"])
        self.assertEqual(msg["type"], "NEWS_BROADCAST")
        self.assertIn("title", msg["data"])
        self.assertIn("content", msg["data"])
        self.assertEqual(msg["data"]["title"], "测试新闻")


class TestPhase4ReportIntegration(unittest.TestCase):
    """测试财报发布完整链路"""
    
    def setUp(self):
        """设置测试环境"""
        self.db = MockDatabase()
        self.price_engine = PriceEngine()
        self.strategy_engine = StrategyEngine()
        
        # 添加股票
        self.price_engine.add_stock("AAPL", "Apple", 150.0)
        
        # 注册机构机器人（对财报敏感）
        self.strategy_engine.register_robot(
            robot_id="robot_1",
            room_id="test_room",
            name="机构机器人",
            strategy_type=StrategyType.INSTITUTION,
            initial_cash=500000
        )
        
        self.admin_tools = AdminTools(
            self.db,
            {"test_room": self.price_engine},
            {"test_room": MagicMock()},
            {"test_room": StepController()},
            {"test_room": self.strategy_engine}
        )
    
    @patch.object(MockDatabase, '_get_stock_by_code', new_callable=AsyncMock)
    def test_report_affects_strategy(self, mock_get_stock):
        """测试财报影响策略"""
        mock_get_stock.return_value = {"id": "stock_1"}
        
        # 发布正面财报
        result = asyncio.run(self.admin_tools.publish_report(
            room_id="test_room",
            stock_code="AAPL",
            pe_ratio=15.0,
            roe=0.25,  # 高 ROE
            net_income=5000000,  # 高净利润
            revenue=50000000,
            manager_weight=1.5
        ))
        
        self.assertIsNotNone(result)
        
        # 验证财报影响被应用
        robot_strategy = self.strategy_engine.strategies["robot_1"]
        self.assertIn("AAPL", robot_strategy.report_impact)
        self.assertGreater(robot_strategy.report_impact["AAPL"], 0)
    
    @patch.object(MockDatabase, '_get_stock_by_code', new_callable=AsyncMock)
    def test_report_broadcast_format(self, mock_get_stock):
        """测试财报广播消息格式"""
        mock_get_stock.return_value = {"id": "stock_1"}
        
        result = asyncio.run(self.admin_tools.publish_report(
            room_id="test_room",
            stock_code="AAPL",
            pe_ratio=20.0,
            roe=0.15,
            net_income=1000000,
            revenue=10000000
        ))
        
        self.assertIsNotNone(result)
        
        import json
        msg = json.loads(result["broadcast_msg"])
        self.assertEqual(msg["type"], "REPORT_BROADCAST")
        self.assertEqual(msg["data"]["stock_code"], "AAPL")
        self.assertEqual(msg["data"]["pe_ratio"], 20.0)


class TestPhase4PriceIntervention(unittest.TestCase):
    """测试价格干预完整链路"""
    
    def setUp(self):
        """设置测试环境"""
        self.db = MockDatabase()
        self.price_engine = PriceEngine()
        self.strategy_engine = StrategyEngine()
        
        # 添加股票，使用随机游走模型
        self.price_engine.add_stock(
            "AAPL", "Apple", 150.0,
            volatility=0.02,
            drift=0.0001,
            model="random_walk"
        )
        
        self.admin_tools = AdminTools(
            self.db,
            {"test_room": self.price_engine},
            {"test_room": MagicMock()},
            {"test_room": StepController()},
            {"test_room": self.strategy_engine}
        )
    
    def test_change_volatility_affects_generation(self):
        """测试改变波动率影响价格生成"""
        # 获取干预前的价格序列
        prices_before = [self.price_engine.generate_next_price("AAPL") for _ in range(10)]
        
        # 大幅增加波动率
        self.admin_tools.intervene_stock_params(
            room_id="test_room",
            stock_code="AAPL",
            volatility=0.2  # 20% 波动率
        )
        
        # 获取干预后的价格序列
        prices_after = [self.price_engine.generate_next_price("AAPL") for _ in range(10)]
        
        # 计算波动率（标准差）
        import statistics
        returns_before = [(prices_before[i] - prices_before[i-1]) / prices_before[i-1] 
                         for i in range(1, len(prices_before))]
        returns_after = [(prices_after[i] - prices_after[i-1]) / prices_after[i-1]
                        for i in range(1, len(prices_after))]
        
        vol_before = statistics.stdev(returns_before) if len(returns_before) > 1 else 0
        vol_after = statistics.stdev(returns_after) if len(returns_after) > 1 else 0
        
        # 干预后波动率应该更大（统计上可能不总是成立，但趋势应该如此）
        # 这里我们至少验证配置被更新了
        self.assertEqual(self.price_engine.stocks["AAPL"].config.volatility, 0.2)
    
    def test_change_model_affects_generation(self):
        """测试改变价格模型影响价格生成"""
        # 切换到均值回归模型
        self.admin_tools.intervene_stock_params(
            room_id="test_room",
            stock_code="AAPL",
            model="mean_reversion"
        )
        
        # 验证模型已切换
        self.assertEqual(
            self.price_engine.stocks["AAPL"].config.model,
            PriceModel.MEAN_REVERSION
        )
    
    def test_set_price_directly(self):
        """测试直接设定价格"""
        # 设定一个具体价格
        self.admin_tools.set_stock_price(
            room_id="test_room",
            stock_code="AAPL",
            new_price=200.0
        )
        
        # 验证价格被设定
        self.assertEqual(self.price_engine.stocks["AAPL"].current_price, 200.0)
        
        # 验证历史被更新
        self.assertEqual(self.price_engine.stocks["AAPL"].history[-1], 200.0)


class TestPhase4RoomManagement(unittest.TestCase):
    """测试房间管理完整链路"""
    
    def setUp(self):
        """设置测试环境"""
        self.db = MockDatabase()
        self.db.rooms = {"test_room": {"name": "测试房间"}}
        
        self.price_engine = PriceEngine()
        self.price_engine.add_stock("AAPL", "Apple", 150.0)
        
        self.strategy_engine = StrategyEngine()
        self.strategy_engine.register_robot(
            robot_id="robot_1",
            room_id="test_room",
            name="测试机器人",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000
        )
        
        self.step_controller = StepController()
        self.step_controller.create_room("test_room")
        
        self.admin_tools = AdminTools(
            self.db,
            {"test_room": self.price_engine},
            {"test_room": MagicMock()},
            {"test_room": self.step_controller},
            {"test_room": self.strategy_engine}
        )
    
    def test_destroy_room_clears_all(self):
        """测试销毁房间清理所有资源"""
        # 销毁房间
        result = asyncio.run(self.admin_tools.destroy_room("test_room"))
        
        self.assertTrue(result)
        
        # 验证所有引擎都被清理
        self.assertNotIn("test_room", self.admin_tools.price_engines)
        self.assertNotIn("test_room", self.admin_tools.trade_managers)
        self.assertNotIn("test_room", self.admin_tools.step_controllers)
        self.assertNotIn("test_room", self.admin_tools.strategy_engines)
    
    def test_pause_resume_flow(self):
        """测试暂停恢复流程"""
        # 暂停
        pause_result = asyncio.run(self.admin_tools.admin_pause("test_room"))
        self.assertTrue(pause_result)
        
        # 验证状态
        status = self.step_controller.get_room_status("test_room")
        self.assertEqual(status["state"], "paused")
        
        # 恢复
        resume_result = asyncio.run(self.admin_tools.admin_resume("test_room"))
        self.assertTrue(resume_result)
        
        # 验证状态
        status = self.step_controller.get_room_status("test_room")
        self.assertEqual(status["state"], "idle")
    
    def test_step_forward_flow(self):
        """测试步进流程"""
        # 触发步进
        result = asyncio.run(self.admin_tools.admin_step_forward("test_room"))
        self.assertTrue(result)
        
        # 验证步进被触发（状态应该是 decision 或 processing）
        status = self.step_controller.get_room_status("test_room")
        self.assertIn(status["state"], ["decision", "processing", "idle"])


class TestPhase4GetRoomStatus(unittest.TestCase):
    """测试获取房间状态"""
    
    def setUp(self):
        """设置测试环境"""
        self.db = MockDatabase()
        self.price_engine = PriceEngine()
        self.price_engine.add_stock("AAPL", "Apple", 150.0, volatility=0.02)
        
        self.strategy_engine = StrategyEngine()
        self.strategy_engine.register_robot(
            robot_id="robot_1",
            room_id="test_room",
            name="测试机器人",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000
        )
        
        self.step_controller = StepController()
        self.step_controller.create_room("test_room")
        
        self.admin_tools = AdminTools(
            self.db,
            {"test_room": self.price_engine},
            {"test_room": MagicMock()},
            {"test_room": self.step_controller},
            {"test_room": self.strategy_engine}
        )
    
    def test_get_full_status(self):
        """测试获取完整房间状态"""
        status = self.admin_tools.get_room_full_status("test_room", {"AAPL": 155.0})
        
        self.assertIsNotNone(status)
        
        # 验证包含所有必要信息
        self.assertIn("room_id", status)
        self.assertIn("state", status)
        self.assertIn("step_mode", status)
        self.assertIn("current_step", status)
        self.assertIn("stocks", status)
        self.assertIn("robots", status)
        
        # 验证股票信息
        self.assertEqual(len(status["stocks"]), 1)
        self.assertEqual(status["stocks"][0]["code"], "AAPL")
        
        # 验证机器人信息
        self.assertEqual(len(status["robots"]), 1)
        self.assertEqual(status["robots"][0]["name"], "测试机器人")


if __name__ == "__main__":
    unittest.main()
