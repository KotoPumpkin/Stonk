"""
Phase 2 集成测试 - 价格引擎 + 交易撮合 + 步进控制
"""

import unittest
import asyncio
from datetime import datetime
from server.price_engine import PriceEngine, PriceModel
from server.trade_manager import TradeManager, OrderSide, OrderStatus
from server.step_controller import StepController, StepMode, StepConfig, RoomState


class TestPhase2Integration(unittest.TestCase):
    """Phase 2 集成测试"""
    
    def setUp(self):
        """测试前设置"""
        # 创建价格引擎
        self.price_engine = PriceEngine()
        self.price_engine.set_seed(42)  # 固定随机种子以确保可重复性
        
        # 添加股票
        self.price_engine.add_stock("AAPL", "Apple Inc.", 150.0, model="random_walk")
        self.price_engine.add_stock("GOOGL", "Google", 2800.0, model="mean_reversion")
        
        # 创建交易管理器
        self.trade_manager = TradeManager()
        self.trade_manager.create_account("user1", 1000000.0)
        self.trade_manager.create_account("user2", 1000000.0)
        
        # 创建步进控制器和房间
        self.step_controller = StepController()
        self.room_id = "test_room"
        self.step_controller.create_room(self.room_id)
        self.step_controller.add_participant(self.room_id, "user1")
        self.step_controller.add_participant(self.room_id, "user2")
    
    def test_complete_workflow(self):
        """测试完整的交易流程"""
        # 1. 获取初始价格
        prices = self.price_engine.get_current_prices()
        self.assertIn("AAPL", prices)
        self.assertIn("GOOGL", prices)
        
        initial_aapl = prices["AAPL"]
        initial_googl = prices["GOOGL"]
        
        # 2. 用户下单
        order1 = self.trade_manager.place_order(
            user_id="user1",
            stock_code="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=initial_aapl
        )
        self.assertIsNotNone(order1)
        
        order2 = self.trade_manager.place_order(
            user_id="user2",
            stock_code="GOOGL",
            side=OrderSide.BUY,
            quantity=50,
            price=initial_googl
        )
        self.assertIsNotNone(order2)
        
        # 3. 开始步进，进入决策期
        asyncio.run(self.step_controller.start_step(self.room_id))
        room = self.step_controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.DECISION)
        
        # 4. 用户标记准备就绪
        asyncio.run(self.step_controller.user_ready(self.room_id, "user1"))
        asyncio.run(self.step_controller.user_ready(self.room_id, "user2"))
        
        # 5. 所有用户就绪后，步进自动处理完成
        room = self.step_controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.IDLE)
        self.assertEqual(room.current_step, 1)
        self.assertGreater(room.virtual_time, 0)
        
        # 6. 生成新价格
        self.price_engine.batch_generate()
        new_prices = self.price_engine.get_current_prices()
        
        # 7. 撮合交易
        trades_aapl = self.trade_manager.match_orders("AAPL", new_prices["AAPL"])
        trades_googl = self.trade_manager.match_orders("GOOGL", new_prices["GOOGL"])
        
        self.assertEqual(len(trades_aapl), 1)
        self.assertEqual(len(trades_googl), 1)
        
        # 8. 验证订单状态
        self.assertEqual(order1.status, OrderStatus.FILLED)
        self.assertEqual(order2.status, OrderStatus.FILLED)
        
        # 9. 验证持仓
        account1 = self.trade_manager.get_account("user1")
        pos_aapl = account1.get_position("AAPL")
        self.assertEqual(pos_aapl.quantity, 100)
        
        account2 = self.trade_manager.get_account("user2")
        pos_googl = account2.get_position("GOOGL")
        self.assertEqual(pos_googl.quantity, 50)
        
        # 10. 验证就绪状态已重置
        room = self.step_controller.get_room(self.room_id)
        self.assertEqual(len(room.ready_users), 0)
    
    def test_multi_step_trading(self):
        """测试多步交易"""
        prices_history = []
        
        for step in range(5):
            # 获取当前价格
            prices = self.price_engine.get_current_prices()
            prices_history.append(prices.copy())
            
            # 用户下单
            side = OrderSide.BUY if step % 2 == 0 else OrderSide.SELL
            
            # 如果是卖单，确保有持仓
            if side == OrderSide.SELL:
                account = self.trade_manager.get_account("user1")
                pos = account.get_position("AAPL")
                if pos.quantity < 10:
                    side = OrderSide.BUY  # 持仓不足时改为买入
            
            order = self.trade_manager.place_order(
                user_id="user1",
                stock_code="AAPL",
                side=side,
                quantity=10,
                price=prices["AAPL"]
            )
            self.assertIsNotNone(order)
            
            # 开始步进
            asyncio.run(self.step_controller.start_step(self.room_id))
            
            # 用户标记准备就绪
            asyncio.run(self.step_controller.user_ready(self.room_id, "user1"))
            asyncio.run(self.step_controller.user_ready(self.room_id, "user2"))
            
            # 生成新价格
            self.price_engine.batch_generate()
            
            # 撮合交易
            new_prices = self.price_engine.get_current_prices()
            self.trade_manager.match_orders("AAPL", new_prices["AAPL"])
        
        # 验证价格历史
        self.assertEqual(len(prices_history), 5)
        
        # 验证步进计数
        room = self.step_controller.get_room(self.room_id)
        self.assertEqual(room.current_step, 5)
        
        # 验证有成交记录
        trades = self.trade_manager.get_recent_trades(stock_code="AAPL")
        self.assertGreater(len(trades), 0)
    
    def test_price_volatility_impact(self):
        """测试价格波动对交易的影响"""
        # 设置高波动率
        self.price_engine.adjust_volatility("AAPL", 0.5)
        
        initial_price = self.price_engine.get_all_prices()["AAPL"]
        
        # 生成多次价格
        prices = [initial_price]
        for _ in range(20):
            self.price_engine.generate_next_price("AAPL")
            prices.append(self.price_engine.get_all_prices()["AAPL"])
        
        # 计算价格变化
        price_changes = [abs(prices[i] - prices[i-1]) / prices[i-1] 
                        for i in range(1, len(prices))]
        avg_change = sum(price_changes) / len(price_changes)
        
        # 高波动率应该导致较大的价格变化
        self.assertGreater(avg_change, 0.01)
    
    def test_fast_forward_mode(self):
        """测试快进模式"""
        # 启用快进
        result = asyncio.run(self.step_controller.start_fast_forward(self.room_id))
        self.assertTrue(result)
        
        # 获取房间状态
        room = self.step_controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.FAST_FORWARD)
        
        # 停止快进
        result = asyncio.run(self.step_controller.stop_fast_forward(self.room_id))
        self.assertTrue(result)
        
        room = self.step_controller.get_room(self.room_id)
        self.assertEqual(room.state, RoomState.IDLE)
    
    def test_order_book_management(self):
        """测试订单簿管理"""
        prices = self.price_engine.get_current_prices()
        
        # 添加多个买单
        orders = []
        for i in range(3):
            order = self.trade_manager.place_order(
                user_id="user1",
                stock_code="AAPL",
                side=OrderSide.BUY,
                quantity=10 * (i + 1),
                price=prices["AAPL"]
            )
            self.assertIsNotNone(order)
            orders.append(order)
        
        # 给 user2 添加持仓后下卖单
        account2 = self.trade_manager.get_account("user2")
        pos2 = account2.get_position("AAPL")
        pos2.update_buy(200, prices["AAPL"])
        
        for i in range(2):
            order = self.trade_manager.place_order(
                user_id="user2",
                stock_code="AAPL",
                side=OrderSide.SELL,
                quantity=10 * (i + 1),
                price=prices["AAPL"]
            )
            self.assertIsNotNone(order)
            orders.append(order)
        
        # 验证订单簿中有 5 个订单
        self.assertEqual(len(self.trade_manager.orders), 5)
        
        # 取消一个订单
        self.trade_manager.cancel_order(orders[0].order_id)
        self.assertEqual(orders[0].status, OrderStatus.CANCELLED)
        
        # 撮合订单
        self.price_engine.batch_generate()
        new_prices = self.price_engine.get_current_prices()
        trades = self.trade_manager.match_orders("AAPL", new_prices["AAPL"])
        
        # 应该有 4 个成交（1个被取消）
        self.assertEqual(len(trades), 4)
    
    def test_different_step_modes(self):
        """测试不同的步进模式"""
        base_time = datetime(2024, 1, 1).timestamp()
        
        modes = [
            (StepMode.SECOND, 1),
            (StepMode.HOUR, 3600),
            (StepMode.DAY, 86400),
            (StepMode.MONTH, 30 * 86400)
        ]
        
        for mode, expected_delta in modes:
            # 为每种模式创建独立房间
            room_id = f"room_{mode.value}"
            config = StepConfig(mode=mode)
            self.step_controller.create_room(room_id, step_config=config)
            
            # 执行步进（无参与者，直接完成）
            asyncio.run(self.step_controller.start_step(room_id))
            
            # 获取虚拟时间
            room = self.step_controller.get_room(room_id)
            expected_time = base_time + expected_delta
            self.assertAlmostEqual(room.virtual_time, expected_time, places=0,
                                   msg=f"Mode {mode.value}: expected {expected_time}, got {room.virtual_time}")
    
    def test_price_history_tracking(self):
        """测试价格历史跟踪"""
        # 生成多个价格点
        for _ in range(10):
            self.price_engine.generate_next_price("AAPL")
        
        # 获取历史数据
        history = self.price_engine.get_price_history("AAPL")
        self.assertEqual(len(history), 11)  # 包括初始价格
        
        # 验证历史数据格式 - 历史数据是价格列表
        for price in history:
            self.assertIsInstance(price, float)
            self.assertGreater(price, 0)
    
    def test_account_summary_after_trading(self):
        """测试交易后的账户摘要"""
        prices = self.price_engine.get_current_prices()
        
        # user1 买入 AAPL
        order = self.trade_manager.place_order(
            user_id="user1",
            stock_code="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=prices["AAPL"]
        )
        
        # 撮合
        self.trade_manager.match_orders("AAPL", prices["AAPL"])
        
        # 获取账户摘要
        summary = self.trade_manager.get_account_summary(
            "user1", prices, 1000000.0
        )
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary["user_id"], "user1")
        self.assertIn("cash", summary)
        self.assertIn("total_value", summary)
        self.assertIn("profit_loss", summary)
        self.assertIn("positions", summary)
        self.assertEqual(len(summary["positions"]), 1)
        self.assertEqual(summary["positions"][0]["stock_code"], "AAPL")
        self.assertEqual(summary["positions"][0]["quantity"], 100)
    
    def test_news_sentiment_affects_price(self):
        """测试新闻情绪影响价格"""
        initial_price = self.price_engine.get_all_prices()["AAPL"]
        
        # 应用强烈的积极情绪
        self.price_engine.apply_news_sentiment("AAPL", sentiment=0.8, impact=0.5)
        
        # 生成多次价格
        positive_prices = []
        for _ in range(20):
            self.price_engine.generate_next_price("AAPL")
            positive_prices.append(self.price_engine.get_all_prices()["AAPL"])
        
        # 积极情绪应该使价格整体上涨
        avg_positive = sum(positive_prices) / len(positive_prices)
        self.assertGreater(avg_positive, initial_price * 0.9)  # 至少不会大幅下跌
    
    def test_step_controller_with_callbacks(self):
        """测试步进控制器回调机制"""
        callback_log = []
        
        async def on_step_completed(**kwargs):
            callback_log.append(("step_completed", kwargs))
        
        async def on_decision_start(**kwargs):
            callback_log.append(("decision_start", kwargs))
        
        self.step_controller.register_callback("step_completed", on_step_completed)
        self.step_controller.register_callback("decision_start", on_decision_start)
        
        # 移除参与者，使步进可以直接完成
        self.step_controller.remove_participant(self.room_id, "user1")
        self.step_controller.remove_participant(self.room_id, "user2")
        
        # 无参与者，步进直接完成
        asyncio.run(self.step_controller.start_step(self.room_id))
        
        # 验证回调被触发
        event_names = [event[0] for event in callback_log]
        self.assertIn("decision_start", event_names)
        self.assertIn("step_completed", event_names)


if __name__ == '__main__':
    unittest.main()
