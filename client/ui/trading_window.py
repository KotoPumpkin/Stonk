"""
交易窗口 - Trading Window

功能：K线图/折线图、技术指标、交易下单、持仓列表、资产概览、快讯
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QComboBox, QTextEdit, QSplitter,
    QGroupBox, QHeaderView, QSpinBox, QMessageBox, QSizePolicy,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal

from client.config import COLORS, FONT_FAMILY, FONT_SIZE_NORMAL
from client.ui.chart_widgets import (
    CandlestickChartWidget, LineChartWidget, IndicatorChartWidget,
    TechnicalIndicators, OHLCData, IndicatorData
)


class ModifyOrderDialog(QDialog):
    """修改订单对话框"""

    def __init__(self, order: Dict, parent=None):
        super().__init__(parent)
        self.order = order
        self.setWindowTitle("修改订单")
        self.setMinimumWidth(300)
        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 订单信息展示
        info_label = QLabel(
            f"订单号：{self.order.get('order_id', '')}\n"
            f"股票：{self.order.get('stock_code', '')}  "
            f"方向：{'买入' if self.order.get('side') == 'buy' else '卖出'}"
        )
        info_label.setStyleSheet("color: #aaa; font-size: 11px; padding: 4px;")
        layout.addWidget(info_label)

        form = QFormLayout()
        form.setSpacing(8)

        # 数量
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 10_000_000)
        self.qty_spin.setValue(self.order.get("quantity", 100))
        form.addRow("新数量：", self.qty_spin)

        # 价格
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 1_000_000.0)
        self.price_spin.setDecimals(2)
        self.price_spin.setValue(self.order.get("price", 0.0))
        form.addRow("新价格：", self.price_spin)

        layout.addLayout(form)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认修改")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #1a1a1a;
                color: #e0e0e0;
                font-family: "Microsoft YaHei", "Segoe UI";
            }}
            QLabel {{ color: #e0e0e0; }}
            QSpinBox, QDoubleSpinBox {{
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 4px;
                color: #e0e0e0;
            }}
            QPushButton {{
                background-color: #333;
                border: none;
                border-radius: 3px;
                padding: 6px 16px;
                color: #e0e0e0;
            }}
            QPushButton:hover {{ background-color: #444; }}
        """)

    def get_values(self):
        return self.qty_spin.value(), self.price_spin.value()


class TradingWindow(QWidget):
    """交易窗口"""

    # 信号
    place_order_signal = Signal(str, str, int, float)
    cancel_order_signal = Signal(str)
    modify_order_signal = Signal(str, int, float)   # order_id, new_qty, new_price
    ready_signal = Signal()
    exit_room_requested = Signal()

    def __init__(self, client=None, room_id: str = "", parent=None):
        super().__init__(parent)
        self.client = client
        self.room_id = room_id
        self.current_stock: Optional[str] = None
        self.current_prices: Dict[str, float] = {}
        self.step_mode: str = "day"
        self.current_step: int = 0
        self.initial_capital: float = 100000.0

        # 价格历史 {stock_code: [(timestamp, price), ...]}
        self.price_history: Dict[str, List[Tuple[float, float]]] = {}
        # OHLC 数据 {stock_code: [OHLCData, ...]}
        self.ohlc_history: Dict[str, List[OHLCData]] = {}
        # 订单列表（活跃）
        self.pending_orders: List[Dict] = []

        self._init_ui()
        self._apply_styles()

    # ==================== UI 构建 ====================

    def _init_ui(self):
        self.setWindowTitle("Stonk - 交易")
        self.setMinimumSize(1200, 800)

        root = QVBoxLayout(self)
        root.setSpacing(4)
        root.setContentsMargins(6, 6, 6, 6)

        # 顶部信息栏
        top = QHBoxLayout()
        self.room_label = QLabel("房间：-- | 模式：-- | 步：0")
        self.room_label.setStyleSheet("font-size:14px;font-weight:bold;")
        top.addWidget(self.room_label)
        top.addStretch()
        self.exit_btn = QPushButton("退出房间")
        self.exit_btn.setObjectName("exitBtn")
        self.exit_btn.clicked.connect(self.exit_room_requested.emit)
        top.addWidget(self.exit_btn)
        root.addLayout(top)

        # 中央分割
        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, stretch=1)

        # 左侧：图表区
        splitter.addWidget(self._build_chart_area())
        # 右侧：交易面板
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        # 底部：快讯
        root.addWidget(self._build_news_panel())

    def _build_chart_area(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        # 工具栏
        bar = QHBoxLayout()
        bar.addWidget(QLabel("股票："))
        self.stock_combo = QComboBox()
        self.stock_combo.setMinimumWidth(120)
        self.stock_combo.currentTextChanged.connect(self._on_stock_changed)
        bar.addWidget(self.stock_combo)
        bar.addStretch()
        bar.addWidget(QLabel("图表："))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["K线图", "折线图"])
        self.chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)
        bar.addWidget(self.chart_type_combo)
        lay.addLayout(bar)

        # K线图 & 折线图（互斥显示）
        self.candle_chart = CandlestickChartWidget()
        self.line_chart = LineChartWidget()
        self.line_chart.setVisible(False)
        lay.addWidget(self.candle_chart, stretch=3)
        lay.addWidget(self.line_chart, stretch=3)

        # 指标子图
        self.indicator_chart = IndicatorChartWidget()
        lay.addWidget(self.indicator_chart, stretch=1)

        return w

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self._build_trade_group())
        lay.addWidget(self._build_asset_group())
        lay.addWidget(self._build_position_group(), stretch=1)
        lay.addWidget(self._build_order_group(), stretch=1)
        return w

    # ---------- 交易下单 ----------

    def _build_trade_group(self) -> QGroupBox:
        g = QGroupBox("交易下单")
        lay = QVBoxLayout(g)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("代码："))
        self.trade_code = QLineEdit()
        self.trade_code.setPlaceholderText("如 AAPL")
        self.trade_code.textChanged.connect(self._update_estimate)
        r1.addWidget(self.trade_code)
        lay.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("数量："))
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 1000000)
        self.qty_spin.setValue(100)
        self.qty_spin.valueChanged.connect(self._update_estimate)
        r2.addWidget(self.qty_spin)
        lay.addLayout(r2)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("市价："))
        self.price_label = QLabel("--")
        self.price_label.setObjectName("priceLabel")
        r3.addWidget(self.price_label)
        r3.addStretch()
        lay.addLayout(r3)

        r4 = QHBoxLayout()
        r4.addWidget(QLabel("预估："))
        self.estimate_label = QLabel("--")
        r4.addWidget(self.estimate_label)
        r4.addStretch()
        lay.addLayout(r4)

        btns = QHBoxLayout()
        self.buy_btn = QPushButton("买入")
        self.buy_btn.setObjectName("buyBtn")
        self.buy_btn.clicked.connect(lambda: self._place_order("buy"))
        btns.addWidget(self.buy_btn)
        self.sell_btn = QPushButton("卖出")
        self.sell_btn.setObjectName("sellBtn")
        self.sell_btn.clicked.connect(lambda: self._place_order("sell"))
        btns.addWidget(self.sell_btn)
        lay.addLayout(btns)

        # ── 确认进入下一步（开关样式）──
        self._ready_toggled = False  # 当前是否已确认
        self.ready_btn = QPushButton("○  确认进入下一步")
        self.ready_btn.setObjectName("readyBtnOff")
        self.ready_btn.setEnabled(False)
        self.ready_btn.setCheckable(True)
        self.ready_btn.clicked.connect(self._on_ready_toggle)
        lay.addWidget(self.ready_btn)

        return g

    # ---------- 资产概览 ----------

    def _build_asset_group(self) -> QGroupBox:
        g = QGroupBox("资产概览")
        lay = QVBoxLayout(g)

        def row(label_text):
            r = QHBoxLayout()
            r.addWidget(QLabel(label_text))
            val = QLabel("--")
            r.addWidget(val)
            r.addStretch()
            lay.addLayout(r)
            return val

        self.total_label = row("总资产：")
        self.total_label.setStyleSheet("font-size:16px;font-weight:bold;")
        self.cash_label = row("现  金：")
        self.pl_label = row("盈  亏：")
        self.plp_label = row("盈亏比：")

        return g

    # ---------- 持仓列表 ----------

    def _build_position_group(self) -> QGroupBox:
        g = QGroupBox("持仓列表")
        lay = QVBoxLayout(g)
        self.pos_table = QTableWidget()
        self.pos_table.setColumnCount(6)
        self.pos_table.setHorizontalHeaderLabels(
            ["代码", "数量", "成本价", "现价", "市值", "浮盈"]
        )
        self.pos_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pos_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pos_table.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.pos_table)
        return g

    # ---------- 订单列表 ----------

    def _build_order_group(self) -> QGroupBox:
        g = QGroupBox("我的挂单")
        lay = QVBoxLayout(g)

        # 统计标签
        self.order_count_label = QLabel("共 0 笔活跃订单")
        self.order_count_label.setStyleSheet("color: #888; font-size: 11px;")
        lay.addWidget(self.order_count_label)

        self.order_table = QTableWidget()
        self.order_table.setColumnCount(7)
        self.order_table.setHorizontalHeaderLabels(
            ["订单号", "代码", "方向", "数量", "价格", "修改", "撤单"]
        )
        hdr = self.order_table.horizontalHeader()
        # 订单号列较宽，操作列固定
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.Fixed)
        hdr.setSectionResizeMode(6, QHeaderView.Fixed)
        self.order_table.setColumnWidth(5, 52)
        self.order_table.setColumnWidth(6, 52)
        self.order_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.order_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.order_table.verticalHeader().setDefaultSectionSize(28)
        lay.addWidget(self.order_table)
        return g

    # ---------- 快讯面板 ----------

    def _build_news_panel(self) -> QGroupBox:
        g = QGroupBox("快讯")
        lay = QVBoxLayout(g)
        self.news_text = QTextEdit()
        self.news_text.setReadOnly(True)
        self.news_text.setMaximumHeight(130)
        lay.addWidget(self.news_text)
        return g

    # ==================== 样式 ====================

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                font-family: "{FONT_FAMILY}", "Segoe UI";
                font-size: {FONT_SIZE_NORMAL}px;
            }}
            QGroupBox {{
                border: 1px solid #333;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLineEdit, QSpinBox, QComboBox {{
                background-color: #2a2a2a;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 5px;
            }}
            QPushButton {{
                background-color: #333;
                border: none;
                border-radius: 3px;
                padding: 8px;
                min-width: 60px;
            }}
            QPushButton:hover {{ background-color: #444; }}
            QPushButton:pressed {{ background-color: #222; }}
            QPushButton:disabled {{ background-color: #1a1a1a; color: #666; }}
            #buyBtn {{ background: #00aa00; color: #fff; font-weight: bold; }}
            #buyBtn:hover {{ background: #00cc00; }}
            #sellBtn {{ background: #aa0000; color: #fff; font-weight: bold; }}
            #sellBtn:hover {{ background: #cc0000; }}
            #readyBtnOff {{
                background: #2a2a2a;
                color: #888888;
                border: 2px solid #444444;
                border-radius: 16px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 13px;
                text-align: center;
            }}
            #readyBtnOff:hover {{
                background: #333333;
                border-color: #666666;
                color: #aaaaaa;
            }}
            #readyBtnOff:disabled {{
                background: #1a1a1a;
                color: #444444;
                border-color: #333333;
            }}
            #readyBtnOn {{
                background: #006622;
                color: #00ff88;
                border: 2px solid #00cc55;
                border-radius: 16px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 13px;
                text-align: center;
            }}
            #readyBtnOn:hover {{
                background: #007733;
                border-color: #00ff66;
            }}
            #exitBtn {{ background: #aa0000; color: #fff; font-weight: bold; padding: 6px 16px; }}
            #priceLabel {{ font-weight: bold; color: #00ff00; }}
            QTableWidget {{
                background-color: #2a2a2a;
                border: 1px solid #333;
                gridline-color: #333;
            }}
            QHeaderView::section {{
                background-color: #333;
                padding: 5px;
                border: none;
            }}
            QTextEdit {{
                background-color: #2a2a2a;
                border: 1px solid #333;
                border-radius: 3px;
            }}
        """)

    # ==================== 公共接口 ====================

    def update_room_info(self, name: str, mode: str, step: int):
        """更新房间信息"""
        self.step_mode = mode
        self.current_step = step
        self.room_label.setText(f"房间：{name} | 模式：{mode} | 步：{step}")
        # 秒级模式自动切换折线图
        if mode == "second":
            self.chart_type_combo.setCurrentText("折线图")

    def update_stocks(self, stocks: List[str]):
        """更新股票列表"""
        cur = self.stock_combo.currentText()
        self.stock_combo.clear()
        self.stock_combo.addItems(stocks)
        if cur in stocks:
            self.stock_combo.setCurrentText(cur)
        elif stocks:
            self.stock_combo.setCurrentIndex(0)

    def update_current_prices(self, prices: Dict[str, float]):
        """更新当前价格"""
        self.current_prices = prices
        self._update_estimate()

    def update_price_data(self, stock_code: str, prices: List[Tuple[float, float]]):
        """更新价格历史并刷新图表"""
        self.price_history[stock_code] = prices
        if stock_code == self.current_stock:
            self._refresh_charts()

    def update_ohlc_data(self, stock_code: str, ohlc_list: List[OHLCData]):
        """更新 OHLC 数据并刷新图表"""
        self.ohlc_history[stock_code] = ohlc_list
        if stock_code == self.current_stock:
            self._refresh_charts()

    def append_price(self, stock_code: str, timestamp: float, price: float):
        """追加一个价格点"""
        if stock_code not in self.price_history:
            self.price_history[stock_code] = []
        self.price_history[stock_code].append((timestamp, price))
        if stock_code == self.current_stock:
            self._refresh_charts()

    def append_ohlc(self, stock_code: str, ohlc: OHLCData):
        """追加一根K线"""
        if stock_code not in self.ohlc_history:
            self.ohlc_history[stock_code] = []
        self.ohlc_history[stock_code].append(ohlc)
        if stock_code == self.current_stock:
            self._refresh_charts()

    def update_account(self, data: Dict):
        """更新账户信息和持仓"""
        self.total_label.setText(f"¥{data.get('total_value', 0):.2f}")
        self.cash_label.setText(f"¥{data.get('cash', 0):.2f}")

        pl = data.get('profit_loss', 0)
        plp = data.get('profit_loss_percent', 0)
        color = "#00ff00" if pl >= 0 else "#ff0000"
        sign = "+" if pl >= 0 else ""

        self.pl_label.setText(f"{sign}¥{pl:.2f}")
        self.pl_label.setStyleSheet(f"color:{color};font-weight:bold;")
        self.plp_label.setText(f"{sign}{plp:.2f}%")
        self.plp_label.setStyleSheet(f"color:{color};font-weight:bold;")

        # 持仓表
        positions = data.get('positions', [])
        self.pos_table.setRowCount(0)
        for i, pos in enumerate(positions):
            self.pos_table.insertRow(i)
            self.pos_table.setItem(i, 0, QTableWidgetItem(pos.get('stock_code', '')))
            self.pos_table.setItem(i, 1, QTableWidgetItem(str(pos.get('quantity', 0))))
            self.pos_table.setItem(i, 2, QTableWidgetItem(f"¥{pos.get('cost_basis', 0):.2f}"))
            self.pos_table.setItem(i, 3, QTableWidgetItem(f"¥{pos.get('current_price', 0):.2f}"))
            self.pos_table.setItem(i, 4, QTableWidgetItem(f"¥{pos.get('market_value', 0):.2f}"))
            pnl = pos.get('profit_loss', 0)
            item = QTableWidgetItem(f"¥{pnl:.2f}")
            item.setForeground(Qt.green if pnl >= 0 else Qt.red)
            self.pos_table.setItem(i, 5, item)

    def update_orders(self, orders: List[Dict]):
        """更新活跃订单列表"""
        self.pending_orders = orders
        self.order_table.setRowCount(0)

        active = [o for o in orders if o.get("status") in ("pending", "partial")]
        self.order_count_label.setText(f"共 {len(active)} 笔活跃订单")

        for i, order in enumerate(active):
            self.order_table.insertRow(i)
            oid = order.get('order_id', '')

            # 订单号（截短显示）
            oid_item = QTableWidgetItem(oid[-8:] if len(oid) > 8 else oid)
            oid_item.setToolTip(oid)
            self.order_table.setItem(i, 0, oid_item)

            self.order_table.setItem(i, 1, QTableWidgetItem(order.get('stock_code', '')))

            side = order.get('side', '')
            side_item = QTableWidgetItem("买入" if side == "buy" else "卖出")
            side_item.setForeground(Qt.green if side == "buy" else Qt.red)
            self.order_table.setItem(i, 2, side_item)

            self.order_table.setItem(i, 3, QTableWidgetItem(str(order.get('quantity', 0))))
            self.order_table.setItem(i, 4, QTableWidgetItem(f"¥{order.get('price', 0):.2f}"))

            # 修改按钮
            modify_btn = QPushButton("修改")
            modify_btn.setStyleSheet(
                "background:#005599;color:#fff;padding:2px 4px;"
                "font-size:11px;border-radius:2px;"
            )
            modify_btn.clicked.connect(
                lambda checked, o=order: self._show_modify_dialog(o)
            )
            self.order_table.setCellWidget(i, 5, modify_btn)

            # 撤单按钮
            cancel_btn = QPushButton("撤单")
            cancel_btn.setStyleSheet(
                "background:#aa0000;color:#fff;padding:2px 4px;"
                "font-size:11px;border-radius:2px;"
            )
            cancel_btn.clicked.connect(
                lambda checked, o=oid: self._confirm_cancel(o)
            )
            self.order_table.setCellWidget(i, 6, cancel_btn)

    def add_news(self, title: str, content: str, timestamp: float):
        """添加快讯"""
        dt = datetime.fromtimestamp(timestamp)
        ts = dt.strftime("%Y-%m-%d %H:%M:%S")
        html = (
            f"<div style='border-bottom:1px solid #333;padding:4px;margin-bottom:4px;'>"
            f"<b style='color:#00aaff;'>[{ts}] {title}</b><br/>"
            f"<span style='color:#ccc;'>{content}</span></div>"
        )
        self.news_text.append(html)

    def set_decision_mode(self, enabled: bool):
        """设置决策模式"""
        self.buy_btn.setEnabled(enabled)
        self.sell_btn.setEnabled(enabled)
        self.ready_btn.setEnabled(enabled)
        if enabled:
            # 进入决策期：重置为未确认状态
            self._ready_toggled = False
            self.ready_btn.setChecked(False)
            self.ready_btn.setObjectName("readyBtnOff")
            self.ready_btn.setText("○  确认进入下一步")
            self.ready_btn.setStyleSheet("")  # 触发样式刷新
            self._refresh_ready_btn_style()
        else:
            self.ready_btn.setText("⏳ 等待中...")
            self.ready_btn.setChecked(False)
            self._ready_toggled = False

    def set_fast_forward_mode(self, enabled: bool):
        """快进模式：禁用所有交易操作"""
        self.buy_btn.setEnabled(not enabled)
        self.sell_btn.setEnabled(not enabled)
        self.ready_btn.setEnabled(not enabled)
        self.trade_code.setEnabled(not enabled)
        self.qty_spin.setEnabled(not enabled)
        if enabled:
            self.ready_btn.setText("⏩ 快进中...")
            self._ready_toggled = False
            self.ready_btn.setChecked(False)

    # ==================== 内部方法 ====================

    def _on_ready_toggle(self, checked: bool):
        """处理确认按钮点击（开关切换）"""
        if checked and not self._ready_toggled:
            # 切换到已确认状态
            self._ready_toggled = True
            self.ready_btn.setObjectName("readyBtnOn")
            self.ready_btn.setText("✅ 已确认  （点击取消）")
            self._refresh_ready_btn_style()
            self.ready_signal.emit()
        elif not checked and self._ready_toggled:
            # 切换回未确认状态（取消确认）
            self._ready_toggled = False
            self.ready_btn.setObjectName("readyBtnOff")
            self.ready_btn.setText("○  确认进入下一步")
            self._refresh_ready_btn_style()
            # 注意：取消确认不发送信号（服务器端不支持取消就绪）

    def _refresh_ready_btn_style(self):
        """强制刷新 ready_btn 的样式（objectName 变更后需要重新 polish）"""
        self.ready_btn.style().unpolish(self.ready_btn)
        self.ready_btn.style().polish(self.ready_btn)
        self.ready_btn.update()

    def _on_stock_changed(self, stock_code: str):
        self.current_stock = stock_code
        self.trade_code.setText(stock_code)
        self._refresh_charts()
        self._update_estimate()

    def _on_chart_type_changed(self, chart_type: str):
        is_candle = (chart_type == "K线图")
        self.candle_chart.setVisible(is_candle)
        self.line_chart.setVisible(not is_candle)

    def _update_estimate(self):
        code = self.trade_code.text().strip()
        price = self.current_prices.get(code, 0)
        if price > 0:
            self.price_label.setText(f"¥{price:.2f}")
            total = price * self.qty_spin.value()
            self.estimate_label.setText(f"¥{total:.2f}")
        else:
            self.price_label.setText("--")
            self.estimate_label.setText("--")

    def _place_order(self, side: str):
        code = self.trade_code.text().strip()
        if not code:
            QMessageBox.warning(self, "提示", "请输入股票代码")
            return
        qty = self.qty_spin.value()
        price = self.current_prices.get(code, 0)
        if price <= 0:
            QMessageBox.warning(self, "提示", f"无法获取 {code} 的当前价格")
            return
        self.place_order_signal.emit(code, side, qty, price)

    def _confirm_cancel(self, order_id: str):
        """确认撤单"""
        reply = QMessageBox.question(
            self, "确认撤单",
            f"确定要撤销订单 {order_id[-8:]} 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.cancel_order_signal.emit(order_id)

    def _show_modify_dialog(self, order: Dict):
        """弹出修改订单对话框"""
        dlg = ModifyOrderDialog(order, self)
        if dlg.exec() == QDialog.Accepted:
            new_qty, new_price = dlg.get_values()
            self.modify_order_signal.emit(order.get("order_id", ""), new_qty, new_price)

    def _refresh_charts(self):
        """刷新当前股票的所有图表"""
        code = self.current_stock
        if not code:
            return

        # 折线图
        if code in self.price_history:
            self.line_chart.update_data(self.price_history[code])

        # K线图
        if code in self.ohlc_history:
            self.candle_chart.update_data(self.ohlc_history[code])

        # 计算并更新指标
        self._refresh_indicators(code)

    def _refresh_indicators(self, code: str):
        """计算并刷新技术指标"""
        # 优先使用 OHLC 数据
        if code in self.ohlc_history and self.ohlc_history[code]:
            ohlc = self.ohlc_history[code]
            closes = [d.close_price for d in ohlc]
            highs = [d.high_price for d in ohlc]
            lows = [d.low_price for d in ohlc]
        elif code in self.price_history and self.price_history[code]:
            prices = [p for _, p in self.price_history[code]]
            closes = prices
            highs = prices
            lows = prices
        else:
            return

        if len(closes) < 2:
            return

        data = IndicatorData()

        # MACD
        dif, dea, hist = TechnicalIndicators.compute_macd(closes)
        data.macd_line = dif
        data.signal_line = dea
        data.macd_histogram = hist

        # KDJ
        k, d, j = TechnicalIndicators.compute_kdj(highs, lows, closes)
        data.kdj_k = k
        data.kdj_d = d
        data.kdj_j = j

        # RSI
        data.rsi = TechnicalIndicators.compute_rsi(closes)

        display_n = min(120, len(closes))
        self.indicator_chart.update_indicators(data, display_n)

    # ==================== 兼容旧接口 ====================

    def update_price_chart(self, stock_code: str, price_data: List[Dict]):
        """兼容旧接口：更新价格图表"""
        if stock_code != self.current_stock:
            return
        converted = [(p["timestamp"], p["price"]) for p in price_data]
        self.update_price_data(stock_code, converted)
