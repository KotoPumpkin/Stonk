"""
图表组件和技术指标测试
"""

import unittest
import math
from client.ui.chart_widgets import (
    TechnicalIndicators, OHLCData, IndicatorData
)


class TestTechnicalIndicators(unittest.TestCase):
    """技术指标计算测试"""

    def test_compute_ema_basic(self):
        """EMA 基本计算"""
        prices = [10, 11, 12, 13, 14, 15]
        ema = TechnicalIndicators.compute_ema(prices, 3)
        self.assertEqual(len(ema), len(prices))
        self.assertEqual(ema[0], 10)  # 第一个值等于第一个价格
        # EMA 应该跟随价格上升
        for i in range(1, len(ema)):
            self.assertGreater(ema[i], ema[i - 1])

    def test_compute_ema_empty(self):
        """EMA 空输入"""
        self.assertEqual(TechnicalIndicators.compute_ema([], 3), [])
        self.assertEqual(TechnicalIndicators.compute_ema([1, 2], 0), [])

    def test_compute_sma_basic(self):
        """SMA 基本计算"""
        prices = [10, 20, 30, 40, 50]
        sma = TechnicalIndicators.compute_sma(prices, 3)
        self.assertEqual(len(sma), len(prices))
        # SMA(3) 的第3个值 = (10+20+30)/3 = 20
        self.assertAlmostEqual(sma[2], 20.0)
        # SMA(3) 的第4个值 = (20+30+40)/3 = 30
        self.assertAlmostEqual(sma[3], 30.0)
        # SMA(3) 的第5个值 = (30+40+50)/3 = 40
        self.assertAlmostEqual(sma[4], 40.0)

    def test_compute_sma_empty(self):
        """SMA 空输入"""
        self.assertEqual(TechnicalIndicators.compute_sma([], 3), [])

    def test_compute_macd_basic(self):
        """MACD 基本计算"""
        # 生成足够长的价格序列
        prices = [100 + i * 0.5 for i in range(50)]
        dif, dea, hist = TechnicalIndicators.compute_macd(prices, fast=12, slow=26, sig=9)
        self.assertEqual(len(dif), len(prices))
        self.assertEqual(len(dea), len(prices))
        self.assertEqual(len(hist), len(prices))
        # 上升趋势中 DIF 应该为正
        self.assertGreater(dif[-1], 0)

    def test_compute_macd_insufficient_data(self):
        """MACD 数据不足"""
        prices = [10, 11, 12]
        dif, dea, hist = TechnicalIndicators.compute_macd(prices)
        self.assertEqual(dif, [])
        self.assertEqual(dea, [])
        self.assertEqual(hist, [])

    def test_compute_kdj_basic(self):
        """KDJ 基本计算"""
        n = 30
        highs = [100 + i + 2 for i in range(n)]
        lows = [100 + i - 2 for i in range(n)]
        closes = [100 + i for i in range(n)]
        k, d, j = TechnicalIndicators.compute_kdj(highs, lows, closes, period=14)
        self.assertEqual(len(k), n)
        self.assertEqual(len(d), n)
        self.assertEqual(len(j), n)
        # K 和 D 应该在 0-100 范围附近
        for val in k:
            self.assertGreaterEqual(val, -50)
            self.assertLessEqual(val, 150)

    def test_compute_kdj_insufficient_data(self):
        """KDJ 数据不足"""
        k, d, j = TechnicalIndicators.compute_kdj([1], [1], [1], period=14)
        self.assertEqual(k, [])

    def test_compute_kdj_flat_prices(self):
        """KDJ 平价（高低相同）"""
        n = 20
        highs = [100.0] * n
        lows = [100.0] * n
        closes = [100.0] * n
        k, d, j = TechnicalIndicators.compute_kdj(highs, lows, closes, period=14)
        self.assertEqual(len(k), n)
        # 平价时 RSV=50，K 和 D 应趋向 50
        self.assertAlmostEqual(k[-1], 50.0, places=0)

    def test_compute_rsi_basic(self):
        """RSI 基本计算"""
        # 上升趋势
        prices = [100 + i for i in range(30)]
        rsi = TechnicalIndicators.compute_rsi(prices, period=14)
        self.assertGreater(len(rsi), 0)
        # 持续上涨 RSI 应接近 100
        self.assertGreater(rsi[-1], 80)

    def test_compute_rsi_downtrend(self):
        """RSI 下降趋势"""
        prices = [100 - i for i in range(30)]
        rsi = TechnicalIndicators.compute_rsi(prices, period=14)
        self.assertGreater(len(rsi), 0)
        # 持续下跌 RSI 应接近 0
        self.assertLess(rsi[-1], 20)

    def test_compute_rsi_insufficient_data(self):
        """RSI 数据不足"""
        rsi = TechnicalIndicators.compute_rsi([10, 11], period=14)
        self.assertEqual(rsi, [])

    def test_compute_rsi_flat(self):
        """RSI 平价"""
        prices = [100.0] * 30
        rsi = TechnicalIndicators.compute_rsi(prices, period=14)
        # 无变化时 avg_gain=0, avg_loss=0，avg_loss==0 返回 100
        # 前 period 个填充值为 50
        if rsi:
            self.assertAlmostEqual(rsi[13], 50.0, places=0)  # 填充值
            self.assertAlmostEqual(rsi[-1], 100.0, places=0)  # 无损失=100


class TestOHLCData(unittest.TestCase):
    """OHLC 数据结构测试"""

    def test_create_ohlc(self):
        """创建 OHLC 数据"""
        ohlc = OHLCData(
            timestamp=1000.0,
            open_price=100.0,
            high_price=110.0,
            low_price=95.0,
            close_price=105.0,
            volume=1000
        )
        self.assertEqual(ohlc.timestamp, 1000.0)
        self.assertEqual(ohlc.open_price, 100.0)
        self.assertEqual(ohlc.high_price, 110.0)
        self.assertEqual(ohlc.low_price, 95.0)
        self.assertEqual(ohlc.close_price, 105.0)
        self.assertEqual(ohlc.volume, 1000)

    def test_ohlc_default_volume(self):
        """OHLC 默认成交量"""
        ohlc = OHLCData(1000.0, 100.0, 110.0, 95.0, 105.0)
        self.assertEqual(ohlc.volume, 0)


class TestIndicatorData(unittest.TestCase):
    """指标数据结构测试"""

    def test_create_empty(self):
        """创建空指标数据"""
        data = IndicatorData()
        self.assertEqual(data.macd_line, [])
        self.assertEqual(data.signal_line, [])
        self.assertEqual(data.macd_histogram, [])
        self.assertEqual(data.kdj_k, [])
        self.assertEqual(data.kdj_d, [])
        self.assertEqual(data.kdj_j, [])
        self.assertEqual(data.rsi, [])

    def test_create_with_data(self):
        """创建带数据的指标"""
        data = IndicatorData(
            macd_line=[1.0, 2.0],
            signal_line=[0.5, 1.5],
            macd_histogram=[0.5, 0.5]
        )
        self.assertEqual(len(data.macd_line), 2)
        self.assertEqual(len(data.signal_line), 2)


class TestIndicatorIntegration(unittest.TestCase):
    """指标集成测试"""

    def _generate_prices(self, n=100, base=100, trend=0.5, noise=2.0):
        """生成模拟价格序列"""
        import random
        random.seed(42)
        prices = [base]
        for i in range(1, n):
            change = trend + random.gauss(0, noise)
            prices.append(max(1, prices[-1] + change))
        return prices

    def test_full_indicator_pipeline(self):
        """完整指标计算流水线"""
        prices = self._generate_prices(100)
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]

        # MACD
        dif, dea, hist = TechnicalIndicators.compute_macd(prices)
        self.assertEqual(len(dif), 100)

        # KDJ
        k, d, j = TechnicalIndicators.compute_kdj(highs, lows, prices)
        self.assertEqual(len(k), 100)

        # RSI
        rsi = TechnicalIndicators.compute_rsi(prices)
        self.assertGreater(len(rsi), 0)

        # 构建 IndicatorData
        data = IndicatorData(
            macd_line=dif, signal_line=dea, macd_histogram=hist,
            kdj_k=k, kdj_d=d, kdj_j=j, rsi=rsi
        )
        self.assertIsNotNone(data)

    def test_sma_matches_manual(self):
        """SMA 手动验证"""
        prices = [2, 4, 6, 8, 10]
        sma = TechnicalIndicators.compute_sma(prices, 3)
        # sma[2] = (2+4+6)/3 = 4
        self.assertAlmostEqual(sma[2], 4.0)
        # sma[3] = (4+6+8)/3 = 6
        self.assertAlmostEqual(sma[3], 6.0)
        # sma[4] = (6+8+10)/3 = 8
        self.assertAlmostEqual(sma[4], 8.0)

    def test_ema_convergence(self):
        """EMA 收敛性：常数序列的 EMA 应等于该常数"""
        prices = [50.0] * 100
        ema = TechnicalIndicators.compute_ema(prices, 10)
        self.assertAlmostEqual(ema[-1], 50.0, places=5)

    def test_macd_zero_for_constant(self):
        """常数价格的 MACD 应趋近于 0"""
        prices = [100.0] * 50
        dif, dea, hist = TechnicalIndicators.compute_macd(prices)
        if dif:
            self.assertAlmostEqual(dif[-1], 0.0, places=5)
            self.assertAlmostEqual(hist[-1], 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
