"""
Stonk - 交易撮合引擎单元测试
"""

import unittest
from server.trade_manager import (
    TradeManager, OrderSide, OrderStatus, 
    Order, Trade, Position, Account
)


class TestTradeManager(unittest.TestCase):
    """交易撮合引擎测试"""
    
    def setUp(self):
        """测试前设置"""
        self.manager = TradeManager()
        
        # 添加测试账户
        self.manager.create_account("user1", 100000.0)
        self.manager.create_account("user2", 100000.0)
    
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.manager)
        self.assertEqual(len(self.manager.accounts), 2)
        self.assertEqual(len(self.manager.orders), 0)
    
    def test_add_account(self):
        """测试添加账户"""
        account = self.manager.add_account("user3", 50000.0)
        self.assertIsNotNone(account)
        self.assertIsInstance(account, Account)
        self.assertEqual(account.user_id, "user3")
        self.assertEqual(account.cash, 50000.0)
        self.assertEqual(len(account.positions), 0)
        
        # 通过 get_account 验证
        fetched = self.manager.get_account("user3")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.cash, 50000.0)
    
    def test_get_account(self):
        """测试获取账户"""
        account = self.manager.get_account("user1")
        self.assertIsNotNone(account)
        self.assertIsInstance(account, Account)
        self.assertEqual(account.cash, 100000.0)
        
        # 获取不存在的账户
        self.assertIsNone(self.manager.get_account("invalid"))
    
    def test_place_order_buy(self):
        """测试下单（买入）"""
        order = self.manager.place_order(
            user_id="user1",
            stock_code="TEST001",
            side=OrderSide.BUY,
            quantity=100,
            price=50.0
        )
        
        self.assertIsNotNone(order)
        self.assertIsInstance(order, Order)
        self.assertEqual(order.user_id, "user1")
        self.assertEqual(order.stock_code, "TEST001")
        self.assertEqual(order.side, OrderSide.BUY)
        self.assertEqual(order.quantity, 100)
        self.assertEqual(order.price, 50.0)
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(len(self.manager.orders), 1)
    
    def test_place_order_sell(self):
        """测试下单（卖出）"""
        # 先给账户添加持仓
        account = self.manager.get_account("user1")
        position = account.get_position("TEST001")
        position.update_buy(100, 50.0)
        
        order = self.manager.place_order(
            user_id="user1",
            stock_code="TEST001",
            side=OrderSide.SELL,
            quantity=50,
            price=55.0
        )
        
        self.assertIsNotNone(order)
        self.assertEqual(order.side, OrderSide.SELL)
        self.assertEqual(order.quantity, 50)
    
    def test_place_order_invalid_account(self):
        """测试下单（无效账户）"""
        order = self.manager.place_order(
            user_id="invalid_user",
            stock_code="TEST001",
            side=OrderSide.BUY,
            quantity=100,
            price=50.0
        )
        
        # 无效账户应返回 None
        self.assertIsNone(order)
    
    def test_cancel_order(self):
        """测试取消订单"""
        order = self.manager.place_order(
            user_id="user1",
            stock_code="TEST001",
            side=OrderSide.BUY,
            quantity=100,
            price=50.0
        )
        
        self.assertTrue(self.manager.cancel_order(order.order_id))
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        
        # 取消不存在的订单
        self.assertFalse(self.manager.cancel_order("invalid"))
        
        # 取消已取消的订单
        self.assertFalse(self.manager.cancel_order(order.order_id))
    
    def test_match_orders_buy(self):
        """测试撮合买单"""
        # 下买单
        order = self.manager.place_order(
            user_id="user1",
            stock_code="TEST001",
            side=OrderSide.BUY,
            quantity=100,
            price=50.0
        )
        
        initial_cash = self.manager.get_account("user1").cash
        
        # 撮合订单（按市价成交）
        trades = self.manager.match_orders("TEST001", 50.0)
        
        self.assertEqual(len(trades), 1)
        self.assertEqual(order.status, OrderStatus.FILLED)
        self.assertEqual(order.filled_quantity, 100)
        
        # 检查账户变化
        account = self.manager.get_account("user1")
        self.assertEqual(account.cash, initial_cash - 5000.0)  # 100 * 50
        
        # 检查持仓
        position = account.get_position("TEST001")
        self.assertEqual(position.quantity, 100)
        self.assertAlmostEqual(position.cost_basis, 50.0)
    
    def test_match_orders_sell(self):
        """测试撮合卖单"""
        # 先添加持仓
        account = self.manager.get_account("user1")
        position = account.get_position("TEST001")
        position.update_buy(100, 50.0)
        initial_cash = account.cash
        
        # 下卖单
        order = self.manager.place_order(
            user_id="user1",
            stock_code="TEST001",
            side=OrderSide.SELL,
            quantity=50,
            price=55.0
        )
        
        # 撮合订单
        trades = self.manager.match_orders("TEST001", 55.0)
        
        self.assertEqual(len(trades), 1)
        self.assertEqual(order.status, OrderStatus.FILLED)
        
        # 检查账户变化
        self.assertEqual(account.cash, initial_cash + 2750.0)  # 50 * 55
        self.assertEqual(position.quantity, 50)
    
    def test_match_orders_multiple(self):
        """测试撮合多个订单"""
        # user1 下买单
        buy_order = self.manager.place_order(
            user_id="user1",
            stock_code="TEST001",
            side=OrderSide.BUY,
            quantity=50,
            price=52.0
        )
        
        # user2 下卖单（先给 user2 添加持仓）
        account2 = self.manager.get_account("user2")
        pos2 = account2.get_position("TEST001")
        pos2.update_buy(100, 48.0)
        
        sell_order = self.manager.place_order(
            user_id="user2",
            stock_code="TEST001",
            side=OrderSide.SELL,
            quantity=50,
            price=50.0
        )
        
        # 撮合订单（市价 51.0）
        trades = self.manager.match_orders("TEST001", 51.0)
        
        # 两个订单都应该成交
        self.assertEqual(len(trades), 2)
        self.assertEqual(buy_order.status, OrderStatus.FILLED)
        self.assertEqual(sell_order.status, OrderStatus.FILLED)
    
    def test_cancel_does_not_match(self):
        """测试已取消的订单不会被撮合"""
        order = self.manager.place_order(
            user_id="user1",
            stock_code="TEST001",
            side=OrderSide.BUY,
            quantity=100,
            price=50.0
        )
        
        # 取消订单
        self.manager.cancel_order(order.order_id)
        
        # 撮合不应产生成交
        trades = self.manager.match_orders("TEST001", 50.0)
        self.assertEqual(len(trades), 0)
    
    def test_get_user_orders(self):
        """测试获取用户订单"""
        # 下几个订单
        self.manager.place_order("user1", "TEST001", OrderSide.BUY, 100, 50.0)
        self.manager.place_order("user1", "TEST002", OrderSide.BUY, 50, 100.0)
        self.manager.place_order("user2", "TEST001", OrderSide.BUY, 30, 50.0)
        
        orders = self.manager.get_user_orders("user1")
        self.assertEqual(len(orders), 2)
        
        # 验证订单内容
        for order_dict in orders:
            self.assertEqual(order_dict["user_id"], "user1")
            self.assertIn("order_id", order_dict)
            self.assertIn("status", order_dict)
    
    def test_get_user_orders_active_only(self):
        """测试获取用户活跃订单"""
        order1 = self.manager.place_order("user1", "TEST001", OrderSide.BUY, 100, 50.0)
        order2 = self.manager.place_order("user1", "TEST002", OrderSide.BUY, 50, 100.0)
        
        # 取消一个订单
        self.manager.cancel_order(order1.order_id)
        
        active_orders = self.manager.get_user_orders("user1", active_only=True)
        self.assertEqual(len(active_orders), 1)
        self.assertEqual(active_orders[0]["order_id"], order2.order_id)
    
    def test_calculate_total_value(self):
        """测试计算总资产"""
        # 添加持仓
        account = self.manager.get_account("user1")
        pos1 = account.get_position("TEST001")
        pos1.update_buy(100, 50.0)
        pos2 = account.get_position("TEST002")
        pos2.update_buy(50, 100.0)
        
        # 计算总资产
        prices = {"TEST001": 50.0, "TEST002": 100.0}
        total = account.calculate_total_value(prices)
        
        # 总资产 = 现金 + 持仓价值
        # = 100000 + (100 * 50 + 50 * 100)
        # = 100000 + 10000
        # = 110000
        self.assertEqual(total, 110000.0)
    
    def test_calculate_profit_loss(self):
        """测试计算盈亏"""
        account = self.manager.get_account("user1")
        pos = account.get_position("TEST001")
        pos.update_buy(100, 50.0)
        
        # 价格上涨
        prices = {"TEST001": 60.0}
        profit = account.calculate_profit_loss(100000.0, prices)
        
        # 盈亏 = 总资产 - 初始资金
        # 总资产 = 100000 + 100 * 60 = 106000
        # 盈亏 = 106000 - 100000 = 6000
        self.assertEqual(profit, 6000.0)
    
    def test_get_account_summary(self):
        """测试获取账户摘要"""
        account = self.manager.get_account("user1")
        pos = account.get_position("TEST001")
        pos.update_buy(100, 50.0)
        
        prices = {"TEST001": 55.0}
        summary = self.manager.get_account_summary("user1", prices, 100000.0)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary["user_id"], "user1")
        self.assertIn("cash", summary)
        self.assertIn("total_value", summary)
        self.assertIn("profit_loss", summary)
        self.assertIn("positions", summary)
        self.assertEqual(len(summary["positions"]), 1)
    
    def test_get_order_status(self):
        """测试获取订单状态"""
        order = self.manager.place_order("user1", "TEST001", OrderSide.BUY, 100, 50.0)
        
        status = self.manager.get_order_status(order.order_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["order_id"], order.order_id)
        self.assertEqual(status["user_id"], "user1")
        self.assertEqual(status["stock_code"], "TEST001")
        self.assertEqual(status["side"], "buy")
        self.assertEqual(status["quantity"], 100)
        self.assertEqual(status["status"], "pending")
        
        # 不存在的订单
        self.assertIsNone(self.manager.get_order_status("invalid"))
    
    def test_get_recent_trades(self):
        """测试获取最近成交记录"""
        # 下单并撮合
        self.manager.place_order("user1", "TEST001", OrderSide.BUY, 100, 50.0)
        self.manager.place_order("user1", "TEST002", OrderSide.BUY, 50, 100.0)
        
        self.manager.match_orders("TEST001", 50.0)
        self.manager.match_orders("TEST002", 100.0)
        
        # 获取所有成交
        trades = self.manager.get_recent_trades()
        self.assertEqual(len(trades), 2)
        
        # 按股票过滤
        trades_001 = self.manager.get_recent_trades(stock_code="TEST001")
        self.assertEqual(len(trades_001), 1)
        self.assertEqual(trades_001[0]["stock_code"], "TEST001")
    
    def test_position_update_buy(self):
        """测试持仓买入更新"""
        pos = Position(stock_code="TEST001")
        
        # 第一次买入
        pos.update_buy(100, 50.0)
        self.assertEqual(pos.quantity, 100)
        self.assertAlmostEqual(pos.cost_basis, 50.0)
        
        # 第二次买入（不同价格）
        pos.update_buy(100, 60.0)
        self.assertEqual(pos.quantity, 200)
        # 成本价 = (100*50 + 100*60) / 200 = 55
        self.assertAlmostEqual(pos.cost_basis, 55.0)
    
    def test_position_update_sell(self):
        """测试持仓卖出更新"""
        pos = Position(stock_code="TEST001", quantity=100, cost_basis=50.0)
        
        pos.update_sell(30)
        self.assertEqual(pos.quantity, 70)
    
    def test_order_remaining_quantity(self):
        """测试订单剩余数量"""
        order = Order(
            order_id="test",
            user_id="user1",
            stock_code="TEST001",
            side=OrderSide.BUY,
            quantity=100,
            price=50.0
        )
        
        self.assertEqual(order.remaining_quantity, 100)
        
        order.filled_quantity = 30
        self.assertEqual(order.remaining_quantity, 70)
    
    def test_order_is_active(self):
        """测试订单是否活跃"""
        order = Order(
            order_id="test",
            user_id="user1",
            stock_code="TEST001",
            side=OrderSide.BUY,
            quantity=100,
            price=50.0
        )
        
        self.assertTrue(order.is_active())
        
        order.status = OrderStatus.FILLED
        self.assertFalse(order.is_active())
        
        order.status = OrderStatus.CANCELLED
        self.assertFalse(order.is_active())
        
        order.status = OrderStatus.PARTIAL
        self.assertTrue(order.is_active())
    
    def test_reset(self):
        """测试重置"""
        self.manager.place_order("user1", "TEST001", OrderSide.BUY, 100, 50.0)
        self.manager.match_orders("TEST001", 50.0)
        
        self.manager.reset()
        
        self.assertEqual(len(self.manager.orders), 0)
        self.assertEqual(len(self.manager.accounts), 0)
        self.assertEqual(len(self.manager.trades), 0)
        self.assertEqual(self.manager.order_counter, 0)
        self.assertEqual(self.manager.trade_counter, 0)


if __name__ == '__main__':
    unittest.main()
