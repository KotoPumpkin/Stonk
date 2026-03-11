"""
Stonk - 价格引擎单元测试
"""

import unittest
from server.price_engine import PriceEngine, PriceModel, PriceConfig


class TestPriceEngine(unittest.TestCase):
    """价格引擎测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = PriceEngine()
        self.engine.set_seed(42)  # 设置随机种子保证可重复
    
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.engine)
        self.assertEqual(len(self.engine.stocks), 0)
    
    def test_add_stock(self):
        """测试添加股票"""
        stock_id = self.engine.add_stock(
            code="TEST001",
            name="测试股票",
            initial_price=100.0,
            volatility=0.02,
            drift=0.001
        )
        
        self.assertIsNotNone(stock_id)
        self.assertEqual(len(self.engine.stocks), 1)
        self.assertIn("TEST001", self.engine.stocks)
        
        # 获取股票信息
        stock = self.engine.get_stock("TEST001")
        self.assertIsNotNone(stock)
        self.assertEqual(stock['code'], "TEST001")
        self.assertEqual(stock['current_price'], 100.0)
        self.assertEqual(stock['volatility'], 0.02)
        self.assertEqual(stock['drift'], 0.001)
    
    def test_remove_stock(self):
        """测试移除股票"""
        self.engine.add_stock("TEST001", "测试股票", 100.0)
        self.assertTrue(self.engine.remove_stock("TEST001"))
        self.assertEqual(len(self.engine.stocks), 0)
        
        # 移除不存在的股票
        self.assertFalse(self.engine.remove_stock("INVALID"))
    
    def test_get_stock(self):
        """测试获取股票"""
        self.engine.add_stock("TEST001", "测试股票", 100.0)
        stock = self.engine.get_stock("TEST001")
        
        self.assertIsNotNone(stock)
        self.assertEqual(stock['code'], "TEST001")
        self.assertEqual(stock['current_price'], 100.0)
        
        # 获取不存在的股票
        self.assertIsNone(self.engine.get_stock("INVALID"))
    
    def test_update_price_random_walk(self):
        """测试随机游走价格更新"""
        self.engine.add_stock(
            "TEST001", 
            "测试股票", 
            100.0,
            volatility=0.02,
            drift=0.0,
            model="random_walk"
        )
        
        # 多次更新价格
        prices = []
        for _ in range(100):
            new_price = self.engine.update_price("TEST001")
            prices.append(new_price)
        
        # 检查价格变化
        self.assertTrue(len(set(prices)) > 1)  # 价格应该有变化
        self.assertTrue(all(p > 0 for p in prices))  # 价格应该都为正
    
    def test_update_price_mean_reversion(self):
        """测试均值回归价格更新"""
        self.engine.add_stock(
            "TEST001",
            "测试股票",
            100.0,
            volatility=0.02,
            drift=0.0,
            model="mean_reversion",
            mean_price=100.0,
            reversion_speed=0.5
        )
        
        # 设置一个远离均值的价格
        self.engine.stocks["TEST001"].current_price = 150.0
        
        # 多次更新，价格应该向均值靠拢
        for _ in range(50):
            self.engine.update_price("TEST001")
        
        final_price = self.engine.get_stock("TEST001")['current_price']
        # 价格应该比初始的 150 更接近 100
        self.assertLess(abs(final_price - 100.0), 50.0)
    
    def test_update_price_trend_following(self):
        """测试趋势跟踪价格更新"""
        self.engine.add_stock(
            "TEST001",
            "测试股票",
            100.0,
            volatility=0.01,
            drift=0.002,
            model="trend_following"
        )
        
        # 多次更新价格
        prices = []
        for _ in range(100):
            new_price = self.engine.update_price("TEST001")
            prices.append(new_price)
        
        # 检查是否有趋势（正漂移应该使价格整体上升）
        final_price = prices[-1]
        self.assertGreater(final_price, 95.0)  # 最终价格应该接近或高于初始价格
    
    def test_adjust_volatility(self):
        """测试调整波动率"""
        self.engine.add_stock("TEST001", "测试股票", 100.0, volatility=0.02)
        
        self.engine.adjust_volatility("TEST001", 0.05)
        stock = self.engine.get_stock("TEST001")
        self.assertEqual(stock['volatility'], 0.05)
        
        # 调整负波动率应该被限制为0
        self.engine.adjust_volatility("TEST001", -0.01)
        stock = self.engine.get_stock("TEST001")
        self.assertEqual(stock['volatility'], 0.0)
    
    def test_adjust_drift(self):
        """测试调整漂移"""
        self.engine.add_stock("TEST001", "测试股票", 100.0, drift=0.001)
        
        self.engine.adjust_drift("TEST001", 0.002)
        stock = self.engine.get_stock("TEST001")
        self.assertEqual(stock['drift'], 0.002)
    
    def test_apply_news_sentiment(self):
        """测试应用新闻情绪"""
        self.engine.add_stock("TEST001", "测试股票", 100.0)
        self.engine.set_seed(42)
        
        # 应用积极新闻
        self.engine.apply_news_sentiment("TEST001", 0.5, impact=0.1)
        positive_price = self.engine.update_price("TEST001")
        # 积极新闻应该提升价格
        self.assertGreater(positive_price, 100.0)
        
        # 重置
        self.engine.stocks["TEST001"].current_price = 100.0
        self.engine.set_seed(42)
        
        # 应用消极新闻
        self.engine.apply_news_sentiment("TEST001", -0.5, impact=0.1)
        negative_price = self.engine.update_price("TEST001")
        # 消极新闻应该降低价格
        self.assertLess(negative_price, 100.0)
    
    def test_get_historical_data(self):
        """测试获取历史数据"""
        self.engine.add_stock("TEST001", "测试股票", 100.0)
        
        # 生成一些历史数据
        for _ in range(10):
            self.engine.update_price("TEST001")
        
        # 获取全部历史
        history = self.engine.get_historical_data("TEST001")
        self.assertEqual(len(history), 11)  # 初始价格 + 10次更新
        
        # 获取最近5条
        history_limited = self.engine.get_historical_data("TEST001", limit=5)
        self.assertEqual(len(history_limited), 5)
        
        # 检查数据结构
        for idx, price in history_limited:
            self.assertIsInstance(idx, int)
            self.assertIsInstance(price, float)
            self.assertGreater(price, 0)
    
    def test_get_all_prices(self):
        """测试获取所有股票价格"""
        # 添加多个股票
        self.engine.add_stock("TEST001", "股票1", 100.0)
        self.engine.add_stock("TEST002", "股票2", 200.0)
        self.engine.add_stock("TEST003", "股票3", 300.0)
        
        prices = self.engine.get_all_prices()
        self.assertEqual(len(prices), 3)
        
        # 检查价格数据
        self.assertEqual(prices["TEST001"], 100.0)
        self.assertEqual(prices["TEST002"], 200.0)
        self.assertEqual(prices["TEST003"], 300.0)
    
    def test_batch_generate(self):
        """测试批量生成价格"""
        self.engine.add_stock("TEST001", "股票1", 100.0)
        self.engine.add_stock("TEST002", "股票2", 200.0)
        self.engine.add_stock("TEST003", "股票3", 300.0)
        
        # 批量生成所有股票的新价格
        new_prices = self.engine.batch_generate()
        self.assertEqual(len(new_prices), 3)
        self.assertIn("TEST001", new_prices)
        self.assertIn("TEST002", new_prices)
        self.assertIn("TEST003", new_prices)
        
        # 批量生成指定股票的新价格
        new_prices_partial = self.engine.batch_generate(["TEST001", "TEST002"])
        self.assertEqual(len(new_prices_partial), 2)
        self.assertIn("TEST001", new_prices_partial)
        self.assertIn("TEST002", new_prices_partial)
        self.assertNotIn("TEST003", new_prices_partial)
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        self.engine.add_stock("TEST001", "测试股票", 100.0)
        
        # 生成一些历史数据
        for _ in range(50):
            self.engine.update_price("TEST001")
        
        stats = self.engine.get_statistics("TEST001")
        self.assertIsNotNone(stats)
        self.assertEqual(stats['stock_code'], "TEST001")
        self.assertIn('current_price', stats)
        self.assertIn('min_price', stats)
        self.assertIn('max_price', stats)
        self.assertIn('mean_return', stats)
        self.assertIn('volatility', stats)
        self.assertEqual(stats['count'], 51)  # 初始 + 50次更新
    
    def test_reset_stock(self):
        """测试重置股票"""
        self.engine.add_stock("TEST001", "测试股票", 100.0)
        
        # 更新几次价格
        for _ in range(10):
            self.engine.update_price("TEST001")
        
        # 应用新闻情绪
        self.engine.apply_news_sentiment("TEST001", 0.5)
        
        # 重置
        self.engine.reset_stock("TEST001")
        
        stock = self.engine.get_stock("TEST001")
        self.assertEqual(stock['current_price'], 100.0)
        
        history = self.engine.get_price_history("TEST001")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0], 100.0)


if __name__ == '__main__':
    unittest.main()
