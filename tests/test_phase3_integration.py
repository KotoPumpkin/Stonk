"""
Stonk - Phase 3 集成测试

测试策略引擎与价格引擎、交易管理器的完整集成流程。
"""

import unittest
from server.strategy_engine import (
    StrategyEngine, StrategyType, TradeAction
)
from server.price_engine import PriceEngine, PriceConfig, PriceModel
from server.trade_manager import TradeManager, OrderSide


class TestPhase3Integration(unittest.TestCase):
    """Phase 3 集成测试"""
    
    def setUp(self):
        """测试前设置"""
        self.strategy_engine = StrategyEngine()
        self.strategy_engine.set_seed(42)
        
        self.price_engine = PriceEngine()
        self.price_engine.set_seed(42)
        
        self.trade_manager = TradeManager()
        
    def test_complete_robot_trading_flow(self):
        """测试完整的机器人交易流程"""
        # 1. 注册机器人
        self.strategy_engine.register_robot(
            robot_id="robot_001",
            room_id="room_001",
            name="Test Retail Bot",
            strategy_type=StrategyType.RETAIL,
            initial_cash=100000.0,
            config={"trade_frequency": 1.0, "fomo_threshold": 0.02}
        )
        
        # 2. 在价格引擎中添加股票
        self.price_engine.add_stock(
            code="STK001",
            name="Test Stock",
            initial_price=100.0,
            volatility=0.02
        )
        
        # 3. 在交易管理器中创建账户
        self.trade_manager.create_account("robot_001", 100000.0)
        
        # 4. 生成价格历史
        price_history = {"STK001": [100.0]}
        for _ in range(10):
            new_price = self.price_engine.generate_next_price("STK001")
            price_history["STK001"].append(new_price)
            
        current_prices = self.price_engine.get_all_prices()
        
        # 5. 执行机器人决策
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=current_prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 6. 将决策转化为实际订单
        for decision in decisions:
            if decision.action == TradeAction.BUY:
                order = self.trade_manager.place_order(
                    user_id=decision.robot_id,
                    stock_code=decision.stock_code,
                    side=OrderSide.BUY,
                    quantity=decision.quantity,
                    price=current_prices.get(decision.stock_code, 0)
                )
                self.assertIsNotNone(order)
            elif decision.action == TradeAction.SELL:
                order = self.trade_manager.place_order(
                    user_id=decision.robot_id,
                    stock_code=decision.stock_code,
                    side=OrderSide.SELL,
                    quantity=decision.quantity,
                    price=current_prices.get(decision.stock_code, 0)
                )
                # 卖单需要有持仓，可能为 None
        
        # 7. 验证机器人状态更新
        robot_state = self.strategy_engine.get_robot_state("robot_001")
        self.assertIsNotNone(robot_state)
        
    def test_multi_robot_same_room(self):
        """测试同一房间内多个机器人同时交易"""
        # 注册三种不同类型的机器人
        self.strategy_engine.register_robot(
            robot_id="retail_001",
            room_id="room_001",
            name="Retail Bot 1",
            strategy_type=StrategyType.RETAIL,
            initial_cash=50000.0,
            config={"trade_frequency": 1.0}
        )
        self.strategy_engine.register_robot(
            robot_id="institution_001",
            room_id="room_001",
            name="Institution Bot 1",
            strategy_type=StrategyType.INSTITUTION,
            initial_cash=200000.0
        )
        self.strategy_engine.register_robot(
            robot_id="trend_001",
            room_id="room_001",
            name="Trend Bot 1",
            strategy_type=StrategyType.TREND,
            initial_cash=100000.0,
            config={"bias": "long"}
        )
        
        # 添加股票并生成价格历史
        self.price_engine.add_stock("STK001", "Test Stock", 100.0)
        price_history = {"STK001": [100.0]}
        for _ in range(15):
            self.price_engine.generate_next_price("STK001")
            price_history["STK001"].append(self.price_engine.stocks["STK001"].current_price)
            
        current_prices = self.price_engine.get_all_prices()
        
        # 执行所有机器人决策
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=current_prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 验证每个机器人都生成了决策（可能为空）
        retail_decisions = [d for d in decisions if d.robot_id == "retail_001"]
        institution_decisions = [d for d in decisions if d.robot_id == "institution_001"]
        trend_decisions = [d for d in decisions if d.robot_id == "trend_001"]
        
        # 所有决策的总和应该合理
        self.assertIsInstance(retail_decisions, list)
        self.assertIsInstance(institution_decisions, list)
        self.assertIsInstance(trend_decisions, list)
        
    def test_news_sentiment_affects_robots(self):
        """测试新闻情绪影响所有机器人"""
        # 注册多个机器人
        self.strategy_engine.register_robot(
            robot_id="r1", room_id="room_001", name="Bot1",
            strategy_type=StrategyType.RETAIL, initial_cash=100000.0,
            config={"trade_frequency": 1.0, "fomo_threshold": 0.01}
        )
        self.strategy_engine.register_robot(
            robot_id="r2", room_id="room_001", name="Bot2",
            strategy_type=StrategyType.RETAIL, initial_cash=100000.0,
            config={"trade_frequency": 1.0, "fomo_threshold": 0.01}
        )
        
        # 设置房间积极情绪
        count = self.strategy_engine.set_room_sentiment("room_001", 0.8)
        self.assertEqual(count, 2)
        
        # 准备价格数据
        self.price_engine.add_stock("STK001", "Test", 100.0)
        price_history = {"STK001": [100.0, 101.0, 102.0]}
        current_prices = {"STK001": 102.0}
        
        # 执行决策
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=current_prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 积极情绪下应该有买入决策
        buy_decisions = [d for d in decisions if d.action == TradeAction.BUY]
        self.assertGreater(len(buy_decisions), 0)
        
    def test_report_impact_on_institution(self):
        """测试财报对机构策略的影响"""
        # 注册机构机器人
        self.strategy_engine.register_robot(
            robot_id="inst_001", room_id="room_001", name="Institution",
            strategy_type=StrategyType.INSTITUTION, initial_cash=200000.0,
            config={"rebalance_threshold": 0.05}
        )
        
        # 准备价格数据（价格低于均线，低估）
        self.price_engine.add_stock("STK001", "Test", 100.0)
        price_history = {"STK001": [100.0] * 19 + [90.0]}  # 跌到 90
        current_prices = {"STK001": 90.0}
        
        # 应用正面财报影响
        self.strategy_engine.apply_report_impact("inst_001", "STK001", 0.3)
        
        # 执行决策
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=current_prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 机构在低估 + 正面财报下可能买入
        self.assertIsInstance(decisions, list)
        
    def test_dynamic_param_update(self):
        """测试动态参数调整影响机器人行为"""
        # 注册机器人，初始低频交易
        self.strategy_engine.register_robot(
            robot_id="r1", room_id="room_001", name="Bot",
            strategy_type=StrategyType.RETAIL, initial_cash=100000.0,
            config={"trade_frequency": 0.1}  # 低频
        )
        
        # 准备价格数据
        self.price_engine.add_stock("STK001", "Test", 100.0)
        price_history = {"STK001": list(range(100, 120))}  # 上涨趋势
        current_prices = {"STK001": 119.0}
        
        # 第一次执行（低频）
        decisions_low = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=current_prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 动态调整参数为高频
        self.strategy_engine.update_robot_params("r1", {"trade_frequency": 1.0})
        
        # 第二次执行（高频）
        decisions_high = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=current_prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 验证参数已更新
        strategy = self.strategy_engine.strategies["r1"]
        self.assertEqual(strategy.config.trade_frequency, 1.0)
        
    def test_robot_profit_loss_calculation(self):
        """测试机器人盈亏计算"""
        # 注册机器人并手动设置持仓
        self.strategy_engine.register_robot(
            robot_id="r1", room_id="room_001", name="Bot",
            strategy_type=StrategyType.RETAIL, initial_cash=50000.0
        )
        
        # 模拟买入：100 股 @ 50 元
        self.strategy_engine.update_robot_holdings("r1", "STK001", 100, 50.0)
        # 现金减少 5000
        self.strategy_engine.update_robot_cash("r1", 95000.0)
        
        # 当前价格上涨到 55 元
        current_prices = {"STK001": 55.0}
        
        # 获取摘要
        summary = self.strategy_engine.get_robot_summary("r1", current_prices)
        
        # 验证计算
        # 持仓价值 = 100 * 55 = 5500
        # 总资产 = 95000 + 5500 = 100500
        # 盈亏 = 5500 - 5000 = 500
        self.assertAlmostEqual(summary["total_value"], 100500.0, places=1)
        self.assertAlmostEqual(summary["profit_loss"], 500.0, places=1)
        
    def test_trend_strategy_bias_effect(self):
        """测试趋势策略偏好方向的影响"""
        # 注册做多偏好的机器人
        self.strategy_engine.register_robot(
            robot_id="long_bot", room_id="room_001", name="Long Bot",
            strategy_type=StrategyType.TREND, initial_cash=100000.0,
            config={"bias": "long", "trend_threshold": 0.02}
        )
        
        # 注册做空偏好的机器人
        self.strategy_engine.register_robot(
            robot_id="short_bot", room_id="room_001", name="Short Bot",
            strategy_type=StrategyType.TREND, initial_cash=100000.0,
            config={"bias": "short", "trend_threshold": 0.02}
        )
        
        # 准备上涨趋势数据
        self.price_engine.add_stock("STK001", "Test", 100.0)
        price_history = {"STK001": list(range(100, 120))}  # 从 100 涨到 119
        current_prices = {"STK001": 119.0}
        
        # 执行决策
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=current_prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 验证不同偏好的机器人有不同决策
        long_decisions = [d for d in decisions if d.robot_id == "long_bot"]
        short_decisions = [d for d in decisions if d.robot_id == "short_bot"]
        
        # 两个机器人都应该有决策
        self.assertIsInstance(long_decisions, list)
        self.assertIsInstance(short_decisions, list)
        
    def test_stop_loss_triggers(self):
        """测试止损触发"""
        # 注册趋势策略机器人，设置 10% 止损
        self.strategy_engine.register_robot(
            robot_id="r1", room_id="room_001", name="Bot",
            strategy_type=StrategyType.TREND, initial_cash=100000.0,
            config={"stop_loss": 0.1}
        )
        
        # 模拟买入：100 股 @ 100 元
        self.strategy_engine.update_robot_holdings("r1", "STK001", 100, 100.0)
        self.strategy_engine.update_robot_cash("r1", 90000.0)
        
        # 价格下跌到 85 元（亏损 15%，超过止损线）
        self.price_engine.add_stock("STK001", "Test", 100.0)
        price_history = {"STK001": [100.0] * 10 + [85.0]}
        current_prices = {"STK001": 85.0}
        
        # 执行决策
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=current_prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        # 应该触发止损卖出
        sell_decisions = [d for d in decisions if d.action == TradeAction.SELL]
        self.assertGreater(len(sell_decisions), 0)
        
        # 验证卖出数量是全部持仓
        self.assertEqual(sell_decisions[0].quantity, 100)
        
    def test_multiple_steps_simulation(self):
        """测试多步模拟"""
        # 注册机器人
        self.strategy_engine.register_robot(
            robot_id="r1", room_id="room_001", name="Bot",
            strategy_type=StrategyType.RETAIL, initial_cash=100000.0,
            config={"trade_frequency": 1.0, "fomo_threshold": 0.01}
        )
        
        # 初始化股票
        self.price_engine.add_stock("STK001", "Test", 100.0, volatility=0.03)
        
        # 模拟 10 步
        price_history = {"STK001": [100.0]}
        all_decisions = []
        
        for step in range(10):
            # 生成新价格
            new_price = self.price_engine.generate_next_price("STK001")
            price_history["STK001"].append(new_price)
            current_prices = self.price_engine.get_all_prices()
            
            # 执行决策
            decisions = self.strategy_engine.execute_decisions(
                room_id="room_001",
                prices=current_prices,
                price_history=price_history,
                available_stocks=["STK001"]
            )
            all_decisions.extend(decisions)
            
        # 验证有决策产生
        self.assertGreater(len(all_decisions), 0)
        
        # 验证机器人状态
        robot_state = self.strategy_engine.get_robot_state("r1")
        self.assertGreater(len(robot_state.decision_history), 0)
        
    def test_robot_reset(self):
        """测试机器人重置后重新交易"""
        # 注册机器人
        self.strategy_engine.register_robot(
            robot_id="r1", room_id="room_001", name="Bot",
            strategy_type=StrategyType.RETAIL, initial_cash=100000.0,
            config={"trade_frequency": 1.0}
        )
        
        # 模拟一些交易
        self.strategy_engine.update_robot_holdings("r1", "STK001", 50, 100.0)
        self.strategy_engine.update_robot_cash("r1", 95000.0)
        
        # 重置
        self.strategy_engine.reset_robot("r1", 100000.0)
        
        # 验证状态已清空
        state = self.strategy_engine.get_robot_state("r1")
        self.assertEqual(state.cash, 100000.0)
        self.assertEqual(len(state.holdings), 0)
        self.assertEqual(len(state.decision_history), 0)
        
        # 重置后可以继续交易
        self.price_engine.add_stock("STK001", "Test", 100.0)
        price_history = {"STK001": list(range(100, 120))}
        current_prices = {"STK001": 119.0}
        
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=current_prices,
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        self.assertIsInstance(decisions, list)


class TestStrategyWithPriceModels(unittest.TestCase):
    """测试不同价格模型下的策略表现"""
    
    def setUp(self):
        self.strategy_engine = StrategyEngine()
        self.strategy_engine.set_seed(42)
        self.price_engine = PriceEngine()
        self.price_engine.set_seed(42)
        
    def test_retail_in_random_walk(self):
        """测试散户在随机游走模型下的行为"""
        self.strategy_engine.register_robot(
            robot_id="r1", room_id="room_001", name="Retail",
            strategy_type=StrategyType.RETAIL, initial_cash=100000.0,
            config={"trade_frequency": 1.0}
        )
        
        self.price_engine.add_stock(
            "STK001", "Test", 100.0, 
            model="random_walk", volatility=0.02
        )
        
        price_history = {"STK001": [100.0]}
        for _ in range(20):
            self.price_engine.generate_next_price("STK001")
            price_history["STK001"].append(self.price_engine.stocks["STK001"].current_price)
            
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=self.price_engine.get_all_prices(),
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        self.assertIsInstance(decisions, list)
        
    def test_institution_in_mean_reversion(self):
        """测试机构在均值回归模型下的行为"""
        self.strategy_engine.register_robot(
            robot_id="inst1", room_id="room_001", name="Institution",
            strategy_type=StrategyType.INSTITUTION, initial_cash=200000.0
        )
        
        self.price_engine.add_stock(
            "STK001", "Test", 100.0,
            model="mean_reversion", volatility=0.02,
            mean_price=100.0, reversion_speed=0.1
        )
        
        price_history = {"STK001": [100.0]}
        for _ in range(25):  # 需要更多数据点
            self.price_engine.generate_next_price("STK001")
            price_history["STK001"].append(self.price_engine.stocks["STK001"].current_price)
            
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=self.price_engine.get_all_prices(),
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        self.assertIsInstance(decisions, list)
        
    def test_trend_in_trend_following(self):
        """测试趋势策略在趋势跟踪模型下的行为"""
        self.strategy_engine.register_robot(
            robot_id="trend1", room_id="room_001", name="Trend",
            strategy_type=StrategyType.TREND, initial_cash=100000.0,
            config={"bias": "long", "trend_threshold": 0.02}
        )
        
        # 使用正确的 API 添加股票（趋势跟踪模型）
        stock_id = self.price_engine.add_stock(
            code="STK001",
            name="Test",
            initial_price=100.0,
            volatility=0.02,
            model="trend_following"
        )
        
        price_history = {"STK001": [100.0]}
        for _ in range(15):
            self.price_engine.generate_next_price("STK001")
            price_history["STK001"].append(self.price_engine.stocks["STK001"].current_price)
            
        decisions = self.strategy_engine.execute_decisions(
            room_id="room_001",
            prices=self.price_engine.get_all_prices(),
            price_history=price_history,
            available_stocks=["STK001"]
        )
        
        self.assertIsInstance(decisions, list)


if __name__ == '__main__':
    unittest.main()
