"""
Stonk - 管理员 UI 模块

PySide6 管理员界面，支持：
- 多标签页房间管理
- 步进控制（下一步、快进、暂停）
- 股票参数干预
- 新闻发布器
- 财报发布器
- 机器人管理
- 股票管理（CRUD）
"""

import sys
import os

# 确保项目根目录在 sys.path 中，支持直接运行此文件
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncio
import json
import websockets
from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QSplitter, QGridLayout, QDialog, QInputDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont

import logging

from shared.message_protocol import MessageType, create_message, parse_message
from shared.utils import get_timestamp
from shared.constants import SERVER_CONNECT_HOST, SERVER_PORT
from server.config import PORT

# 管理员 UI 应使用 SERVER_CONNECT_HOST (127.0.0.1) 连接服务器，而不是 HOST (0.0.0.0)
HOST = SERVER_CONNECT_HOST

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebSocketClientThread(QThread):
    """WebSocket 客户端线程，用于与服务器通信"""
    
    connected_signal = Signal()
    disconnected_signal = Signal()
    message_received_signal = Signal(dict)
    error_signal = Signal(str)
    
    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port
        self.websocket = None
        self.running = True
        self._message_queue = []
        
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._connect_and_listen(loop))
        
    async def _connect_and_listen(self, loop):
        uri = f"ws://{self.host}:{self.port}"
        logger.info(f"Connecting to {uri}...")
        try:
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                logger.info(f"Connected to server at {uri}")
                self.connected_signal.emit()
                
                send_task = asyncio.create_task(self._process_send_queue(loop))
                
                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                        parsed = parse_message(message)
                        self.message_received_signal.emit(parsed)
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("Connection closed by server")
                        break
                        
                send_task.cancel()
                        
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.error_signal.emit(f"连接失败：{str(e)}")
            
    async def _process_send_queue(self, loop):
        while self.running:
            if self._message_queue:
                msg_str = self._message_queue.pop(0)
                try:
                    await self.websocket.send(msg_str)
                except Exception as e:
                    logger.error(f"Send failed: {e}")
                    self.error_signal.emit(f"发送失败：{str(e)}")
            await asyncio.sleep(0.01)
            
    def send_message(self, message):
        if isinstance(message, str):
            self._message_queue.append(message)
        elif isinstance(message, dict):
            self._message_queue.append(json.dumps(message))
        else:
            self._message_queue.append(str(message))
            
    def stop(self):
        self.running = False


class NewsPublisher(QWidget):
    """新闻发布器组件"""
    
    publish_news_signal = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_rooms: Dict[str, str] = {}  # room_id -> room_name
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title_label = QLabel("📰 新闻发布器")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 8px;")
        layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        
        # 房间选择下拉框
        self.room_combo = QComboBox()
        self.room_combo.addItem("-- 请选择房间 --", "")
        self.room_combo.setStyleSheet("QComboBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("目标房间:", self.room_combo)
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("输入新闻标题...")
        self.title_edit.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 8px; }")
        form_layout.addRow("标题:", self.title_edit)
        
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("输入新闻详细内容...")
        self.content_edit.setMaximumHeight(100)
        self.content_edit.setStyleSheet("QTextEdit { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 8px; }")
        form_layout.addRow("内容:", self.content_edit)
        
        self.sentiment_combo = QComboBox()
        self.sentiment_combo.addItems(["积极", "中立", "消极"])
        self.sentiment_combo.setStyleSheet("QComboBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("情绪:", self.sentiment_combo)
        
        self.scope_edit = QLineEdit()
        self.scope_edit.setPlaceholderText("股票代码，多个用逗号分隔（留空表示房间内全局）")
        self.scope_edit.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 8px; }")
        form_layout.addRow("影响股票:", self.scope_edit)
        
        layout.addLayout(form_layout)
        
        self.publish_button = QPushButton("📢 发布新闻")
        self.publish_button.setStyleSheet("QPushButton { background-color: #2d7d2d; color: #ffffff; border: none; border-radius: 4px; padding: 12px 24px; font-weight: bold; font-size: 13px; } QPushButton:hover { background-color: #3d8d3d; }")
        self.publish_button.clicked.connect(self.on_publish_clicked)
        layout.addWidget(self.publish_button)
        layout.addStretch()
        
    def update_rooms(self, rooms: Dict[str, str]):
        """更新房间列表
        
        Args:
            rooms: {room_id: room_name} 字典
        """
        self.available_rooms = rooms
        current_id = self.room_combo.currentData()
        self.room_combo.clear()
        self.room_combo.addItem("-- 请选择房间 --", "")
        for room_id, room_name in sorted(rooms.items()):
            self.room_combo.addItem(f"{room_name} ({room_id})", room_id)
        # 尝试恢复之前选择的房间
        if current_id and current_id in rooms:
            for i in range(self.room_combo.count()):
                if self.room_combo.itemData(i) == current_id:
                    self.room_combo.setCurrentIndex(i)
                    break
        
    def get_selected_room_id(self) -> Optional[str]:
        """获取当前选择的房间 ID"""
        return self.room_combo.currentData()
        
    def on_publish_clicked(self):
        room_id = self.get_selected_room_id()
        if not room_id:
            QMessageBox.warning(self, "警告", "请先选择要发布新闻的房间")
            return
            
        sentiment_map = {"积极": "positive", "中立": "neutral", "消极": "negative"}
        scope_text = self.scope_edit.text().strip()
        affected_stocks = [s.strip().upper() for s in scope_text.split(",")] if scope_text else None
        
        news_data = {
            "room_id": room_id,
            "title": self.title_edit.text().strip(),
            "content": self.content_edit.toPlainText().strip(),
            "sentiment": sentiment_map[self.sentiment_combo.currentText()],
            "affected_stocks": affected_stocks
        }
        
        if not news_data["title"] or not news_data["content"]:
            QMessageBox.warning(self, "警告", "请填写新闻标题和内容")
            return
        
        self.publish_news_signal.emit(news_data)
        self.title_edit.clear()
        self.content_edit.clear()
        self.scope_edit.clear()


class ReportPublisher(QWidget):
    """财报发布器组件"""
    
    publish_report_signal = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_rooms: Dict[str, str] = {}  # room_id -> room_name
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title_label = QLabel("📊 财报发布器")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 8px;")
        layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        
        # 房间选择下拉框
        self.room_combo = QComboBox()
        self.room_combo.addItem("-- 请选择房间 --", "")
        self.room_combo.setStyleSheet("QComboBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("目标房间:", self.room_combo)
        
        self.stock_code_edit = QLineEdit()
        self.stock_code_edit.setPlaceholderText("例如：AAPL")
        self.stock_code_edit.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 8px; }")
        form_layout.addRow("股票代码:", self.stock_code_edit)
        
        self.pe_spin = QDoubleSpinBox()
        self.pe_spin.setRange(-1000, 1000)
        self.pe_spin.setValue(20.0)
        self.pe_spin.setDecimals(2)
        self.pe_spin.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("市盈率 (PE):", self.pe_spin)
        
        self.roe_spin = QDoubleSpinBox()
        self.roe_spin.setRange(-1.0, 1.0)
        self.roe_spin.setValue(0.15)
        self.roe_spin.setDecimals(4)
        self.roe_spin.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("净资产收益率 (ROE):", self.roe_spin)
        
        self.net_income_spin = QDoubleSpinBox()
        self.net_income_spin.setRange(-1e12, 1e12)
        self.net_income_spin.setValue(1000000)
        self.net_income_spin.setPrefix("¥ ")
        self.net_income_spin.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("净利润:", self.net_income_spin)
        
        self.revenue_spin = QDoubleSpinBox()
        self.revenue_spin.setRange(0, 1e12)
        self.revenue_spin.setValue(10000000)
        self.revenue_spin.setPrefix("¥ ")
        self.revenue_spin.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("营收:", self.revenue_spin)
        
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 2.0)
        self.weight_spin.setValue(1.0)
        self.weight_spin.setDecimals(2)
        self.weight_spin.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("策略影响权重:", self.weight_spin)
        
        layout.addLayout(form_layout)
        
        self.publish_button = QPushButton("📈 发布财报")
        self.publish_button.setStyleSheet("QPushButton { background-color: #2d5d8d; color: #ffffff; border: none; border-radius: 4px; padding: 12px 24px; font-weight: bold; font-size: 13px; } QPushButton:hover { background-color: #3d6d9d; }")
        self.publish_button.clicked.connect(self.on_publish_clicked)
        layout.addWidget(self.publish_button)
        layout.addStretch()
        
    def update_rooms(self, rooms: Dict[str, str]):
        """更新房间列表
        
        Args:
            rooms: {room_id: room_name} 字典
        """
        self.available_rooms = rooms
        current_id = self.room_combo.currentData()
        self.room_combo.clear()
        self.room_combo.addItem("-- 请选择房间 --", "")
        for room_id, room_name in sorted(rooms.items()):
            self.room_combo.addItem(f"{room_name} ({room_id})", room_id)
        # 尝试恢复之前选择的房间
        if current_id and current_id in rooms:
            for i in range(self.room_combo.count()):
                if self.room_combo.itemData(i) == current_id:
                    self.room_combo.setCurrentIndex(i)
                    break
        
    def get_selected_room_id(self) -> Optional[str]:
        """获取当前选择的房间 ID"""
        return self.room_combo.currentData()
        
    def on_publish_clicked(self):
        room_id = self.get_selected_room_id()
        if not room_id:
            QMessageBox.warning(self, "警告", "请先选择要发布财报的房间")
            return
            
        stock_code = self.stock_code_edit.text().strip().upper()
        if not stock_code:
            QMessageBox.warning(self, "警告", "请填写股票代码")
            return
        
        report_data = {
            "room_id": room_id,
            "stock_code": stock_code,
            "pe_ratio": self.pe_spin.value(),
            "roe": self.roe_spin.value(),
            "net_income": self.net_income_spin.value(),
            "revenue": self.revenue_spin.value(),
            "manager_weight": self.weight_spin.value()
        }
        self.publish_report_signal.emit(report_data)
        self.stock_code_edit.clear()


class StockInterventionWidget(QWidget):
    """股票参数干预组件"""
    
    intervene_signal = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title_label = QLabel("🎯 股票参数干预")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 8px;")
        layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        
        self.stock_code_edit = QLineEdit()
        self.stock_code_edit.setPlaceholderText("例如：AAPL")
        self.stock_code_edit.setStyleSheet("QLineEdit { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 8px; }")
        form_layout.addRow("股票代码:", self.stock_code_edit)
        
        self.volatility_spin = QDoubleSpinBox()
        self.volatility_spin.setRange(0.001, 1.0)
        self.volatility_spin.setValue(0.02)
        self.volatility_spin.setDecimals(4)
        self.volatility_spin.setSuffix(" (2%)")
        self.volatility_spin.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("波动率:", self.volatility_spin)
        
        self.drift_spin = QDoubleSpinBox()
        self.drift_spin.setRange(-0.1, 0.1)
        self.drift_spin.setValue(0.0001)
        self.drift_spin.setDecimals(6)
        self.drift_spin.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("漂移率:", self.drift_spin)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["random_walk", "mean_reversion", "trend_following"])
        self.model_combo.setStyleSheet("QComboBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("价格模型:", self.model_combo)
        
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 1e9)
        self.price_spin.setValue(100.0)
        self.price_spin.setPrefix("¥ ")
        self.price_spin.setDecimals(2)
        self.price_spin.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        form_layout.addRow("设定价格:", self.price_spin)
        
        layout.addLayout(form_layout)
        
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("应用参数")
        self.apply_button.setStyleSheet("QPushButton { background-color: #8d5d2d; color: #ffffff; border: none; border-radius: 4px; padding: 10px 20px; font-weight: bold; } QPushButton:hover { background-color: #9d6d3d; }")
        self.apply_button.clicked.connect(lambda: self.on_apply_clicked("params"))
        button_layout.addWidget(self.apply_button)
        
        self.set_price_button = QPushButton("设定价格")
        self.set_price_button.setStyleSheet("QPushButton { background-color: #2d8d5d; color: #ffffff; border: none; border-radius: 4px; padding: 10px 20px; font-weight: bold; } QPushButton:hover { background-color: #3d9d6d; }")
        self.set_price_button.clicked.connect(lambda: self.on_apply_clicked("price"))
        button_layout.addWidget(self.set_price_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
    def on_apply_clicked(self, action_type: str):
        stock_code = self.stock_code_edit.text().strip().upper()
        if not stock_code:
            QMessageBox.warning(self, "警告", "请填写股票代码")
            return
        
        if action_type == "params":
            intervene_data = {
                "type": "params",
                "stock_code": stock_code,
                "volatility": self.volatility_spin.value(),
                "drift": self.drift_spin.value(),
                "model": self.model_combo.currentText()
            }
        else:
            intervene_data = {
                "type": "price",
                "stock_code": stock_code,
                "price": self.price_spin.value()
            }
        self.intervene_signal.emit(intervene_data)


class StockManagementWidget(QWidget):
    """股票管理系统组件 - 支持 CRUD 操作"""
    
    create_stock_signal = Signal(dict)
    update_stock_signal = Signal(dict)
    delete_stock_signal = Signal(str)
    list_stocks_signal = Signal()
    add_to_room_signal = Signal(dict)
    remove_from_room_signal = Signal(dict)
    list_room_stocks_signal = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_room_id = None
        self.all_stocks = []
        self.room_stocks = []
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 全局股票池管理
        global_group = QGroupBox("📈 全局股票池管理")
        global_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; color: #ffffff; border: 1px solid #555555; border-radius: 4px; margin-top: 10px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        global_layout = QVBoxLayout(global_group)
        
        toolbar_layout = QHBoxLayout()
        self.create_stock_btn = QPushButton("➕ 创建股票")
        self.create_stock_btn.setStyleSheet("QPushButton { background-color: #2d7d2d; color: #ffffff; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #3d8d3d; }")
        self.create_stock_btn.clicked.connect(self.on_create_stock)
        toolbar_layout.addWidget(self.create_stock_btn)
        
        self.refresh_global_btn = QPushButton("🔄 刷新")
        self.refresh_global_btn.setStyleSheet("QPushButton { background-color: #555555; color: #ffffff; border: none; border-radius: 4px; padding: 8px 16px; } QPushButton:hover { background-color: #666666; }")
        self.refresh_global_btn.clicked.connect(self.on_refresh_global)
        toolbar_layout.addWidget(self.refresh_global_btn)
        toolbar_layout.addStretch()
        global_layout.addLayout(toolbar_layout)
        
        self.global_stock_table = QTableWidget()
        self.global_stock_table.setColumnCount(6)
        self.global_stock_table.setHorizontalHeaderLabels(["代码", "名称", "初始价格", "发行量", "描述", "操作"])
        header = self.global_stock_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.global_stock_table.setStyleSheet("QTableWidget { background-color: #2b2b2b; color: #ffffff; gridline-color: #444444; border: 1px solid #444444; border-radius: 4px; } QTableWidget::item { padding: 8px; } QHeaderView::section { background-color: #3c3c3c; color: #ffffff; padding: 8px; border: none; font-weight: bold; }")
        global_layout.addWidget(self.global_stock_table)
        main_layout.addWidget(global_group)
        
        # 房间股票池管理
        room_group = QGroupBox("🏠 房间股票池管理")
        room_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; color: #ffffff; border: 1px solid #555555; border-radius: 4px; margin-top: 10px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        room_layout = QVBoxLayout(room_group)
        
        self.room_info_label = QLabel("未选择房间")
        self.room_info_label.setStyleSheet("color: #888888; padding: 8px;")
        room_layout.addWidget(self.room_info_label)
        
        room_toolbar_layout = QHBoxLayout()
        self.add_to_room_btn = QPushButton("➕ 添加股票到房间")
        self.add_to_room_btn.setStyleSheet("QPushButton { background-color: #2d5d8d; color: #ffffff; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #3d6d9d; } QPushButton:disabled { background-color: #555555; color: #888888; }")
        self.add_to_room_btn.clicked.connect(self.on_add_to_room)
        self.add_to_room_btn.setEnabled(False)
        room_toolbar_layout.addWidget(self.add_to_room_btn)
        
        self.refresh_room_btn = QPushButton("🔄 刷新")
        self.refresh_room_btn.setStyleSheet("QPushButton { background-color: #555555; color: #ffffff; border: none; border-radius: 4px; padding: 8px 16px; } QPushButton:hover { background-color: #666666; } QPushButton:disabled { background-color: #444444; color: #666666; }")
        self.refresh_room_btn.clicked.connect(self.on_refresh_room)
        self.refresh_room_btn.setEnabled(False)
        room_toolbar_layout.addWidget(self.refresh_room_btn)
        room_toolbar_layout.addStretch()
        room_layout.addLayout(room_toolbar_layout)
        
        self.room_stock_table = QTableWidget()
        self.room_stock_table.setColumnCount(6)
        self.room_stock_table.setHorizontalHeaderLabels(["代码", "名称", "当前价格", "初始价格", "发行量", "操作"])
        room_header = self.room_stock_table.horizontalHeader()
        room_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        room_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        room_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        room_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        room_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        room_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.room_stock_table.setStyleSheet("QTableWidget { background-color: #2b2b2b; color: #ffffff; gridline-color: #444444; border: 1px solid #444444; border-radius: 4px; } QTableWidget::item { padding: 8px; } QHeaderView::section { background-color: #3c3c3c; color: #ffffff; padding: 8px; border: none; font-weight: bold; }")
        room_layout.addWidget(self.room_stock_table)
        main_layout.addWidget(room_group)
        
    def set_current_room(self, room_id: str, room_info: dict):
        self.current_room_id = room_id
        self.room_info_label.setText(f"📁 {room_info.get('name', 'Unknown')} ({room_id})")
        self.room_info_label.setStyleSheet("color: #ffffff; padding: 8px;")
        self.add_to_room_btn.setEnabled(True)
        self.refresh_room_btn.setEnabled(True)
        self.list_room_stocks_signal.emit(room_id)
        
    def clear_current_room(self):
        self.current_room_id = None
        self.room_info_label.setText("未选择房间")
        self.room_info_label.setStyleSheet("color: #888888; padding: 8px;")
        self.add_to_room_btn.setEnabled(False)
        self.refresh_room_btn.setEnabled(False)
        self.room_stock_table.setRowCount(0)
        self.room_stocks = []
        
    def update_global_stocks(self, stocks: List[dict]):
        self.all_stocks = stocks
        self.global_stock_table.setRowCount(len(stocks))
        for row, stock in enumerate(stocks):
            self.global_stock_table.setItem(row, 0, QTableWidgetItem(stock.get("code", "")))
            self.global_stock_table.setItem(row, 1, QTableWidgetItem(stock.get("name", "")))
            self.global_stock_table.setItem(row, 2, QTableWidgetItem(f"¥{stock.get('initial_price', 0):,.2f}"))
            self.global_stock_table.setItem(row, 3, QTableWidgetItem(f"{stock.get('issued_shares', 0):,}"))
            desc = stock.get("description", "")
            self.global_stock_table.setItem(row, 4, QTableWidgetItem(desc[:50] + "..." if len(desc) > 50 else desc))
            
            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet("QPushButton { background-color: #2d5d8d; color: #ffffff; border: none; border-radius: 4px; padding: 4px 12px; } QPushButton:hover { background-color: #3d6d9d; }")
            edit_btn.clicked.connect(lambda checked, s=stock: self.on_edit_stock(s))
            self.global_stock_table.setCellWidget(row, 5, edit_btn)
            
    def update_room_stocks(self, stocks: List[dict]):
        self.room_stocks = stocks
        self.room_stock_table.setRowCount(len(stocks))
        for row, stock in enumerate(stocks):
            self.room_stock_table.setItem(row, 0, QTableWidgetItem(stock.get("code", "")))
            self.room_stock_table.setItem(row, 1, QTableWidgetItem(stock.get("name", "")))
            self.room_stock_table.setItem(row, 2, QTableWidgetItem(f"¥{stock.get('current_price', 0):,.2f}"))
            self.room_stock_table.setItem(row, 3, QTableWidgetItem(f"¥{stock.get('initial_price', 0):,.2f}"))
            self.room_stock_table.setItem(row, 4, QTableWidgetItem(f"{stock.get('issued_shares', 0):,}"))
            
            remove_btn = QPushButton("移除")
            remove_btn.setStyleSheet("QPushButton { background-color: #8d2d2d; color: #ffffff; border: none; border-radius: 4px; padding: 4px 12px; } QPushButton:hover { background-color: #9d3d3d; }")
            remove_btn.clicked.connect(lambda checked, s=stock: self.on_remove_from_room(s))
            self.room_stock_table.setCellWidget(row, 5, remove_btn)
    
    def on_create_stock(self):
        dialog = CreateStockDialog(self)
        if dialog.exec() == 1:
            stock_data = dialog.get_stock_data()
            if stock_data:
                self.create_stock_signal.emit(stock_data)
                
    def on_edit_stock(self, stock: dict):
        dialog = EditStockDialog(self, stock)
        if dialog.exec() == 1:
            stock_data = dialog.get_stock_data()
            if stock_data:
                stock_data["stock_id"] = stock.get("id")
                self.update_stock_signal.emit(stock_data)
                
    def on_add_to_room(self):
        if not self.current_room_id:
            QMessageBox.warning(self, "警告", "请先选择一个房间")
            return
        dialog = SelectStockDialog(self, self.all_stocks)
        if dialog.exec() == 1:
            selected_stock = dialog.get_selected_stock()
            if selected_stock:
                price, ok = QInputDialog.getDouble(self, "设定初始价格", f"为 {selected_stock['code']} 设定初始价格:", selected_stock.get("initial_price", 100.0), 0.01, 1e9, 2)
                if ok:
                    self.add_to_room_signal.emit({"room_id": self.current_room_id, "stock_code": selected_stock["code"], "current_price": price})
                    
    def on_remove_from_room(self, stock: dict):
        if not self.current_room_id:
            return
        reply = QMessageBox.question(self, "确认移除", f"确定要从房间移除股票 {stock['code']} 吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.remove_from_room_signal.emit({"room_id": self.current_room_id, "stock_code": stock["code"]})
            
    def on_refresh_global(self):
        self.list_stocks_signal.emit()
        
    def on_refresh_room(self):
        if self.current_room_id:
            self.list_room_stocks_signal.emit(self.current_room_id)


class CreateStockDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_dialog()
        
    def setup_dialog(self):
        self.setWindowTitle("创建股票")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("例如：AAPL")
        layout.addRow("股票代码:", self.code_edit)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：苹果公司")
        layout.addRow("股票名称:", self.name_edit)
        
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 1e9)
        self.price_spin.setValue(100.0)
        self.price_spin.setPrefix("¥ ")
        layout.addRow("初始价格:", self.price_spin)
        
        self.shares_spin = QSpinBox()
        self.shares_spin.setRange(1000, 1000000000)
        self.shares_spin.setValue(1000000)
        self.shares_spin.setSingleStep(100000)
        layout.addRow("发行数量:", self.shares_spin)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("股票描述（可选）")
        layout.addRow("描述:", self.desc_edit)
        
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
    def get_stock_data(self) -> Optional[dict]:
        if self.result() == 1:
            code = self.code_edit.text().strip().upper()
            name = self.name_edit.text().strip()
            if not code or not name:
                QMessageBox.warning(self, "警告", "请填写股票代码和名称")
                return None
            return {"code": code, "name": name, "initial_price": self.price_spin.value(), "issued_shares": self.shares_spin.value(), "description": self.desc_edit.toPlainText().strip()}
        return None


class EditStockDialog(QDialog):
    def __init__(self, parent=None, stock_data: dict = None):
        super().__init__(parent)
        self.stock_data = stock_data or {}
        self.setup_dialog()
        
    def setup_dialog(self):
        self.setWindowTitle("编辑股票")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        
        self.code_edit = QLineEdit()
        self.code_edit.setText(self.stock_data.get("code", ""))
        layout.addRow("股票代码:", self.code_edit)
        
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.stock_data.get("name", ""))
        layout.addRow("股票名称:", self.name_edit)
        
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 1e9)
        self.price_spin.setValue(self.stock_data.get("initial_price", 100.0))
        self.price_spin.setPrefix("¥ ")
        layout.addRow("初始价格:", self.price_spin)
        
        self.shares_spin = QSpinBox()
        self.shares_spin.setRange(1000, 1000000000)
        self.shares_spin.setValue(self.stock_data.get("issued_shares", 1000000))
        self.shares_spin.setSingleStep(100000)
        layout.addRow("发行数量:", self.shares_spin)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setText(self.stock_data.get("description", ""))
        self.desc_edit.setMaximumHeight(80)
        layout.addRow("描述:", self.desc_edit)
        
        ok_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
    def get_stock_data(self) -> Optional[dict]:
        if self.result() == 1:
            code = self.code_edit.text().strip().upper()
            name = self.name_edit.text().strip()
            if not code or not name:
                QMessageBox.warning(self, "警告", "请填写股票代码和名称")
                return None
            return {"code": code, "name": name, "initial_price": self.price_spin.value(), "issued_shares": self.shares_spin.value(), "description": self.desc_edit.toPlainText().strip()}
        return None


class SelectStockDialog(QDialog):
    def __init__(self, parent=None, stocks: List[dict] = None):
        super().__init__(parent)
        self.stocks = stocks or []
        self.setup_dialog()
        
    def setup_dialog(self):
        self.setWindowTitle("选择股票")
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)
        
        info_label = QLabel("从全局股票池中选择一个股票添加到房间:")
        info_label.setStyleSheet("color: #ffffff; padding: 8px;")
        layout.addWidget(info_label)
        
        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(4)
        self.stock_table.setHorizontalHeaderLabels(["代码", "名称", "初始价格", "发行量"])
        self.stock_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stock_table.setSelectionMode(QTableWidget.SingleSelection)
        header = self.stock_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.stock_table.setStyleSheet("QTableWidget { background-color: #2b2b2b; color: #ffffff; gridline-color: #444444; border: 1px solid #444444; border-radius: 4px; } QTableWidget::item:selected { background-color: #3a7abd; } QHeaderView::section { background-color: #3c3c3c; color: #ffffff; padding: 8px; border: none; font-weight: bold; }")
        self.stock_table.setRowCount(len(self.stocks))
        for row, stock in enumerate(self.stocks):
            self.stock_table.setItem(row, 0, QTableWidgetItem(stock.get("code", "")))
            self.stock_table.setItem(row, 1, QTableWidgetItem(stock.get("name", "")))
            self.stock_table.setItem(row, 2, QTableWidgetItem(f"¥{stock.get('initial_price', 0):,.2f}"))
            self.stock_table.setItem(row, 3, QTableWidgetItem(f"{stock.get('issued_shares', 0):,}"))
        layout.addWidget(self.stock_table)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def get_selected_stock(self) -> Optional[dict]:
        selected = self.stock_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        if row < len(self.stocks):
            return self.stocks[row]
        return None


class RoomControlWidget(QWidget):
    control_signal = Signal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_room_id = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.room_info_label = QLabel("未选择房间")
        self.room_info_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.room_info_label.setStyleSheet("color: #888888; padding: 8px;")
        layout.addWidget(self.room_info_label)
        
        status_layout = QHBoxLayout()
        self.status_label = QLabel("状态：--")
        self.status_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        status_layout.addWidget(self.status_label)
        self.step_label = QLabel("步数：--")
        self.step_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        status_layout.addWidget(self.step_label)
        self.mode_label = QLabel("模式：--")
        self.mode_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        status_layout.addWidget(self.mode_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        grid_layout = QGridLayout()
        self.step_button = QPushButton("⏭️ 下一步")
        self.step_button.setStyleSheet("QPushButton { background-color: #2d7d2d; color: #ffffff; border: none; border-radius: 4px; padding: 15px 30px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #3d8d3d; } QPushButton:disabled { background-color: #555555; color: #888888; }")
        self.step_button.clicked.connect(lambda: self.control_signal.emit("step_forward", {}))
        grid_layout.addWidget(self.step_button, 0, 0)
        
        self.fast_forward_button = QPushButton("⏩ 快进")
        self.fast_forward_button.setStyleSheet("QPushButton { background-color: #2d5d8d; color: #ffffff; border: none; border-radius: 4px; padding: 15px 30px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #3d6d9d; } QPushButton:disabled { background-color: #555555; color: #888888; }")
        self.fast_forward_button.clicked.connect(lambda: self.control_signal.emit("fast_forward", {}))
        grid_layout.addWidget(self.fast_forward_button, 0, 1)
        
        self.pause_button = QPushButton("⏸️ 暂停")
        self.pause_button.setStyleSheet("QPushButton { background-color: #8d7d2d; color: #ffffff; border: none; border-radius: 4px; padding: 15px 30px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #9d8d3d; } QPushButton:disabled { background-color: #555555; color: #888888; }")
        self.pause_button.clicked.connect(lambda: self.control_signal.emit("pause", {}))
        grid_layout.addWidget(self.pause_button, 0, 2)
        
        self.resume_button = QPushButton("▶️ 恢复")
        self.resume_button.setStyleSheet("QPushButton { background-color: #2d8d5d; color: #ffffff; border: none; border-radius: 4px; padding: 15px 30px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #3d9d6d; } QPushButton:disabled { background-color: #555555; color: #888888; }")
        self.resume_button.clicked.connect(lambda: self.control_signal.emit("resume", {}))
        grid_layout.addWidget(self.resume_button, 1, 0)
        
        self.destroy_button = QPushButton("🗑️ 销毁房间")
        self.destroy_button.setStyleSheet("QPushButton { background-color: #8d2d2d; color: #ffffff; border: none; border-radius: 4px; padding: 15px 30px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #9d3d3d; } QPushButton:disabled { background-color: #555555; color: #888888; }")
        self.destroy_button.clicked.connect(self.on_destroy_clicked)
        grid_layout.addWidget(self.destroy_button, 1, 1)
        
        speed_layout = QHBoxLayout()
        speed_label = QLabel("快进速度:")
        speed_label.setStyleSheet("color: #ffffff;")
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 10.0)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setDecimals(1)
        self.speed_spin.setSuffix(" 步/秒")
        self.speed_spin.setStyleSheet("QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }")
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_spin)
        speed_layout.addStretch()
        grid_layout.addLayout(speed_layout, 1, 2)
        layout.addLayout(grid_layout)
        layout.addStretch()
        
    def set_room(self, room_id: str, room_info: dict):
        self.current_room_id = room_id
        self.room_info_label.setText(f"📁 {room_info.get('name', 'Unknown')} ({room_id})")
        self.room_info_label.setStyleSheet("color: #ffffff; padding: 8px;")
        self.status_label.setText(f"状态：{room_info.get('status', '--')}")
        self.step_label.setText(f"步数：{room_info.get('step_count', '--')}")
        self.mode_label.setText(f"模式：{room_info.get('step_mode', '--')}")
        
    def clear_room(self):
        self.current_room_id = None
        self.room_info_label.setText("未选择房间")
        self.room_info_label.setStyleSheet("color: #888888; padding: 8px;")
        self.status_label.setText("状态：--")
        self.step_label.setText("步数：--")
        self.mode_label.setText("模式：--")
        
    def on_destroy_clicked(self):
        if not self.current_room_id:
            return
        reply = QMessageBox.question(self, "确认销毁", f"确定要销毁房间 {self.current_room_id} 吗？\n此操作不可恢复！", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.control_signal.emit("destroy_room", {})


class ParticipantListWidget(QWidget):
    kick_user_signal = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel("👥 参与者列表")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 8px;")
        layout.addWidget(title_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["类型", "ID/名称", "资金", "操作"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setStyleSheet("QTableWidget { background-color: #2b2b2b; color: #ffffff; gridline-color: #444444; border: 1px solid #444444; border-radius: 4px; } QTableWidget::item { padding: 8px; } QHeaderView::section { background-color: #3c3c3c; color: #ffffff; padding: 8px; border: none; font-weight: bold; }")
        layout.addWidget(self.table)
        
    def update_participants(self, users: List[dict], robots: List[dict]):
        self.table.setRowCount(len(users) + len(robots))
        row = 0
        for user in users:
            self.table.setItem(row, 0, QTableWidgetItem("👤 真人"))
            self.table.setItem(row, 1, QTableWidgetItem(user.get("user_id", "")))
            self.table.setItem(row, 2, QTableWidgetItem(f"¥{user.get('current_cash', 0):,.2f}"))
            kick_btn = QPushButton("踢出")
            kick_btn.setStyleSheet("QPushButton { background-color: #8d2d2d; color: #ffffff; border: none; border-radius: 4px; padding: 4px 12px; } QPushButton:hover { background-color: #9d3d3d; }")
            kick_btn.clicked.connect(lambda checked, uid=user.get("user_id"): self.kick_user_signal.emit(uid))
            self.table.setCellWidget(row, 3, kick_btn)
            row += 1
        for robot in robots:
            strategy_map = {"retail": "散户", "institution": "机构", "trend": "趋势"}
            strategy_name = strategy_map.get(robot.get("strategy_type", ""), "")
            self.table.setItem(row, 0, QTableWidgetItem(f"🤖 {strategy_name}"))
            self.table.setItem(row, 1, QTableWidgetItem(robot.get("name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(f"¥{robot.get('total_value', 0):,.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem("--"))
            row += 1


class CreateRoomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_dialog()
        
    def setup_dialog(self):
        self.setWindowTitle("创建房间")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入房间名称")
        layout.addRow("房间名称:", self.name_edit)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["秒级", "小时级", "天级", "月级"])
        layout.addRow("步进模式:", self.mode_combo)
        self.capital_spin = QDoubleSpinBox()
        self.capital_spin.setRange(1000, 10000000)
        self.capital_spin.setValue(100000)
        self.capital_spin.setPrefix("¥ ")
        layout.addRow("初始资金:", self.capital_spin)
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
    def get_room_data(self) -> Optional[dict]:
        if self.result() == 1:
            mode_map = {"秒级": "second", "小时级": "hour", "天级": "day", "月级": "month"}
            return {"name": self.name_edit.text(), "step_mode": mode_map[self.mode_combo.currentText()], "initial_capital": self.capital_spin.value()}
        return None


class AdminMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_room_id = None
        self.rooms_data: Dict[str, dict] = {}
        self.ws_client: Optional[WebSocketClientThread] = None
        self.connected = False
        self.setup_ui()
        self.setup_styles()
        self.connect_signals()
        self.connect_to_server()
        
    def connect_signals(self):
        self.create_room_button.clicked.connect(self.on_create_room)
        self.refresh_button.clicked.connect(self.on_refresh)
        self.room_control.control_signal.connect(self.on_room_control)
        self.news_publisher.publish_news_signal.connect(self.on_publish_news)
        self.report_publisher.publish_report_signal.connect(self.on_publish_report)
        self.stock_intervention.intervene_signal.connect(self.on_stock_intervention)
        self.stock_management.create_stock_signal.connect(self.on_create_stock)
        self.stock_management.update_stock_signal.connect(self.on_update_stock)
        self.stock_management.list_stocks_signal.connect(self.on_list_stocks)
        self.stock_management.add_to_room_signal.connect(self.on_add_to_room)
        self.stock_management.remove_from_room_signal.connect(self.on_remove_from_room)
        self.stock_management.list_room_stocks_signal.connect(self.on_list_room_stocks)
        self.participant_list.kick_user_signal.connect(self.on_kick_user)
        
    def connect_to_server(self):
        self.ws_client = WebSocketClientThread(HOST, PORT)
        self.ws_client.connected_signal.connect(self.on_connected)
        self.ws_client.disconnected_signal.connect(self.on_disconnected)
        self.ws_client.message_received_signal.connect(self.on_message_received)
        self.ws_client.error_signal.connect(self.on_connection_error)
        self.ws_client.start()
        
    def on_connected(self):
        self.connected = True
        logger.info("Admin UI connected to server")
        self.statusBar().showMessage("已连接到服务器", 5000)
        self.request_room_list()
        self.on_list_stocks()
        
    def on_disconnected(self):
        self.connected = False
        self.statusBar().showMessage("与服务器断开连接", 5000)
        
    def on_connection_error(self, error: str):
        self.connected = False
        logger.error(f"Connection error: {error}")
        self.statusBar().showMessage(error, 10000)
        
    def on_message_received(self, message: dict):
        msg_type = message.get("type")
        data = message.get("data", {})
        
        if msg_type == MessageType.ROOM_LIST.value:
            rooms = data.get("rooms", [])
            self.update_room_list(rooms)
        elif msg_type == MessageType.SUCCESS.value:
            msg = data.get("message", "操作成功")
            self.statusBar().showMessage(msg, 3000)
            QTimer.singleShot(300, self.request_room_list)
        elif msg_type == MessageType.ERROR.value:
            err = data.get("error", "未知错误")
            self.statusBar().showMessage(f"错误：{err}", 5000)
        elif msg_type == MessageType.STOCK_LIST.value:
            stocks = data.get("stocks", [])
            self.stock_management.update_global_stocks(stocks)
        elif msg_type == MessageType.ROOM_STOCK_LIST.value:
            stocks = data.get("stocks", [])
            room_id = data.get("room_id")
            if room_id == self.current_room_id:
                self.stock_management.update_room_stocks(stocks)
            
    def send_message(self, message):
        if self.ws_client and self.connected:
            self.ws_client.send_message(message)
        else:
            logger.warning("Not connected to server, cannot send message")
            self.statusBar().showMessage("未连接到服务器", 3000)
            
    def request_room_list(self):
        message = create_message(MessageType.ROOM_LIST, {})
        self.send_message(message)
        
    def on_create_room(self):
        dialog = CreateRoomDialog(self)
        if dialog.exec() == 1:
            room_data = dialog.get_room_data()
            if room_data:
                message = create_message(MessageType.CREATE_ROOM, room_data)
                self.send_message(message)
                QTimer.singleShot(500, self.request_room_list)
                
    def on_refresh(self):
        self.request_room_list()
        
    def on_room_control(self, action: str, data: dict):
        if not self.current_room_id:
            QMessageBox.warning(self, "警告", "请先选择一个房间")
            return
        message_map = {"step_forward": MessageType.ADMIN_STEP_FORWARD, "fast_forward": MessageType.ADMIN_FAST_FORWARD, "pause": MessageType.ADMIN_PAUSE, "resume": MessageType.ADMIN_RESUME, "destroy_room": MessageType.ADMIN_DESTROY_ROOM}
        msg_type = message_map.get(action)
        if msg_type:
            payload = {"room_id": self.current_room_id, **data}
            if action == "fast_forward":
                payload["start"] = True
                payload["speed"] = self.room_control.speed_spin.value()
            message = create_message(msg_type, payload)
            self.send_message(message)
            
    def on_publish_news(self, news_data: dict):
        # news_data 已经包含 room_id（从新闻发布器的房间下拉框选择）
        if not news_data.get("room_id"):
            QMessageBox.warning(self, "警告", "请先选择要发布新闻的房间")
            return
        message = create_message(MessageType.ADMIN_PUBLISH_NEWS, news_data)
        self.send_message(message)
        
    def on_publish_report(self, report_data: dict):
        # report_data 已经包含 room_id（从财报发布器的房间下拉框选择）
        if not report_data.get("room_id"):
            QMessageBox.warning(self, "警告", "请先选择要发布财报的房间")
            return
        message = create_message(MessageType.ADMIN_PUBLISH_REPORT, report_data)
        self.send_message(message)
        
    def on_stock_intervention(self, intervene_data: dict):
        if not self.current_room_id:
            QMessageBox.warning(self, "警告", "请先选择一个房间")
            return
        payload = {"room_id": self.current_room_id, **intervene_data}
        message = create_message(MessageType.ADMIN_STOCK_INTERVENTION, payload)
        self.send_message(message)
        
    def on_create_stock(self, stock_data: dict):
        message = create_message(MessageType.ADMIN_CREATE_STOCK, stock_data)
        self.send_message(message)
        
    def on_update_stock(self, stock_data: dict):
        message = create_message(MessageType.ADMIN_UPDATE_STOCK, stock_data)
        self.send_message(message)
        
    def on_list_stocks(self):
        message = create_message(MessageType.ADMIN_LIST_STOCKS, {})
        self.send_message(message)
        
    def on_add_to_room(self, data: dict):
        message = create_message(MessageType.ADMIN_ADD_STOCK_TO_ROOM, data)
        self.send_message(message)
        
    def on_remove_from_room(self, data: dict):
        message = create_message(MessageType.ADMIN_REMOVE_STOCK_FROM_ROOM, data)
        self.send_message(message)
        
    def on_list_room_stocks(self, room_id: str):
        message = create_message(MessageType.ADMIN_LIST_ROOM_STOCKS, {"room_id": room_id})
        self.send_message(message)
        
    def on_kick_user(self, user_id: str):
        pass
        
    def closeEvent(self, event):
        if self.ws_client:
            self.ws_client.stop()
            self.ws_client.wait(1000)
        event.accept()

    def setup_ui(self):
        self.setWindowTitle("Stonk - 管理员控制台")
        self.setMinimumSize(1400, 900)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        toolbar_layout = QHBoxLayout()
        self.create_room_button = QPushButton("➕ 创建房间")
        self.create_room_button.setStyleSheet("QPushButton { background-color: #2d7d2d; color: #ffffff; border: none; border-radius: 4px; padding: 10px 20px; font-weight: bold; }")
        toolbar_layout.addWidget(self.create_room_button)
        self.refresh_button = QPushButton("🔄 刷新")
        self.refresh_button.setStyleSheet("QPushButton { background-color: #555555; color: #ffffff; border: none; border-radius: 4px; padding: 10px 20px; }")
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        splitter = QSplitter(Qt.Horizontal)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_label = QLabel("📋 房间列表")
        left_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        left_label.setStyleSheet("color: #ffffff; padding: 8px;")
        left_layout.addWidget(left_label)
        self.room_list = QTableWidget()
        self.room_list.setColumnCount(5)
        self.room_list.setHorizontalHeaderLabels(["名称", "模式", "状态", "人数", "机器人"])
        self.room_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.room_list.setSelectionMode(QTableWidget.SingleSelection)
        self.room_list.itemSelectionChanged.connect(self.on_room_selected)
        self.room_list.setStyleSheet("QTableWidget { background-color: #2b2b2b; color: #ffffff; gridline-color: #444444; border: 1px solid #444444; border-radius: 4px; } QTableWidget::item:selected { background-color: #3a7abd; } QHeaderView::section { background-color: #3c3c3c; color: #ffffff; padding: 8px; border: none; font-weight: bold; }")
        left_layout.addWidget(self.room_list)
        splitter.addWidget(left_panel)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #444444; border-radius: 4px; background-color: #1e1e1e; } QTabBar::tab { background-color: #3c3c3c; color: #ffffff; padding: 10px 20px; margin-right: 2px; } QTabBar::tab:selected { background-color: #1e1e1e; }")
        
        self.room_control = RoomControlWidget()
        self.tabs.addTab(self.room_control, "🏠 房间控制")
        self.news_publisher = NewsPublisher()
        self.tabs.addTab(self.news_publisher, "📰 新闻发布")
        self.report_publisher = ReportPublisher()
        self.tabs.addTab(self.report_publisher, "📊 财报发布")
        self.stock_intervention = StockInterventionWidget()
        self.tabs.addTab(self.stock_intervention, "🎯 股票干预")
        self.stock_management = StockManagementWidget()
        self.tabs.addTab(self.stock_management, "📈 股票管理")
        self.participant_list = ParticipantListWidget()
        self.tabs.addTab(self.participant_list, "👥 参与者")
        
        right_layout.addWidget(self.tabs)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)

    def setup_styles(self):
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }")

    def update_room_list(self, rooms: List[dict]):
        self.rooms_data = {room["id"]: room for room in rooms}
        self.room_list.setRowCount(len(rooms))
        for row, room in enumerate(rooms):
            self.room_list.setItem(row, 0, QTableWidgetItem(room.get("name", "")))
            self.room_list.setItem(row, 1, QTableWidgetItem(room.get("step_mode", "")))
            self.room_list.setItem(row, 2, QTableWidgetItem(room.get("status", "")))
            self.room_list.setItem(row, 3, QTableWidgetItem(str(room.get("user_count", 0))))
            self.room_list.setItem(row, 4, QTableWidgetItem(str(room.get("robot_count", 0))))
        
        # 同步更新新闻发布器和财报发布器的房间列表
        rooms_dict = {room["id"]: room.get("name", "Unknown") for room in rooms}
        self.news_publisher.update_rooms(rooms_dict)
        self.report_publisher.update_rooms(rooms_dict)

    def on_room_selected(self):
        selected = self.room_list.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        room_id = list(self.rooms_data.keys())[row]
        room_info = self.rooms_data[room_id]
        self.current_room_id = room_id
        self.room_control.set_room(room_id, room_info)
        self.stock_management.set_current_room(room_id, room_info)

    def get_current_room_id(self) -> Optional[str]:
        return self.current_room_id


def run_admin_ui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AdminMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_admin_ui()
