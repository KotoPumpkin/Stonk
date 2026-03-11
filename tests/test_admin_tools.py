"""
Phase 4 - 管理员工具单元测试

测试 admin_tools.py 中的所有功能：
- 新闻发布系统
- 财报发布系统
- 价格/参数干预
- 房间管理
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.admin_tools import AdminTools
from server.price_engine import PriceEngine
from server.trade_manager import TradeManager
from server.step_controller import StepController, StepConfig, StepMode
from server.strategy_engine import StrategyEngine, StrategyType


class MockDatabase:
    """模拟数据库"""
    
    def __init__(self):
        self.connection = AsyncMock()
        self.rooms = {}
        self.stocks = {}
        self.news_records = []
        self.report_records = []
        
    async def _get_stock_by_code(self, stock_code: str):
        """根据股票代码获取股票信息"""
        return self.stocks.get(stock_code)
        
    async def delete_room(self, room_id: str) -> bool:
        if room_id in self.rooms:
            del self.rooms[room_id]
            return True
        return False
    
    async def remove_user_from_room(self, room_id: str, user_id: str) -> bool:
        return True
    
    async def list_stocks(self):
        return list(self.stocks.values())


class TestAdminToolsNews(unittest.TestCase):
    """测试新闻发布系统"""
    
    def setUp(self):
        """设置测试环境"""
        self.db = MockDatabase()
        self.price_engine = PriceEngine()
        self.trade_manager = MagicMock()
        self.step_controller = StepController()
        self.strategy_engine = StrategyEngine()
        
        # 初始化房间
        room_id = "test_room"
        self.price_engine.stocks["AAPL"] = MagicMock()
        self.price_engine.stocks["AAPL"].config = MagicMock()
        self.price_engine.stocks["AAPL"].config.news_sentiment = 0.0
        self.price_engine.stocks["AAPL"].config.news_impact = 0.1
        
        self.price_engines = {"test_room": self.price_engine}
        self.trade_managers = {"test_room": self.trade_manager}
        self.step_controllers = {"test_room": self.step_controller}
        self.strategy_engines = {"test_room": self.strategy_engine}
        
        self.admin_tools = AdminTools(
            self.db, self.price_engines, self.trade_managers,
            self.step_controllers, self.strategy_engines
        )
    
    def test_publish_news_positive(self):
        """测试发布积极新闻"""
        result = asyncio.run(self.admin_tools.publish_news(
            room_id="test_room",
            title="重大利好",
            content="公司业绩大幅增长",
            sentiment="positive"
        ))
        
        self.assertIsNotNone(result)
        self.assertIn("news_id", result)
        self.assertIn("broadcast_msg", result)
        self.assertEqual(result["sentiment_value"], 0.5)
    
    def test_publish_news_negative(self):
        """测试发布消极新闻"""
        result = asyncio.run(self.admin_tools.publish_news(
            room_id="test_room",
            title="重大利空",
            content="公司面临监管调查",
            sentiment="negative"
        ))
        
        self.assertIsNotNone(result)
        self.assertEqual(result["sentiment_value"], -0.5)
    
    def test_publish_news_neutral(self):
        """测试发布中立新闻"""
        result = asyncio.run(self.admin_tools.publish_news(
            room_id="test_room",
            title="日常公告",
            content="公司正常运营",
            sentiment="neutral"
        ))
        
        self.assertIsNotNone(result)
        self.assertEqual(result["sentiment_value"], 0.0)
    
    def test_publish_news_affected_stocks(self):
        """测试发布影响特定股票的新闻"""
        result = asyncio.run(self.admin_tools.publish_news(
            room_id="test_room",
            title="AAPL 产品发布",
            content="新款 iPhone 发布",
            sentiment="positive",
            affected_stocks=["AAPL"]
        ))
        
        self.assertIsNotNone(result)
    
    def test_publish_news_invalid_room(self):
        """测试无效房间 ID"""
        result = asyncio.run(self.admin_tools.publish_news(
            room_id="invalid_room",
            title="测试新闻",
            content="测试内容",
            sentiment="positive"
        ))
        
        self.assertIsNone(result)


class TestAdminToolsReport(unittest.TestCase):
    """测试财报发布系统"""
    
    def setUp(self):
        """设置测试环境"""
        self.db = MockDatabase()
        self.db.stocks = {"AAPL": {"id": "stock_1", "code": "AAPL"}}
        
        self.price_engine = PriceEngine()
        self.trade_manager = MagicMock()
        self.step_controller = StepController()
        self.strategy_engine = StrategyEngine()
        
        # 注册机器人
        self.strategy_engine.register_robot(
            robot_id="robot_1",
            room_id="test_room",
            name="测试机器人",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000
        )
        
        self.price_engines = {"test_room": self.price_engine}
        self.trade_managers = {"test_room": self.trade_manager}
        self.step_controllers = {"test_room": self.step_controller}
        self.strategy_engines = {"test_room": self.strategy_engine}
        
        self.admin_tools = AdminTools(
            self.db, self.price_engines, self.trade_managers,
            self.step_controllers, self.strategy_engines
        )
    
    @patch.object(MockDatabase, '_get_stock_by_code', new_callable=AsyncMock)
    def test_publish_report_basic(self, mock_get_stock):
        """测试发布基础财报"""
        mock_get_stock.return_value = {"id": "stock_1"}
        
        result = asyncio.run(self.admin_tools.publish_report(
            room_id="test_room",
            stock_code="AAPL",
            pe_ratio=20.0,
            roe=0.15,
            net_income=1000000,
            revenue=10000000,
            manager_weight=1.0
        ))
        
        self.assertIsNotNone(result)
        self.assertIn("report_id", result)
        self.assertIn("broadcast_msg", result)
    
    def test_publish_report_invalid_room(self):
        """测试无效房间"""
        result = asyncio.run(self.admin_tools.publish_report(
            room_id="invalid_room",
            stock_code="AAPL",
            pe_ratio=20.0
        ))
        
        self.assertIsNone(result)
    
    def test_check_report_due(self):
        """测试财报周期探测"""
        # 创建房间上下文
        self.step_controller.create_room("test_room")
        room_context = self.step_controller.get_room("test_room")
        room_context.current_step = 365
        
        result = asyncio.run(self.admin_tools.check_report_due("test_room"))
        self.assertTrue(result)
    
    def test_check_report_not_due(self):
        """测试未到财报发布周期"""
        self.step_controller.create_room("test_room")
        room_context = self.step_controller.get_room("test_room")
        room_context.current_step = 100
        
        result = asyncio.run(self.admin_tools.check_report_due("test_room"))
        self.assertFalse(result)


class TestAdminToolsIntervention(unittest.TestCase):
    """测试价格/参数干预"""
    
    def setUp(self):
        """设置测试环境"""
        self.db = MockDatabase()
        self.price_engine = PriceEngine()
        self.trade_manager = MagicMock()
        self.step_controller = StepController()
        self.strategy_engine = StrategyEngine()
        
        # 添加股票
        self.price_engine.add_stock("AAPL", "Apple", 150.0, volatility=0.02, drift=0.0001)
        
        self.price_engines = {"test_room": self.price_engine}
        self.trade_managers = {"test_room": self.trade_manager}
        self.step_controllers = {"test_room": self.step_controller}
        self.strategy_engines = {"test_room": self.strategy_engine}
        
        self.admin_tools = AdminTools(
            self.db, self.price_engines, self.trade_managers,
            self.step_controllers, self.strategy_engines
        )
    
    def test_intervene_volatility(self):
        """测试干预波动率"""
        result = self.admin_tools.intervene_stock_params(
            room_id="test_room",
            stock_code="AAPL",
            volatility=0.05
        )
        
        self.assertTrue(result)
        self.assertEqual(self.price_engine.stocks["AAPL"].config.volatility, 0.05)
    
    def test_intervene_drift(self):
        """测试干预漂移率"""
        result = self.admin_tools.intervene_stock_params(
            room_id="test_room",
            stock_code="AAPL",
            drift=0.001
        )
        
        self.assertTrue(result)
        self.assertEqual(self.price_engine.stocks["AAPL"].config.drift, 0.001)
    
    def test_intervene_model(self):
        """测试干预价格模型"""
        result = self.admin_tools.intervene_stock_params(
            room_id="test_room",
            stock_code="AAPL",
            model="mean_reversion"
        )
        
        self.assertTrue(result)
        from server.price_engine import PriceModel
        self.assertEqual(self.price_engine.stocks["AAPL"].config.model, PriceModel.MEAN_REVERSION)
    
    def test_set_stock_price(self):
        """测试直接设定股票价格"""
        result = self.admin_tools.set_stock_price(
            room_id="test_room",
            stock_code="AAPL",
            new_price=200.0
        )
        
        self.assertTrue(result)
        self.assertEqual(self.price_engine.stocks["AAPL"].current_price, 200.0)
    
    def test_intervene_invalid_room(self):
        """测试无效房间"""
        result = self.admin_tools.intervene_stock_params(
            room_id="invalid_room",
            stock_code="AAPL",
            volatility=0.05
        )
        
        self.assertFalse(result)
    
    def test_intervene_invalid_stock(self):
        """测试无效股票代码"""
        result = self.admin_tools.intervene_stock_params(
            room_id="test_room",
            stock_code="INVALID",
            volatility=0.05
        )
        
        self.assertFalse(result)
    
    def test_update_robot_params(self):
        """测试更新机器人参数"""
        # 注册机器人
        self.strategy_engine.register_robot(
            robot_id="robot_1",
            room_id="test_room",
            name="测试机器人",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000
        )
        
        params = {"trade_probability": 0.9, "position_ratio": 0.5}
        result = self.admin_tools.update_robot_params("robot_1", params)
        
        self.assertTrue(result)
        robot_strategy = self.strategy_engine.strategies["robot_1"]
        self.assertEqual(robot_strategy.config.trade_probability, 0.9)


class TestAdminToolsRoomManagement(unittest.TestCase):
    """测试房间管理"""
    
    def setUp(self):
        """设置测试环境"""
        self.db = MockDatabase()
        self.db.rooms = {"test_room": {"name": "测试房间"}}
        
        self.price_engine = PriceEngine()
        self.trade_manager = MagicMock()
        self.step_controller = StepController()
        self.strategy_engine = StrategyEngine()
        
        self.price_engines = {"test_room": self.price_engine}
        self.trade_managers = {"test_room": self.trade_manager}
        self.step_controllers = {"test_room": self.step_controller}
        self.strategy_engines = {"test_room": self.strategy_engine}
        
        self.admin_tools = AdminTools(
            self.db, self.price_engines, self.trade_managers,
            self.step_controllers, self.strategy_engines
        )
    
    def test_destroy_room(self):
        """测试销毁房间"""
        result = asyncio.run(self.admin_tools.destroy_room("test_room"))
        
        self.assertTrue(result)
        self.assertNotIn("test_room", self.price_engines)
        self.assertNotIn("test_room", self.trade_managers)
        self.assertNotIn("test_room", self.step_controllers)
        self.assertNotIn("test_room", self.strategy_engines)
    
    def test_kick_user(self):
        """测试踢出用户"""
        user_connections = {"user_1": AsyncMock()}
        
        result = asyncio.run(self.admin_tools.kick_user(
            room_id="test_room",
            user_id="user_1",
            user_connections=user_connections
        ))
        
        self.assertTrue(result)
        user_connections["user_1"].close.assert_called_once()
    
    def test_admin_step_forward(self):
        """测试管理员触发步进"""
        self.step_controller.create_room("test_room")
        
        result = asyncio.run(self.admin_tools.admin_step_forward("test_room"))
        self.assertTrue(result)
    
    def test_admin_fast_forward_start(self):
        """测试开始快进"""
        self.step_controller.create_room("test_room")
        
        result = asyncio.run(self.admin_tools.admin_fast_forward(
            room_id="test_room",
            speed=2.0,
            start=True
        ))
        self.assertTrue(result)
    
    def test_admin_pause(self):
        """测试暂停房间"""
        self.step_controller.create_room("test_room")
        
        result = asyncio.run(self.admin_tools.admin_pause("test_room"))
        self.assertTrue(result)
    
    def test_admin_resume(self):
        """测试恢复房间"""
        self.step_controller.create_room("test_room")
        asyncio.run(self.admin_tools.admin_pause("test_room"))
        
        result = asyncio.run(self.admin_tools.admin_resume("test_room"))
        self.assertTrue(result)
    
    def test_get_room_full_status(self):
        """测试获取房间完整状态"""
        self.step_controller.create_room("test_room")
        
        status = self.admin_tools.get_room_full_status("test_room", {"AAPL": 150.0})
        
        self.assertIsNotNone(status)
        self.assertIn("state", status)
        self.assertIn("stocks", status)
        self.assertIn("robots", status)


if __name__ == "__main__":
    unittest.main()
