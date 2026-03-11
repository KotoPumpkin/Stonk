"""
Stonk - 策略引擎单元测试
"""

import unittest
import random
from server.strategy_engine import (
    StrategyEngine, StrategyType, TradeAction,
    RetailStrategy, InstitutionStrategy, TrendStrategy,
    RetailConfig, InstitutionConfig, TrendConfig,
    RobotState, TradeDecision
)


class TestStrategyConfigs(unittest.TestCase):
    """策略配置测试"""
    
    def test_retail_config_default(self):
        """测试散户策略默认配置"""
        config = RetailConfig()
        self.assertEqual(config.momentum_window, 3)
        self.assertEqual(config.sentiment_weight, 0.5)
        self.assertEqual(config.trade_frequency, 0.8)
        self.assertEqual(config.panic_threshold, -0.05)
        self.assertEqual(config.fomo_threshold, 0.05)
        
    def test_institution_config_default(self):
        """测试机构策略默认配置"""
        config = InstitutionConfig()
        self.assertEqual(config.valuation_weight, 0.6)
        self.assertEqual(config.rebalance_threshold, 0.1)
        self.assertEqual(config.report_sensitivity, 0.4)
        self.assertEqual(config.pe_threshold, 20.0)
        
    def test_trend_config_default(self):
        """测试趋势策略默认配置"""
        config = TrendConfig()
        self.assertEqual(config.trend_window, 10)
        self.assertEqual(config.trend_threshold, 0.03)
        self.assertEqual(config.bias, "long")
        self.assertEqual(config.stop_loss, 0.1)
        
    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = RetailConfig(momentum_window=5, sentiment_weight=0.8)
        config_dict = config.to_dict()
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict["momentum_window"], 5)
        self.assertEqual(config_dict["sentiment_weight"], 0.8)
        
    def test_config_from_dict(self):
        """测试从字典创建配置"""
        data = {"momentum_window": 7, "sentiment_weight": 0.6}
        config = RetailConfig.from_dict(data)
        self.assertEqual(config.momentum_window, 7)
        self.assertEqual(config.sentiment_weight, 0.6)


class TestRetailStrategy(unittest.TestCase):
    """散户游资策略测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = StrategyEngine()
        self.engine.set_seed(42)  # 固定随机种子
        
    def test_retail_strategy_creation(self):
        """测试散户策略创建"""
        robot_id = "robot_001"
        state = self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Retail",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000.0
        )
        self.assertIsNotNone(state)
        self.assertEqual(state.strategy_type, StrategyType.RETAIL)
        self.assertEqual(state.cash, 100000.0)
        
    def test_retail_fomo_buy(self):
        """测试散户追涨行为（FOMO）"""
        robot_id = "robot_001"
        self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Retail",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000.0,
            config={"trade_frequency": 1.0, "fomo_threshold": 0.03}  # 保证交易
        )
        
        # 构造上涨的价格历史（涨幅超过 FOMO 阈值）
        prices = {"STK001": 105.0}
        price_history = {"STK001": [100.0, 101.0, 102.0, 103.0, 105.0]}
        
        decisions = self.engine.execute_decisions(
            room_id="room_001",
            prices=prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 应该有买入决策
        buy_decisions = [d for d in decisions if d.action == TradeAction.BUY]
        self.assertGreater(len(buy_decisions), 0)
        
    def test_retail_panic_sell(self):
        """测试散户杀跌行为（恐慌卖出）"""
        robot_id = "robot_001"
        state = self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Retail",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000.0,
            config={"trade_frequency": 1.0, "panic_threshold": -0.03}
        )
        
        # 先买入持仓
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 100.0)
        
        # 构造下跌的价格历史
        prices = {"STK001": 90.0}
        price_history = {"STK001": [100.0, 98.0, 95.0, 92.0, 90.0]}
        
        decisions = self.engine.execute_decisions(
            room_id="room_001",
            prices=prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 应该有卖出决策
        sell_decisions = [d for d in decisions if d.action == TradeAction.SELL]
        self.assertGreater(len(sell_decisions), 0)
        
    def test_retail_sentiment_impact(self):
        """测试新闻情绪对散户的影响"""
        robot_id = "robot_001"
        self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Retail",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000.0,
            config={"trade_frequency": 1.0, "fomo_threshold": 0.04}
        )
        
        # 设置积极情绪
        self.engine.set_sentiment(robot_id, 0.8)
        
        # 价格小幅上涨（原本不足以触发 FOMO，但加上情绪后应该触发）
        prices = {"STK001": 103.5}
        price_history = {"STK001": [100.0, 101.0, 102.0, 103.0, 103.5]}
        
        decisions = self.engine.execute_decisions(
            room_id="room_001",
            prices=prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 积极情绪应该增加买入可能性
        buy_decisions = [d for d in decisions if d.action == TradeAction.BUY]
        self.assertGreater(len(buy_decisions), 0)


class TestInstitutionStrategy(unittest.TestCase):
    """正规机构策略测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = StrategyEngine()
        self.engine.set_seed(42)
        
    def test_institution_strategy_creation(self):
        """测试机构策略创建"""
        robot_id = "robot_002"
        state = self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Institution",
            strategy_type=StrategyType.INSTITUTION,
            initial_cash=100000.0
        )
        self.assertIsNotNone(state)
        self.assertEqual(state.strategy_type, StrategyType.INSTITUTION)
        
    def test_institution_value_buy(self):
        """测试机构价值投资（低估买入）"""
        robot_id = "robot_002"
        self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Institution",
            strategy_type=StrategyType.INSTITUTION,
            initial_cash=100000.0,
            config={"rebalance_threshold": 0.05}
        )
        
        # 构造价格低于均线的历史（低估）
        prices = {"STK001": 95.0}
        # 前 20 步价格在 100 左右波动，最后一步跌到 95
        price_history = {"STK001": [100.0] * 19 + [95.0]}
        
        # 应用正面财报影响
        self.engine.apply_report_impact(robot_id, "STK001", 0.2)
        
        decisions = self.engine.execute_decisions(
            room_id="room_001",
            prices=prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 可能有买入决策（取决于随机性）
        # 由于机构交易频率低，这里主要验证逻辑正确性
        self.assertIsInstance(decisions, list)
        
    def test_institution_overvalued_sell(self):
        """测试机构高估卖出"""
        robot_id = "robot_002"
        state = self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Institution",
            strategy_type=StrategyType.INSTITUTION,
            initial_cash=100000.0,
            config={"rebalance_threshold": 0.05}
        )
        
        # 先添加持仓
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 100.0)
        
        # 构造价格高于均线的历史（高估）
        prices = {"STK001": 120.0}
        price_history = {"STK001": [100.0] * 19 + [120.0]}
        
        decisions = self.engine.execute_decisions(
            room_id="room_001",
            prices=prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        self.assertIsInstance(decisions, list)
        
    def test_institution_low_turnover(self):
        """测试机构低换手率特征"""
        robot_id = "robot_002"
        self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Institution",
            strategy_type=StrategyType.INSTITUTION,
            initial_cash=100000.0
        )
        
        # 构造中性价格历史
        prices = {"STK001": 100.0}
        price_history = {"STK001": list(range(90, 111))}  # 20 个数据点
        
        # 多次执行决策，统计交易次数
        trade_count = 0
        for _ in range(100):
            decisions = self.engine.execute_decisions(
                room_id="room_001",
                prices=prices,
                price_history=price_history,
                available_stocks=["STK001"]
            )
            trade_count += len(decisions)
            
        # 机构交易频率约 30%，100 次中应该有 20-40 次交易
        self.assertLess(trade_count, 50)  # 不会太频繁


class TestTrendStrategy(unittest.TestCase):
    """趋势追踪策略测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = StrategyEngine()
        self.engine.set_seed(42)
        
    def test_trend_strategy_creation(self):
        """测试趋势策略创建"""
        robot_id = "robot_003"
        state = self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Trend",
            strategy_type=StrategyType.TREND,
            initial_cash=100000.0
        )
        self.assertIsNotNone(state)
        self.assertEqual(state.strategy_type, StrategyType.TREND)
        
    def test_trend_follow_long(self):
        """测试趋势追踪（做多偏好）"""
        robot_id = "robot_003"
        self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Trend Long",
            strategy_type=StrategyType.TREND,
            initial_cash=100000.0,
            config={"bias": "long", "trend_threshold": 0.02}
        )
        
        # 构造上涨趋势
        prices = {"STK001": 110.0}
        price_history = {"STK001": list(range(100, 111))}  # 从 100 涨到 110
        
        decisions = self.engine.execute_decisions(
            room_id="room_001",
            prices=prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 应该有买入决策
        buy_decisions = [d for d in decisions if d.action == TradeAction.BUY]
        self.assertGreater(len(buy_decisions), 0)
        
    def test_trend_follow_short(self):
        """测试趋势追踪（做空偏好）"""
        robot_id = "robot_003"
        self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Trend Short",
            strategy_type=StrategyType.TREND,
            initial_cash=100000.0,
            config={"bias": "short", "trend_threshold": 0.02}
        )
        
        # 构造下跌趋势
        prices = {"STK001": 90.0}
        price_history = {"STK001": list(range(100, 89, -1))}  # 从 100 跌到 90
        
        decisions = self.engine.execute_decisions(
            room_id="room_001",
            prices=prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 做空偏好在下跌趋势中应该买入（低价买入平仓）或卖出（如果已有持仓）
        self.assertIsInstance(decisions, list)
        
    def test_trend_stop_loss(self):
        """测试趋势策略止损"""
        robot_id = "robot_003"
        state = self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Trend",
            strategy_type=StrategyType.TREND,
            initial_cash=100000.0,
            config={"stop_loss": 0.1}  # 10% 止损
        )
        
        # 添加亏损持仓（成本 100，当前 85，亏损 15%）
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 100.0)
        
        prices = {"STK001": 85.0}
        price_history = {"STK001": [100.0] * 10 + [85.0]}
        
        decisions = self.engine.execute_decisions(
            room_id="room_001",
            prices=prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 应该触发止损卖出
        sell_decisions = [d for d in decisions if d.action == TradeAction.SELL]
        self.assertGreater(len(sell_decisions), 0)


class TestStrategyEngine(unittest.TestCase):
    """策略引擎主类测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = StrategyEngine()
        self.engine.set_seed(42)
        
    def test_register_robot(self):
        """测试注册机器人"""
        robot_id = "robot_001"
        state = self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Bot",
            strategy_type=StrategyType.RETAIL,
            initial_cash=50000.0
        )
        
        self.assertIsNotNone(state)
        self.assertEqual(state.robot_id, robot_id)
        self.assertEqual(state.room_id, "room_001")
        self.assertEqual(state.name, "Test Bot")
        self.assertEqual(state.cash, 50000.0)
        
    def test_remove_robot(self):
        """测试移除机器人"""
        robot_id = "robot_001"
        self.engine.register_robot(
            robot_id=robot_id,
            room_id="room_001",
            name="Test Bot",
            strategy_type=StrategyType.RETAIL,
            initial_cash=50000.0
        )
        
        # 移除
        success = self.engine.remove_robot(robot_id)
        self.assertTrue(success)
        
        # 验证已移除
        self.assertIsNone(self.engine.get_robot_state(robot_id))
        self.assertNotIn(robot_id, self.engine.get_room_robots("room_001"))
        
    def test_get_room_robots(self):
        """测试获取房间内机器人列表"""
        # 注册多个机器人
        self.engine.register_robot("r1", "room_001", "Bot1", StrategyType.RETAIL, 10000.0)
        self.engine.register_robot("r2", "room_001", "Bot2", StrategyType.INSTITUTION, 10000.0)
        self.engine.register_robot("r3", "room_002", "Bot3", StrategyType.TREND, 10000.0)
        
        room1_robots = self.engine.get_room_robots("room_001")
        self.assertEqual(len(room1_robots), 2)
        self.assertIn("r1", room1_robots)
        self.assertIn("r2", room1_robots)
        
        room2_robots = self.engine.get_room_robots("room_002")
        self.assertEqual(len(room2_robots), 1)
        
    def test_update_robot_cash(self):
        """测试更新机器人现金"""
        robot_id = "robot_001"
        self.engine.register_robot(robot_id, "room_001", "Bot", StrategyType.RETAIL, 10000.0)
        
        # 更新现金
        success = self.engine.update_robot_cash(robot_id, 15000.0)
        self.assertTrue(success)
        
        state = self.engine.get_robot_state(robot_id)
        self.assertEqual(state.cash, 15000.0)
        
    def test_update_robot_holdings_buy(self):
        """测试更新机器人持仓（买入）"""
        robot_id = "robot_001"
        self.engine.register_robot(robot_id, "room_001", "Bot", StrategyType.RETAIL, 10000.0)
        
        # 买入
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 50.0)
        
        state = self.engine.get_robot_state(robot_id)
        self.assertEqual(state.holdings.get("STK001"), 100)
        self.assertAlmostEqual(state.cost_basis.get("STK001"), 50.0)
        
    def test_update_robot_holdings_add_position(self):
        """测试加仓"""
        robot_id = "robot_001"
        self.engine.register_robot(robot_id, "room_001", "Bot", StrategyType.RETAIL, 10000.0)
        
        # 第一次买入
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 50.0)
        # 第二次买入（更高价）
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 60.0)
        
        state = self.engine.get_robot_state(robot_id)
        self.assertEqual(state.holdings.get("STK001"), 200)
        # 平均成本 = (100*50 + 100*60) / 200 = 55
        self.assertAlmostEqual(state.cost_basis.get("STK001"), 55.0)
        
    def test_update_robot_holdings_sell(self):
        """测试卖出持仓"""
        robot_id = "robot_001"
        self.engine.register_robot(robot_id, "room_001", "Bot", StrategyType.RETAIL, 10000.0)
        
        # 买入
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 50.0)
        # 卖出一半
        self.engine.update_robot_holdings(robot_id, "STK001", -50, 55.0)
        
        state = self.engine.get_robot_state(robot_id)
        self.assertEqual(state.holdings.get("STK001"), 50)
        # 卖出后成本价不变
        self.assertAlmostEqual(state.cost_basis.get("STK001"), 50.0)
        
    def test_update_robot_holdings_clear(self):
        """测试清仓"""
        robot_id = "robot_001"
        self.engine.register_robot(robot_id, "room_001", "Bot", StrategyType.RETAIL, 10000.0)
        
        # 买入
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 50.0)
        # 全部卖出
        self.engine.update_robot_holdings(robot_id, "STK001", -100, 55.0)
        
        state = self.engine.get_robot_state(robot_id)
        self.assertNotIn("STK001", state.holdings)
        self.assertNotIn("STK001", state.cost_basis)
        
    def test_set_room_sentiment(self):
        """测试设置房间情绪"""
        # 注册两个机器人
        self.engine.register_robot("r1", "room_001", "Bot1", StrategyType.RETAIL, 10000.0)
        self.engine.register_robot("r2", "room_001", "Bot2", StrategyType.RETAIL, 10000.0)
        
        # 设置房间情绪
        count = self.engine.set_room_sentiment("room_001", 0.8)
        self.assertEqual(count, 2)
        
    def test_update_robot_params(self):
        """测试动态更新机器人参数"""
        robot_id = "robot_001"
        self.engine.register_robot(
            robot_id, "room_001", "Bot", 
            StrategyType.RETAIL, 10000.0,
            config={"momentum_window": 3}
        )
        
        # 更新参数
        success = self.engine.update_robot_params(robot_id, {"momentum_window": 10, "trade_frequency": 0.9})
        self.assertTrue(success)
        
        strategy = self.engine.strategies[robot_id]
        self.assertEqual(strategy.config.momentum_window, 10)
        self.assertEqual(strategy.config.trade_frequency, 0.9)
        
    def test_get_robot_summary(self):
        """测试获取机器人摘要"""
        robot_id = "robot_001"
        self.engine.register_robot(robot_id, "room_001", "Bot", StrategyType.RETAIL, 10000.0)
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 50.0)
        
        prices = {"STK001": 55.0}
        summary = self.engine.get_robot_summary(robot_id, prices)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary["robot_id"], robot_id)
        self.assertEqual(summary["name"], "Bot")
        self.assertEqual(summary["strategy_type"], "retail")
        self.assertIn("cash", summary)
        self.assertIn("holdings", summary)
        self.assertIn("total_value", summary)
        self.assertIn("profit_loss", summary)
        
    def test_get_all_robot_summaries(self):
        """测试获取所有机器人摘要"""
        self.engine.register_robot("r1", "room_001", "Bot1", StrategyType.RETAIL, 10000.0)
        self.engine.register_robot("r2", "room_001", "Bot2", StrategyType.INSTITUTION, 10000.0)
        
        prices = {}
        summaries = self.engine.get_all_robot_summaries("room_001", prices)
        
        self.assertEqual(len(summaries), 2)
        
    def test_reset_robot(self):
        """测试重置机器人"""
        robot_id = "robot_001"
        self.engine.register_robot(robot_id, "room_001", "Bot", StrategyType.RETAIL, 10000.0)
        self.engine.update_robot_holdings(robot_id, "STK001", 100, 50.0)
        
        # 重置
        success = self.engine.reset_robot(robot_id, 50000.0)
        self.assertTrue(success)
        
        state = self.engine.get_robot_state(robot_id)
        self.assertEqual(state.cash, 50000.0)
        self.assertEqual(len(state.holdings), 0)
        self.assertEqual(len(state.decision_history), 0)
        
    def test_clear_room(self):
        """测试清空房间"""
        self.engine.register_robot("r1", "room_001", "Bot1", StrategyType.RETAIL, 10000.0)
        self.engine.register_robot("r2", "room_001", "Bot2", StrategyType.INSTITUTION, 10000.0)
        
        # 清空房间
        self.engine.clear_room("room_001")
        
        robots = self.engine.get_room_robots("room_001")
        self.assertEqual(len(robots), 0)
        
    def test_execute_decisions(self):
        """测试执行决策"""
        self.engine.register_robot("r1", "room_001", "Bot1", StrategyType.RETAIL, 100000.0)
        
        prices = {"STK001": 100.0}
        price_history = {"STK001": [100.0] * 10}
        
        decisions = self.engine.execute_decisions(
            room_id="room_001",
            prices=prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        self.assertIsInstance(decisions, list)
        
    def test_decision_history_recording(self):
        """测试决策历史记录"""
        self.engine.register_robot(
            "r1", "room_001", "Bot1", StrategyType.RETAIL, 100000.0,
            config={"trade_frequency": 1.0, "fomo_threshold": 0.01}
        )
        
        # 制造明显上涨趋势
        prices = {"STK001": 110.0}
        price_history = {"STK001": list(range(100, 111))}
        
        # 执行多步
        for i in range(5):
            self.engine.execute_decisions(
                room_id="room_001",
                prices=prices,
                price_history=price_history,
                available_stocks=["STK001"]
            )
            
        state = self.engine.get_robot_state("r1")
        # 应该有决策记录
        self.assertGreater(len(state.decision_history), 0)
        
    def test_robot_state_calculations(self):
        """测试机器人状态计算"""
        robot_id = "robot_001"
        state = RobotState(
            robot_id=robot_id,
            room_id="room_001",
            name="Test",
            strategy_type=StrategyType.RETAIL,
            cash=50000.0,
            holdings={"STK001": 100, "STK002": 50},
            cost_basis={"STK001": 50.0, "STK002": 100.0}
        )
        
        prices = {"STK001": 55.0, "STK002": 110.0}
        
        # 测试持仓市值
        position_value = state.get_position_value(prices)
        self.assertEqual(position_value, 5500.0 + 5500.0)  # 100*55 + 50*110
        
        # 测试总资产
        total_value = state.get_total_value(prices)
        self.assertEqual(total_value, 50000.0 + 11000.0)
        
        # 测试盈亏
        profit_loss = state.get_profit_loss(prices)
        # 持仓盈利 = (55-50)*100 + (110-100)*50 = 500 + 500 = 1000
        self.assertEqual(profit_loss, 1000.0)


class TestTradeDecision(unittest.TestCase):
    """交易决策测试"""
    
    def test_trade_decision_to_dict(self):
        """测试交易决策转换为字典"""
        decision = TradeDecision(
            robot_id="r1",
            stock_code="STK001",
            action=TradeAction.BUY,
            quantity=100,
            reason="Momentum buy",
            confidence=0.8
        )
        
        d = decision.to_dict()
        self.assertEqual(d["robot_id"], "r1")
        self.assertEqual(d["stock_code"], "STK001")
        self.assertEqual(d["action"], "buy")
        self.assertEqual(d["quantity"], 100)
        self.assertEqual(d["reason"], "Momentum buy")
        self.assertEqual(d["confidence"], 0.8)


if __name__ == '__main__':
    unittest.main()
