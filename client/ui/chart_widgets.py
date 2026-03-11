"""
图表组件模块 - Chart Widgets

包含：
- K线图组件 (CandlestickChartWidget)
- 折线图组件 (LineChartWidget)
- 技术指标子图 (IndicatorChartWidget)
- 技术指标计算器 (TechnicalIndicators)
- 数据结构 (OHLCData, IndicatorData)
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCharts import (
    QChart, QChartView, QLineSeries, QValueAxis,
    QCandlestickSeries, QCandlestickSet, QBarCategoryAxis
)

from shared.constants import MACD_FAST, MACD_SLOW, MACD_SIGNAL, KDJ_PERIOD, RSI_PERIOD


# ==================== 数据结构 ====================

@dataclass
class OHLCData:
    """K线数据"""
    timestamp: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int = 0


@dataclass
class IndicatorData:
    """技术指标数据"""
    macd_line: List[float] = field(default_factory=list)
    signal_line: List[float] = field(default_factory=list)
    macd_histogram: List[float] = field(default_factory=list)
    kdj_k: List[float] = field(default_factory=list)
    kdj_d: List[float] = field(default_factory=list)
    kdj_j: List[float] = field(default_factory=list)
    rsi: List[float] = field(default_factory=list)


# ==================== 技术指标计算 ====================

class TechnicalIndicators:
    """技术指标计算器"""

    @staticmethod
    def compute_ema(prices: List[float], period: int) -> List[float]:
        if not prices or period <= 0:
            return []
        ema = [prices[0]]
        k = 2.0 / (period + 1)
        for i in range(1, len(prices)):
            ema.append(prices[i] * k + ema[-1] * (1 - k))
        return ema

    @staticmethod
    def compute_sma(prices: List[float], period: int) -> List[float]:
        if not prices or period <= 0:
            return []
        result = []
        for i in range(len(prices)):
            start = max(0, i - period + 1)
            result.append(sum(prices[start:i + 1]) / (i - start + 1))
        return result

    @staticmethod
    def compute_macd(prices, fast=MACD_FAST, slow=MACD_SLOW, sig=MACD_SIGNAL):
        if len(prices) < slow:
            return [], [], []
        ef = TechnicalIndicators.compute_ema(prices, fast)
        es = TechnicalIndicators.compute_ema(prices, slow)
        dif = [a - b for a, b in zip(ef, es)]
        dea = TechnicalIndicators.compute_ema(dif, sig)
        hist = [2 * (a - b) for a, b in zip(dif, dea)]
        return dif, dea, hist

    @staticmethod
    def compute_kdj(highs, lows, closes, period=KDJ_PERIOD):
        n = len(closes)
        if n < period:
            return [], [], []
        kv, dv, jv = [], [], []
        pk, pd = 50.0, 50.0
        for i in range(n):
            s = max(0, i - period + 1)
            wh = max(highs[s:i + 1])
            wl = min(lows[s:i + 1])
            rsv = 50.0 if wh == wl else (closes[i] - wl) / (wh - wl) * 100
            k = 2 / 3 * pk + 1 / 3 * rsv
            d = 2 / 3 * pd + 1 / 3 * k
            kv.append(k)
            dv.append(d)
            jv.append(3 * k - 2 * d)
            pk, pd = k, d
        return kv, dv, jv

    @staticmethod
    def compute_rsi(prices, period=RSI_PERIOD):
        if len(prices) < period + 1:
            return []
        result = []
        gains, losses = [], []
        for i in range(1, len(prices)):
            c = prices[i] - prices[i - 1]
            gains.append(max(0, c))
            losses.append(max(0, -c))
        ag = sum(gains[:period]) / period
        al = sum(losses[:period]) / period
        for _ in range(period):
            result.append(50.0)
        result.append(100.0 if al == 0 else 100 - 100 / (1 + ag / al))
        for i in range(period, len(gains)):
            ag = (ag * (period - 1) + gains[i]) / period
            al = (al * (period - 1) + losses[i]) / period
            result.append(100.0 if al == 0 else 100 - 100 / (1 + ag / al))
        return result


# ==================== 图表样式 ====================

_BG = QColor("#1a1a1a")
_TEXT = QColor("#cccccc")
_GRID = QColor("#333333")
_BULL = QColor("#ff4444")
_BEAR = QColor("#00cc66")
_LINE = QColor("#00aaff")


def _style_chart(chart: QChart):
    chart.setBackgroundBrush(QBrush(_BG))
    chart.setTitleBrush(QBrush(_TEXT))
    chart.legend().setLabelColor(_TEXT)
    chart.setAnimationOptions(QChart.NoAnimation)
    chart.legend().setVisible(True)
    chart.legend().setAlignment(Qt.AlignTop)


def _style_axis(axis):
    axis.setLabelsColor(_TEXT)
    axis.setTitleBrush(QBrush(_TEXT))
    axis.setGridLineColor(_GRID)
    axis.setLinePenColor(_GRID)


# ==================== K线图 ====================

class CandlestickChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[OHLCData] = []
        self._max = 120
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.chart = QChart()
        self.chart.setTitle("K 线图")
        _style_chart(self.chart)

        self.candles = QCandlestickSeries()
        self.candles.setName("价格")
        self.candles.setIncreasingColor(_BULL)
        self.candles.setDecreasingColor(_BEAR)
        self.candles.setBodyWidth(0.7)
        self.chart.addSeries(self.candles)

        self.ma5 = QLineSeries()
        self.ma5.setName("MA5")
        self.ma5.setPen(QPen(QColor("#ffaa00"), 1))
        self.chart.addSeries(self.ma5)

        self.ma10 = QLineSeries()
        self.ma10.setName("MA10")
        self.ma10.setPen(QPen(QColor("#00aaff"), 1))
        self.chart.addSeries(self.ma10)

        self.ma20 = QLineSeries()
        self.ma20.setName("MA20")
        self.ma20.setPen(QPen(QColor("#ff55ff"), 1))
        self.chart.addSeries(self.ma20)

        self.ax = QBarCategoryAxis()
        _style_axis(self.ax)
        self.ax.setLabelsAngle(-45)
        self.chart.addAxis(self.ax, Qt.AlignBottom)

        self.ay = QValueAxis()
        self.ay.setTitleText("价格")
        _style_axis(self.ay)
        self.chart.addAxis(self.ay, Qt.AlignLeft)

        for s in [self.candles, self.ma5, self.ma10, self.ma20]:
            s.attachAxis(self.ax)
            s.attachAxis(self.ay)

        view = QChartView(self.chart)
        view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(view)

    def update_data(self, data: List[OHLCData]):
        self._data = data
        self._refresh()

    def append_data(self, d: OHLCData):
        self._data.append(d)
        self._refresh()

    def _refresh(self):
        disp = self._data[-self._max:]
        if not disp:
            return
        self.candles.clear()
        self.ma5.clear()
        self.ma10.clear()
        self.ma20.clear()

        closes = [d.close_price for d in self._data]
        m5 = TechnicalIndicators.compute_sma(closes, 5)
        m10 = TechnicalIndicators.compute_sma(closes, 10)
        m20 = TechnicalIndicators.compute_sma(closes, 20)
        off = len(self._data) - len(disp)
        cats = []
        lo, hi = float('inf'), float('-inf')

        for i, o in enumerate(disp):
            g = off + i
            cats.append(datetime.fromtimestamp(o.timestamp).strftime("%m-%d %H:%M"))
            cs = QCandlestickSet(o.open_price, o.high_price, o.low_price, o.close_price)
            cs.setTimestamp(float(i))
            self.candles.append(cs)
            lo = min(lo, o.low_price)
            hi = max(hi, o.high_price)
            if g < len(m5):
                self.ma5.append(i, m5[g])
            if g < len(m10):
                self.ma10.append(i, m10[g])
            if g < len(m20):
                self.ma20.append(i, m20[g])

        self.ax.clear()
        self.ax.append(cats)
        p = (hi - lo) * 0.05 if hi > lo else 1.0
        self.ay.setRange(lo - p, hi + p)


# ==================== 折线图 ====================

class LineChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._prices: List[Tuple[float, float]] = []
        self._max = 300
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.chart = QChart()
        self.chart.setTitle("价格走势")
        _style_chart(self.chart)

        self.series = QLineSeries()
        self.series.setName("价格")
        self.series.setPen(QPen(_LINE, 2))
        self.chart.addSeries(self.series)

        self.ax = QValueAxis()
        self.ax.setTitleText("时间步")
        _style_axis(self.ax)
        self.chart.addAxis(self.ax, Qt.AlignBottom)
        self.series.attachAxis(self.ax)

        self.ay = QValueAxis()
        self.ay.setTitleText("价格")
        _style_axis(self.ay)
        self.chart.addAxis(self.ay, Qt.AlignLeft)
        self.series.attachAxis(self.ay)

        view = QChartView(self.chart)
        view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(view)

    def update_data(self, data: List[Tuple[float, float]]):
        self._prices = data
        self._refresh()

    def append_data(self, ts: float, price: float):
        self._prices.append((ts, price))
        self._refresh()

    def _refresh(self):
        d = self._prices[-self._max:]
        if not d:
            return
        self.series.clear()
        vals = []
        for i, (_, p) in enumerate(d):
            self.series.append(i, p)
            vals.append(p)
        self.ax.setRange(0, max(1, len(d) - 1))
        if vals:
            mn, mx = min(vals), max(vals)
            p = (mx - mn) * 0.05 if mx > mn else 1.0
            self.ay.setRange(mn - p, mx + p)


# ==================== 指标图 ====================

class IndicatorChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cur = "MACD"
        self._data = IndicatorData()
        self._n = 120
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        bl = QHBoxLayout()
        bl.setSpacing(4)
        sty = ("QPushButton{background:#333;color:#ccc;border:none;"
               "border-radius:3px;padding:2px 10px;font-size:11px}"
               "QPushButton:hover{background:#444}"
               "QPushButton:checked{background:#00aaff;color:#000}")
        self.bm = QPushButton("MACD")
        self.bk = QPushButton("KDJ")
        self.br = QPushButton("RSI")
        for b in [self.bm, self.bk, self.br]:
            b.setFixedHeight(24)
            b.setCheckable(True)
            b.setStyleSheet(sty)
        self.bm.setChecked(True)
        self.bm.clicked.connect(lambda: self._sw("MACD"))
        self.bk.clicked.connect(lambda: self._sw("KDJ"))
        self.br.clicked.connect(lambda: self._sw("RSI"))
        bl.addWidget(self.bm)
        bl.addWidget(self.bk)
        bl.addWidget(self.br)
        bl.addStretch()
        layout.addLayout(bl)

        self.chart = QChart()
        _style_chart(self.chart)
        self.chart.setTitle("")
        self._ax = QValueAxis()
        _style_axis(self._ax)
        self._ax.setLabelsVisible(False)
        self.chart.addAxis(self._ax, Qt.AlignBottom)
        self._ay = QValueAxis()
        _style_axis(self._ay)
        self.chart.addAxis(self._ay, Qt.AlignLeft)

        v = QChartView(self.chart)
        v.setRenderHint(QPainter.Antialiasing)
        v.setMinimumHeight(150)
        layout.addWidget(v, stretch=1)

    def _sw(self, name):
        self._cur = name
        self.bm.setChecked(name == "MACD")
        self.bk.setChecked(name == "KDJ")
        self.br.setChecked(name == "RSI")
        self._refresh()

    def update_indicators(self, data: IndicatorData, n: int = 120):
        self._data = data
        self._n = n
        self._refresh()

    def _refresh(self):
        self.chart.removeAllSeries()
        if self._cur == "MACD":
            self._macd()
        elif self._cur == "KDJ":
            self._kdj()
        else:
            self._rsi()

    def _line(self, name, color, vals):
        s = QLineSeries()
        s.setName(name)
        s.setPen(QPen(QColor(color), 1.5))
        for i, v in enumerate(vals):
            s.append(i, v)
        self.chart.addSeries(s)
        s.attachAxis(self._ax)
        s.attachAxis(self._ay)

    def _rng(self, cnt, vals):
        self._ax.setRange(0, max(1, cnt - 1))
        if vals:
            mn, mx = min(vals), max(vals)
            p = (mx - mn) * 0.1 if mx > mn else 1.0
            self._ay.setRange(mn - p, mx + p)

    def _macd(self):
        d = self._data
        n = self._n
        dif = d.macd_line[-n:] if d.macd_line else []
        dea = d.signal_line[-n:] if d.signal_line else []
        h = d.macd_histogram[-n:] if d.macd_histogram else []
        if not dif:
            return
        self._line("DIF", "#ffaa00", dif)
        self._line("DEA", "#00aaff", dea)
        self._line("MACD+", "#ff4444", [v if v >= 0 else 0 for v in h])
        self._line("MACD-", "#00cc66", [v if v < 0 else 0 for v in h])
        self._rng(len(dif), dif + dea + h)

    def _kdj(self):
        d = self._data
        n = self._n
        k = d.kdj_k[-n:] if d.kdj_k else []
        dv = d.kdj_d[-n:] if d.kdj_d else []
        j = d.kdj_j[-n:] if d.kdj_j else []
        if not k:
            return
        self._line("K", "#ffaa00", k)
        self._line("D", "#00aaff", dv)
        self._line("J", "#ff55ff", j)
        self._rng(len(k), k + dv + j)

    def _rsi(self):
        d = self._data
        n = self._n
        r = d.rsi[-n:] if d.rsi else []
        if not r:
            return
        self._line("RSI", "#ffaa00", r)
        self._line("超买(80)", "#ff4444", [80.0] * len(r))
        self._line("超卖(20)", "#00cc66", [20.0] * len(r))
        self._rng(len(r), r + [20, 80])
