"""
Stonk - 管理员 UI 模块

PySide6 管理员界面，支持：
- 多标签页房间管理
- 步进控制（下一步、快进、暂停）
- 参与者列表（整合在房间控制中，含刷新功能）
- 操作日志（记录真人和机器人的操作）
- 股票参数干预
- 新闻发布器
- 财报发布器
- 机器人管理
- 股票管理（CRUD）
- 调试控制台（完整显示所有 WebSocket 通信、系统日志和错误信息）
"""

import sys
import os

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncio
import collections
import json
import traceback
import websockets
from datetime import datetime
from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QSplitter, QGridLayout, QDialog, QInputDialog, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont, QTextCursor, QColor

import logging

from shared.message_protocol import MessageType, create_message, parse_message
from shared.utils import get_timestamp
from shared.constants import SERVER_CONNECT_HOST, SERVER_PORT
from server.config import PORT

HOST = SERVER_CONNECT_HOST

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== 自定义日志处理器 ====================

class QtLogHandler(logging.Handler, QObject):
    """将 Python logging 输出重定向到 Qt 信号（线程安全版本）

    继承 QObject 以支持 Qt 信号机制，确保跨线程日志消息
    通过 QueuedConnection 安全投递到主线程，避免在工作线程
    中直接操作 Qt 控件导致的 UI 无响应/崩溃问题。
    """

    _log_signal = Signal(str, int)

    def __init__(self, callback):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        # QueuedConnection 确保信号跨线程时排队到主线程事件循环
        self._log_signal.connect(callback, Qt.QueuedConnection)

    def emit(self, record):
        try:
            msg = self.format(record)
            self._log_signal.emit(msg, record.levelno)
        except Exception:
            pass


# ==================== 通用样式常量 ====================
BTN_STYLE_GREEN = "QPushButton { background-color: #2d7d2d; color: #ffffff; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #3d8d3d; } QPushButton:disabled { background-color: #555555; color: #888888; }"
BTN_STYLE_BLUE = "QPushButton { background-color: #2d5d8d; color: #ffffff; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #3d6d9d; } QPushButton:disabled { background-color: #555555; color: #888888; }"
BTN_STYLE_GRAY = "QPushButton { background-color: #555555; color: #ffffff; border: none; border-radius: 4px; padding: 8px 16px; } QPushButton:hover { background-color: #666666; } QPushButton:disabled { background-color: #444444; color: #666666; }"
BTN_STYLE_RED = "QPushButton { background-color: #8d2d2d; color: #ffffff; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #9d3d3d; } QPushButton:disabled { background-color: #555555; color: #888888; }"
TABLE_STYLE = "QTableWidget { background-color: #2b2b2b; color: #ffffff; gridline-color: #444444; border: 1px solid #444444; border-radius: 4px; } QTableWidget::item { padding: 8px; } QTableWidget::item:selected { background-color: #3a7abd; } QHeaderView::section { background-color: #3c3c3c; color: #ffffff; padding: 8px; border: none; font-weight: bold; }"
GROUPBOX_STYLE = "QGroupBox { font-weight: bold; font-size: 13px; color: #ffffff; border: 1px solid #555555; border-radius: 4px; margin-top: 10px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }"
INPUT_STYLE = "background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px;"


class WebSocketClientThread(QThread):
    """WebSocket 客户端线程"""

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
        self._message_queue = collections.deque()

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._connect_and_listen(loop))

    async def _connect_and_listen(self, loop):
        uri = f"ws://{self.host}:{self.port}"
        try:
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
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
                        break
                send_task.cancel()
        except Exception as e:
            error_msg = f"连接失败：{str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            print(error_msg, flush=True)
            self.error_signal.emit(error_msg)

    async def _process_send_queue(self, loop):
        while self.running:
            if self._message_queue:
                msg_str = self._message_queue.popleft()
                try:
                    await self.websocket.send(msg_str)
                except Exception as e:
                    error_msg = f"发送失败：{str(e)}\n{traceback.format_exc()}"
                    logger.error(error_msg)
                    print(error_msg, flush=True)
                    self.error_signal.emit(error_msg)
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


# ==================== 房间控制组件（含参与者列表 + 操作日志）====================

class RoomControlWidget(QWidget):
    """房间控制组件 - 整合了参与者列表和操作日志"""

    control_signal = Signal(str, dict)
    refresh_participants_signal = Signal(str)   # room_id
    get_operation_log_signal = Signal(str)       # room_id
    kick_user_signal = Signal(str)               # user_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_room_id = None
        self._auto_scroll = True
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── 房间信息 ──
        self.room_info_label = QLabel("未选择房间")
        self.room_info_label.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        self.room_info_label.setStyleSheet("color: #888888; padding: 4px 0;")
        layout.addWidget(self.room_info_label)

        # ── 状态行 ──
        status_layout = QHBoxLayout()
        self.status_label = QLabel("状态：--")
        self.status_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        self.step_label = QLabel("步数：--")
        self.step_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        self.mode_label = QLabel("模式：--")
        self.mode_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        status_layout.addSpacing(16)
        status_layout.addWidget(self.step_label)
        status_layout.addSpacing(16)
        status_layout.addWidget(self.mode_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # ── 控制按钮组 ──
        ctrl_group = QGroupBox("🎮 步进控制")
        ctrl_group.setStyleSheet(GROUPBOX_STYLE)
        ctrl_inner = QVBoxLayout(ctrl_group)

        grid = QGridLayout()
        grid.setSpacing(8)

        self.step_button = QPushButton("⏭️ 下一步")
        self.step_button.setStyleSheet(BTN_STYLE_GREEN.replace("padding: 8px 16px", "padding: 12px 20px").replace("font-weight: bold", "font-weight: bold; font-size: 13px"))
        self.step_button.clicked.connect(lambda: self.control_signal.emit("step_forward", {}))
        grid.addWidget(self.step_button, 0, 0)

        self.fast_forward_button = QPushButton("⏩ 快进")
        self.fast_forward_button.setStyleSheet(BTN_STYLE_BLUE.replace("padding: 8px 16px", "padding: 12px 20px").replace("font-weight: bold", "font-weight: bold; font-size: 13px"))
        self.fast_forward_button.clicked.connect(lambda: self.control_signal.emit("fast_forward", {}))
        grid.addWidget(self.fast_forward_button, 0, 1)

        self.pause_button = QPushButton("⏸️ 暂停")
        self.pause_button.setStyleSheet("QPushButton { background-color: #8d7d2d; color: #ffffff; border: none; border-radius: 4px; padding: 12px 20px; font-weight: bold; font-size: 13px; } QPushButton:hover { background-color: #9d8d3d; }")
        self.pause_button.clicked.connect(lambda: self.control_signal.emit("pause", {}))
        grid.addWidget(self.pause_button, 0, 2)

        self.resume_button = QPushButton("▶️ 恢复")
        self.resume_button.setStyleSheet("QPushButton { background-color: #2d8d5d; color: #ffffff; border: none; border-radius: 4px; padding: 12px 20px; font-weight: bold; font-size: 13px; } QPushButton:hover { background-color: #3d9d6d; }")
        self.resume_button.clicked.connect(lambda: self.control_signal.emit("resume", {}))
        grid.addWidget(self.resume_button, 1, 0)

        self.destroy_button = QPushButton("🗑️ 销毁房间")
        self.destroy_button.setStyleSheet(BTN_STYLE_RED.replace("padding: 8px 16px", "padding: 12px 20px").replace("font-weight: bold", "font-weight: bold; font-size: 13px"))
        self.destroy_button.clicked.connect(self.on_destroy_clicked)
        grid.addWidget(self.destroy_button, 1, 1)

        speed_widget = QWidget()
        speed_layout = QHBoxLayout(speed_widget)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_lbl = QLabel("快进速度:")
        speed_lbl.setStyleSheet("color: #cccccc;")
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 10.0)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setDecimals(1)
        self.speed_spin.setSuffix(" 步/秒")
        self.speed_spin.setStyleSheet(f"QDoubleSpinBox {{ {INPUT_STYLE} }}")
        speed_layout.addWidget(speed_lbl)
        speed_layout.addWidget(self.speed_spin)
        grid.addWidget(speed_widget, 1, 2)

        ctrl_inner.addLayout(grid)
        layout.addWidget(ctrl_group)

        # ── 下方分割区：参与者列表 + 操作日志 ──
        bottom_splitter = QSplitter(Qt.Vertical)
        bottom_splitter.setStyleSheet("QSplitter::handle { background-color: #444444; height: 4px; }")

        # ── 参与者列表 ──
        participant_group = QGroupBox("👥 参与者列表")
        participant_group.setStyleSheet(GROUPBOX_STYLE)
        participant_layout = QVBoxLayout(participant_group)
        participant_layout.setSpacing(4)

        p_toolbar = QHBoxLayout()
        self.participant_count_label = QLabel("共 0 人")
        self.participant_count_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        p_toolbar.addWidget(self.participant_count_label)
        p_toolbar.addStretch()

        self.refresh_participants_btn = QPushButton("🔄 刷新参与者")
        self.refresh_participants_btn.setStyleSheet(BTN_STYLE_GRAY)
        self.refresh_participants_btn.clicked.connect(self.on_refresh_participants)
        self.refresh_participants_btn.setEnabled(False)
        p_toolbar.addWidget(self.refresh_participants_btn)
        participant_layout.addLayout(p_toolbar)

        self.participant_table = QTableWidget()
        self.participant_table.setColumnCount(5)
        self.participant_table.setHorizontalHeaderLabels(["类型", "ID / 名称", "资金", "就绪", "操作"])
        ph = self.participant_table.horizontalHeader()
        ph.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        ph.setSectionResizeMode(1, QHeaderView.Stretch)
        ph.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        ph.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        ph.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.participant_table.setStyleSheet(TABLE_STYLE)
        self.participant_table.setMinimumHeight(120)
        participant_layout.addWidget(self.participant_table)
        bottom_splitter.addWidget(participant_group)

        # ── 操作日志 ──
        log_group = QGroupBox("📋 操作日志")
        log_group.setStyleSheet(GROUPBOX_STYLE)
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(4)

        log_toolbar = QHBoxLayout()
        self.log_count_label = QLabel("共 0 条记录")
        self.log_count_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        log_toolbar.addWidget(self.log_count_label)
        log_toolbar.addStretch()

        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.setStyleSheet("color: #cccccc; font-size: 12px;")
        self.auto_scroll_check.stateChanged.connect(self._on_auto_scroll_changed)
        log_toolbar.addWidget(self.auto_scroll_check)

        self.refresh_log_btn = QPushButton("🔄 刷新日志")
        self.refresh_log_btn.setStyleSheet(BTN_STYLE_GRAY)
        self.refresh_log_btn.clicked.connect(self.on_refresh_log)
        self.refresh_log_btn.setEnabled(False)
        log_toolbar.addWidget(self.refresh_log_btn)

        self.clear_log_btn = QPushButton("🗑️ 清空")
        self.clear_log_btn.setStyleSheet(BTN_STYLE_GRAY)
        self.clear_log_btn.clicked.connect(self.clear_operation_log)
        log_toolbar.addWidget(self.clear_log_btn)
        log_layout.addLayout(log_toolbar)

        self.operation_log = QTextEdit()
        self.operation_log.setReadOnly(True)
        self.operation_log.setStyleSheet(
            "QTextEdit { background-color: #1a1a1a; color: #cccccc; "
            "border: 1px solid #444444; border-radius: 4px; "
            "font-family: 'Consolas', 'Microsoft YaHei'; font-size: 12px; padding: 4px; }"
        )
        self.operation_log.setMinimumHeight(150)
        log_layout.addWidget(self.operation_log)
        bottom_splitter.addWidget(log_group)

        bottom_splitter.setSizes([180, 300])
        layout.addWidget(bottom_splitter, 1)

    # ── 房间设置 / 清除 ──

    def set_room(self, room_id: str, room_info: dict):
        self.current_room_id = room_id
        self.room_info_label.setText(f"📁 {room_info.get('name', 'Unknown')}  ({room_id})")
        self.room_info_label.setStyleSheet("color: #ffffff; padding: 4px 0;")
        self.status_label.setText(f"状态：{room_info.get('status', '--')}")
        self.step_label.setText(f"步数：{room_info.get('step_count', '--')}")
        self.mode_label.setText(f"模式：{room_info.get('step_mode', '--')}")
        self.refresh_participants_btn.setEnabled(True)
        self.refresh_log_btn.setEnabled(True)

    def clear_room(self):
        self.current_room_id = None
        self.room_info_label.setText("未选择房间")
        self.room_info_label.setStyleSheet("color: #888888; padding: 4px 0;")
        self.status_label.setText("状态：--")
        self.step_label.setText("步数：--")
        self.mode_label.setText("模式：--")
        self.refresh_participants_btn.setEnabled(False)
        self.refresh_log_btn.setEnabled(False)
        self.participant_table.setRowCount(0)
        self.participant_count_label.setText("共 0 人")

    # ── 参与者列表 ──

    def update_participants(self, users: List[dict], robots: List[dict]):
        """更新参与者列表显示"""
        total = len(users) + len(robots)
        self.participant_count_label.setText(
            f"共 {total} 人  （真人 {len(users)} · 机器人 {len(robots)}）"
        )
        self.participant_table.setRowCount(total)

        strategy_map = {"retail": "散户", "institution": "机构", "trend": "趋势"}
        row = 0

        # 真人用户
        for user in users:
            user_id = user.get("user_id", "")
            username = user.get("username", user_id)
            total_value = user.get("total_value", user.get("current_cash", 0))

            type_item = QTableWidgetItem("👤 真人")
            type_item.setForeground(Qt.cyan)
            self.participant_table.setItem(row, 0, type_item)
            self.participant_table.setItem(row, 1, QTableWidgetItem(username))
            self.participant_table.setItem(row, 2, QTableWidgetItem(f"¥{total_value:,.2f}"))
            # 就绪状态列（默认未就绪）
            ready_item = QTableWidgetItem("⬜ 等待中")
            ready_item.setForeground(QColor("#888888"))
            self.participant_table.setItem(row, 3, ready_item)

            kick_btn = QPushButton("踢出")
            kick_btn.setStyleSheet(
                "QPushButton { background-color: #8d2d2d; color: #ffffff; border: none; "
                "border-radius: 4px; padding: 3px 10px; font-size: 11px; } "
                "QPushButton:hover { background-color: #9d3d3d; }"
            )
            kick_btn.clicked.connect(lambda checked, uid=user_id: self.kick_user_signal.emit(uid))
            self.participant_table.setCellWidget(row, 4, kick_btn)
            row += 1

        # 机器人
        for robot in robots:
            strategy = strategy_map.get(robot.get("strategy_type", ""), "未知")
            total_value = robot.get("total_value", robot.get("current_cash", robot.get("initial_capital", 0)))

            type_item = QTableWidgetItem(f"🤖 {strategy}")
            type_item.setForeground(Qt.yellow)
            self.participant_table.setItem(row, 0, type_item)
            self.participant_table.setItem(row, 1, QTableWidgetItem(robot.get("name", "")))
            self.participant_table.setItem(row, 2, QTableWidgetItem(f"¥{total_value:,.2f}"))
            self.participant_table.setItem(row, 3, QTableWidgetItem("--"))
            self.participant_table.setItem(row, 4, QTableWidgetItem("--"))
            row += 1

    def update_ready_status(self, users_ready_info: list, ready_count: int, total_count: int):
        """更新参与者就绪状态列（根据 STEP_READY_UPDATE 消息）"""
        # 构建 user_id -> is_ready 映射
        ready_map = {u.get("user_id", ""): u.get("is_ready", False) for u in users_ready_info}

        # 遍历表格中的真人用户行，更新就绪状态
        for row in range(self.participant_table.rowCount()):
            type_item = self.participant_table.item(row, 0)
            if not type_item or "真人" not in type_item.text():
                continue
            name_item = self.participant_table.item(row, 1)
            if not name_item:
                continue
            # 通过用户名匹配（也可通过 user_id，但表格只存了 username）
            # 遍历 users_ready_info 找到匹配的用户
            username = name_item.text()
            is_ready = False
            for u in users_ready_info:
                if u.get("username") == username or u.get("user_id") == username:
                    is_ready = u.get("is_ready", False)
                    break

            if is_ready:
                ready_item = QTableWidgetItem("✅ 已确认")
                ready_item.setForeground(QColor("#00cc44"))
            else:
                ready_item = QTableWidgetItem("⬜ 等待中")
                ready_item.setForeground(QColor("#888888"))
            self.participant_table.setItem(row, 3, ready_item)

        # 更新计数标签
        total_users = sum(1 for row in range(self.participant_table.rowCount())
                          if self.participant_table.item(row, 0) and "真人" in self.participant_table.item(row, 0).text())
        self.participant_count_label.setText(
            f"共 {self.participant_table.rowCount()} 人  "
            f"（真人 {total_users} · 已确认 {ready_count}/{total_count}）"
        )

    def on_refresh_participants(self):
        if self.current_room_id:
            self.refresh_participants_signal.emit(self.current_room_id)

    # ── 操作日志 ──

    def add_operation_log_entry(self, entry: dict):
        """追加单条操作日志"""
        ts = entry.get("timestamp", 0)
        try:
            time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        except Exception:
            time_str = "--:--:--"

        actor_type = entry.get("actor_type", "")
        actor_name = entry.get("actor_name", entry.get("actor_id", ""))
        action = entry.get("action", "")
        details = entry.get("details", "")

        # 根据类型选择颜色标记
        if actor_type == "user":
            icon = "👤"
            color = "#5bc8f5"
        elif actor_type == "robot":
            icon = "🤖"
            color = "#f5c842"
        else:
            icon = "⚙️"
            color = "#aaaaaa"

        line = (
            f'<span style="color:#666666;">[{time_str}]</span> '
            f'<span style="color:{color};">{icon} {actor_name}</span> '
            f'<span style="color:#cccccc;">→ {details}</span>'
        )
        self.operation_log.append(line)

        # 更新计数
        count = self.operation_log.document().blockCount()
        self.log_count_label.setText(f"共 {count} 条记录")

        # 自动滚动
        if self._auto_scroll:
            cursor = self.operation_log.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.operation_log.setTextCursor(cursor)

    def load_full_operation_log(self, entries: List[dict]):
        """加载完整操作日志（替换现有内容）"""
        self.operation_log.clear()
        for entry in entries:
            self.add_operation_log_entry(entry)

    def clear_operation_log(self):
        self.operation_log.clear()
        self.log_count_label.setText("共 0 条记录")

    def on_refresh_log(self):
        if self.current_room_id:
            self.get_operation_log_signal.emit(self.current_room_id)

    def _on_auto_scroll_changed(self, state):
        self._auto_scroll = (state == Qt.Checked)

    # ── 销毁房间 ──

    def on_destroy_clicked(self):
        if not self.current_room_id:
            return
        reply = QMessageBox.question(
            self, "确认销毁",
            f"确定要销毁房间 {self.current_room_id} 吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.control_signal.emit("destroy_room", {})


# ==================== 新闻发布器 ====================

class NewsPublisher(QWidget):
    publish_news_signal = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_rooms: Dict[str, str] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        title_label = QLabel("📰 新闻发布器")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 8px;")
        layout.addWidget(title_label)

        form = QFormLayout()
        self.room_combo = QComboBox()
        self.room_combo.addItem("-- 请选择房间 --", "")
        self.room_combo.setStyleSheet(f"QComboBox {{ {INPUT_STYLE} }}")
        form.addRow("目标房间:", self.room_combo)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("输入新闻标题...")
        self.title_edit.setStyleSheet(f"QLineEdit {{ {INPUT_STYLE} }}")
        form.addRow("标题:", self.title_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("输入新闻详细内容...")
        self.content_edit.setMaximumHeight(100)
        self.content_edit.setStyleSheet(f"QTextEdit {{ {INPUT_STYLE} }}")
        form.addRow("内容:", self.content_edit)

        self.sentiment_combo = QComboBox()
        self.sentiment_combo.addItems(["积极", "中立", "消极"])
        self.sentiment_combo.setStyleSheet(f"QComboBox {{ {INPUT_STYLE} }}")
        form.addRow("情绪:", self.sentiment_combo)

        self.scope_edit = QLineEdit()
        self.scope_edit.setPlaceholderText("股票代码，多个用逗号分隔（留空表示全局）")
        self.scope_edit.setStyleSheet(f"QLineEdit {{ {INPUT_STYLE} }}")
        form.addRow("影响股票:", self.scope_edit)
        layout.addLayout(form)

        self.publish_button = QPushButton("📢 发布新闻")
        self.publish_button.setStyleSheet(BTN_STYLE_GREEN.replace("padding: 8px 16px", "padding: 12px 24px").replace("font-weight: bold", "font-weight: bold; font-size: 13px"))
        self.publish_button.clicked.connect(self.on_publish_clicked)
        layout.addWidget(self.publish_button)
        layout.addStretch()

    def update_rooms(self, rooms: Dict[str, str]):
        self.available_rooms = rooms
        current_id = self.room_combo.currentData()
        self.room_combo.clear()
        self.room_combo.addItem("-- 请选择房间 --", "")
        for room_id, room_name in sorted(rooms.items()):
            self.room_combo.addItem(f"{room_name} ({room_id})", room_id)
        if current_id and current_id in rooms:
            for i in range(self.room_combo.count()):
                if self.room_combo.itemData(i) == current_id:
                    self.room_combo.setCurrentIndex(i)
                    break

    def get_selected_room_id(self) -> Optional[str]:
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


# ==================== 财报发布器 ====================

class ReportPublisher(QWidget):
    publish_report_signal = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_rooms: Dict[str, str] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        title_label = QLabel("📊 财报发布器")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 8px;")
        layout.addWidget(title_label)

        form = QFormLayout()
        self.room_combo = QComboBox()
        self.room_combo.addItem("-- 请选择房间 --", "")
        self.room_combo.setStyleSheet(f"QComboBox {{ {INPUT_STYLE} }}")
        form.addRow("目标房间:", self.room_combo)

        self.stock_code_edit = QLineEdit()
        self.stock_code_edit.setPlaceholderText("例如：AAPL")
        self.stock_code_edit.setStyleSheet(f"QLineEdit {{ {INPUT_STYLE} }}")
        form.addRow("股票代码:", self.stock_code_edit)

        self.pe_spin = QDoubleSpinBox()
        self.pe_spin.setRange(-1000, 1000)
        self.pe_spin.setValue(20.0)
        self.pe_spin.setDecimals(2)
        self.pe_spin.setStyleSheet(f"QDoubleSpinBox {{ {INPUT_STYLE} }}")
        form.addRow("市盈率 (PE):", self.pe_spin)

        self.roe_spin = QDoubleSpinBox()
        self.roe_spin.setRange(-1.0, 1.0)
        self.roe_spin.setValue(0.15)
        self.roe_spin.setDecimals(4)
        self.roe_spin.setStyleSheet(f"QDoubleSpinBox {{ {INPUT_STYLE} }}")
        form.addRow("净资产收益率 (ROE):", self.roe_spin)

        self.net_income_spin = QDoubleSpinBox()
        self.net_income_spin.setRange(-1e12, 1e12)
        self.net_income_spin.setValue(1000000)
        self.net_income_spin.setPrefix("¥ ")
        self.net_income_spin.setStyleSheet(f"QDoubleSpinBox {{ {INPUT_STYLE} }}")
        form.addRow("净利润:", self.net_income_spin)

        self.revenue_spin = QDoubleSpinBox()
        self.revenue_spin.setRange(0, 1e12)
        self.revenue_spin.setValue(10000000)
        self.revenue_spin.setPrefix("¥ ")
        self.revenue_spin.setStyleSheet(f"QDoubleSpinBox {{ {INPUT_STYLE} }}")
        form.addRow("营收:", self.revenue_spin)

        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 2.0)
        self.weight_spin.setValue(1.0)
        self.weight_spin.setDecimals(2)
        self.weight_spin.setStyleSheet(f"QDoubleSpinBox {{ {INPUT_STYLE} }}")
        form.addRow("策略影响权重:", self.weight_spin)
        layout.addLayout(form)

        self.publish_button = QPushButton("📈 发布财报")
        self.publish_button.setStyleSheet(BTN_STYLE_BLUE.replace("padding: 8px 16px", "padding: 12px 24px").replace("font-weight: bold", "font-weight: bold; font-size: 13px"))
        self.publish_button.clicked.connect(self.on_publish_clicked)
        layout.addWidget(self.publish_button)
        layout.addStretch()

    def update_rooms(self, rooms: Dict[str, str]):
        self.available_rooms = rooms
        current_id = self.room_combo.currentData()
        self.room_combo.clear()
        self.room_combo.addItem("-- 请选择房间 --", "")
        for room_id, room_name in sorted(rooms.items()):
            self.room_combo.addItem(f"{room_name} ({room_id})", room_id)
        if current_id and current_id in rooms:
            for i in range(self.room_combo.count()):
                if self.room_combo.itemData(i) == current_id:
                    self.room_combo.setCurrentIndex(i)
                    break

    def get_selected_room_id(self) -> Optional[str]:
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


# ==================== 机器人管理组件 ====================

class RobotManagementWidget(QWidget):
    create_robot_signal = Signal(dict)
    update_robot_signal = Signal(dict)
    delete_robot_signal = Signal(str)
    list_robots_signal = Signal()
    add_to_room_signal = Signal(dict)
    remove_from_room_signal = Signal(str)
    list_room_robots_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_room_id = None
        self.global_robots = []
        self.room_robots = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        global_group = QGroupBox("🤖 全局机器人池管理")
        global_group.setStyleSheet(GROUPBOX_STYLE)
        global_layout = QVBoxLayout(global_group)

        tb = QHBoxLayout()
        self.create_robot_btn = QPushButton("➕ 创建机器人")
        self.create_robot_btn.setStyleSheet(BTN_STYLE_GREEN)
        self.create_robot_btn.clicked.connect(self.on_create_robot)
        tb.addWidget(self.create_robot_btn)
        self.refresh_global_btn = QPushButton("🔄 刷新")
        self.refresh_global_btn.setStyleSheet(BTN_STYLE_GRAY)
        self.refresh_global_btn.clicked.connect(self.on_refresh_global)
        tb.addWidget(self.refresh_global_btn)
        tb.addStretch()
        global_layout.addLayout(tb)

        self.global_robot_table = QTableWidget()
        self.global_robot_table.setColumnCount(5)
        self.global_robot_table.setHorizontalHeaderLabels(["名称", "策略类型", "初始资金", "状态", "操作"])
        h = self.global_robot_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.global_robot_table.setStyleSheet(TABLE_STYLE)
        global_layout.addWidget(self.global_robot_table)
        main_layout.addWidget(global_group)

        room_group = QGroupBox("🏠 房间机器人池管理")
        room_group.setStyleSheet(GROUPBOX_STYLE)
        room_layout = QVBoxLayout(room_group)

        self.room_info_label = QLabel("未选择房间")
        self.room_info_label.setStyleSheet("color: #888888; padding: 8px;")
        room_layout.addWidget(self.room_info_label)

        rtb = QHBoxLayout()
        self.add_to_room_btn = QPushButton("➕ 添加机器人到房间")
        self.add_to_room_btn.setStyleSheet(BTN_STYLE_BLUE)
        self.add_to_room_btn.clicked.connect(self.on_add_to_room)
        self.add_to_room_btn.setEnabled(False)
        rtb.addWidget(self.add_to_room_btn)
        self.refresh_room_btn = QPushButton("🔄 刷新")
        self.refresh_room_btn.setStyleSheet(BTN_STYLE_GRAY)
        self.refresh_room_btn.clicked.connect(self.on_refresh_room)
        self.refresh_room_btn.setEnabled(False)
        rtb.addWidget(self.refresh_room_btn)
        rtb.addStretch()
        room_layout.addLayout(rtb)

        self.room_robot_table = QTableWidget()
        self.room_robot_table.setColumnCount(5)
        self.room_robot_table.setHorizontalHeaderLabels(["名称", "策略类型", "初始资金", "当前资产", "操作"])
        rh = self.room_robot_table.horizontalHeader()
        for i in range(5):
            rh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.room_robot_table.setStyleSheet(TABLE_STYLE)
        room_layout.addWidget(self.room_robot_table)
        main_layout.addWidget(room_group)

    def set_current_room(self, room_id: str, room_info: dict):
        self.current_room_id = room_id
        self.room_info_label.setText(f"📁 {room_info.get('name', 'Unknown')} ({room_id})")
        self.room_info_label.setStyleSheet("color: #ffffff; padding: 8px;")
        self.add_to_room_btn.setEnabled(True)
        self.refresh_room_btn.setEnabled(True)
        self.list_room_robots_signal.emit(room_id)

    def clear_current_room(self):
        self.current_room_id = None
        self.room_info_label.setText("未选择房间")
        self.room_info_label.setStyleSheet("color: #888888; padding: 8px;")
        self.add_to_room_btn.setEnabled(False)
        self.refresh_room_btn.setEnabled(False)
        self.room_robot_table.setRowCount(0)
        self.room_robots = []

    def update_global_robots(self, robots: List[dict]):
        self.global_robots = robots
        self.global_robot_table.setRowCount(len(robots))
        smap = {"retail": "散户游资", "institution": "正规机构", "trend": "趋势追踪"}
        for row, robot in enumerate(robots):
            self.global_robot_table.setItem(row, 0, QTableWidgetItem(robot.get("name", "")))
            self.global_robot_table.setItem(row, 1, QTableWidgetItem(smap.get(robot.get("strategy_type", ""), "")))
            self.global_robot_table.setItem(row, 2, QTableWidgetItem(f"¥{robot.get('initial_capital', 0):,.2f}"))
            self.global_robot_table.setItem(row, 3, QTableWidgetItem("空闲"))
            bw = QWidget()
            bl = QHBoxLayout(bw)
            bl.setContentsMargins(4, 4, 4, 4)
            eb = QPushButton("修改策略")
            eb.setStyleSheet("QPushButton{background:#2d5d8d;color:#fff;border:none;border-radius:4px;padding:4px 8px;font-size:11px}QPushButton:hover{background:#3d6d9d}")
            eb.clicked.connect(lambda checked, r=robot: self.on_edit_robot(r))
            bl.addWidget(eb)
            db = QPushButton("删除")
            db.setStyleSheet("QPushButton{background:#8d2d2d;color:#fff;border:none;border-radius:4px;padding:4px 8px;font-size:11px}QPushButton:hover{background:#9d3d3d}")
            db.clicked.connect(lambda checked, r=robot: self.on_delete_robot(r))
            bl.addWidget(db)
            bl.addStretch()
            self.global_robot_table.setCellWidget(row, 4, bw)

    def update_room_robots(self, robots: List[dict]):
        self.room_robots = robots
        self.room_robot_table.setRowCount(len(robots))
        smap = {"retail": "散户游资", "institution": "正规机构", "trend": "趋势追踪"}
        for row, robot in enumerate(robots):
            self.room_robot_table.setItem(row, 0, QTableWidgetItem(robot.get("name", "")))
            self.room_robot_table.setItem(row, 1, QTableWidgetItem(smap.get(robot.get("strategy_type", ""), "")))
            self.room_robot_table.setItem(row, 2, QTableWidgetItem(f"¥{robot.get('initial_capital', 0):,.2f}"))
            self.room_robot_table.setItem(row, 3, QTableWidgetItem(f"¥{robot.get('current_cash', 0):,.2f}"))
            rb = QPushButton("移除")
            rb.setStyleSheet("QPushButton{background:#8d5d2d;color:#fff;border:none;border-radius:4px;padding:4px 12px}QPushButton:hover{background:#9d6d3d}")
            rb.clicked.connect(lambda checked, r=robot: self.on_remove_from_room(r))
            self.room_robot_table.setCellWidget(row, 4, rb)

    def on_create_robot(self):
        dialog = CreateRobotDialog(self)
        if dialog.exec() == 1:
            data = dialog.get_robot_data()
            if data:
                self.create_robot_signal.emit(data)

    def on_edit_robot(self, robot: dict):
        dialog = EditRobotStrategyDialog(self, robot)
        if dialog.exec() == 1:
            data = dialog.get_robot_data()
            if data:
                data["robot_id"] = robot.get("id")
                self.update_robot_signal.emit(data)

    def on_delete_robot(self, robot: dict):
        reply = QMessageBox.question(self, "确认删除", f"确定要删除机器人 {robot['name']} 吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.delete_robot_signal.emit(robot.get("id"))

    def on_add_to_room(self):
        if not self.current_room_id:
            QMessageBox.warning(self, "警告", "请先选择一个房间")
            return
        if not self.global_robots:
            QMessageBox.warning(self, "警告", "全局机器人池为空，请先创建机器人")
            return
        dialog = SelectRobotDialog(self, self.global_robots)
        if dialog.exec() == 1:
            selected = dialog.get_selected_robot()
            if selected:
                self.add_to_room_signal.emit({"room_id": self.current_room_id, "robot_id": selected["id"]})

    def on_remove_from_room(self, robot: dict):
        if not self.current_room_id:
            return
        reply = QMessageBox.question(self, "确认移除", f"确定要将机器人 {robot['name']} 从房间移除吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.remove_from_room_signal.emit(robot.get("id"))

    def on_refresh_global(self):
        self.list_robots_signal.emit()

    def on_refresh_room(self):
        if self.current_room_id:
            self.list_room_robots_signal.emit(self.current_room_id)


class CreateRobotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建机器人")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：散户小王")
        layout.addRow("机器人名称:", self.name_edit)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["retail", "institution", "trend"])
        layout.addRow("策略类型:", self.strategy_combo)
        self.capital_spin = QDoubleSpinBox()
        self.capital_spin.setRange(1000, 10000000)
        self.capital_spin.setValue(100000)
        self.capital_spin.setPrefix("¥ ")
        layout.addRow("初始资金:", self.capital_spin)
        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("确定")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addRow(bl)

    def get_robot_data(self) -> Optional[dict]:
        if self.result() == 1:
            name = self.name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "警告", "请填写机器人名称")
                return None
            return {"name": name, "strategy_type": self.strategy_combo.currentText(), "initial_capital": self.capital_spin.value()}
        return None


class EditRobotStrategyDialog(QDialog):
    def __init__(self, parent=None, robot_data: dict = None):
        super().__init__(parent)
        self.robot_data = robot_data or {}
        self.setWindowTitle("修改机器人策略")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        info = QLabel(f"当前机器人：{self.robot_data.get('name', '')}")
        info.setStyleSheet("color: #ffffff; padding: 8px;")
        layout.addRow(info)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["retail", "institution", "trend"])
        idx = self.strategy_combo.findText(self.robot_data.get("strategy_type", "retail"))
        if idx >= 0:
            self.strategy_combo.setCurrentIndex(idx)
        layout.addRow("新策略类型:", self.strategy_combo)
        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("保存")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addRow(bl)

    def get_robot_data(self) -> Optional[dict]:
        if self.result() == 1:
            return {"strategy_type": self.strategy_combo.currentText()}
        return None


class SelectRobotDialog(QDialog):
    def __init__(self, parent=None, robots: List[dict] = None):
        super().__init__(parent)
        self.robots = robots or []
        self.setWindowTitle("选择机器人")
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("从全局机器人池中选择一个机器人添加到房间:"))
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["名称", "策略类型", "初始资金"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setStyleSheet(TABLE_STYLE)
        smap = {"retail": "散户游资", "institution": "正规机构", "trend": "趋势追踪"}
        self.table.setRowCount(len(self.robots))
        for row, robot in enumerate(self.robots):
            self.table.setItem(row, 0, QTableWidgetItem(robot.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(smap.get(robot.get("strategy_type", ""), "")))
            self.table.setItem(row, 2, QTableWidgetItem(f"¥{robot.get('initial_capital', 0):,.2f}"))
        layout.addWidget(self.table)
        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("确定")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addLayout(bl)

    def get_selected_robot(self) -> Optional[dict]:
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return self.robots[row] if row < len(self.robots) else None


# ==================== 股票管理组件 ====================

class StockManagementWidget(QWidget):
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

        global_group = QGroupBox("📈 全局股票池管理")
        global_group.setStyleSheet(GROUPBOX_STYLE)
        global_layout = QVBoxLayout(global_group)

        tb = QHBoxLayout()
        self.create_stock_btn = QPushButton("➕ 创建股票")
        self.create_stock_btn.setStyleSheet(BTN_STYLE_GREEN)
        self.create_stock_btn.clicked.connect(self.on_create_stock)
        tb.addWidget(self.create_stock_btn)
        self.refresh_global_btn = QPushButton("🔄 刷新")
        self.refresh_global_btn.setStyleSheet(BTN_STYLE_GRAY)
        self.refresh_global_btn.clicked.connect(self.on_refresh_global)
        tb.addWidget(self.refresh_global_btn)
        tb.addStretch()
        global_layout.addLayout(tb)

        self.global_stock_table = QTableWidget()
        self.global_stock_table.setColumnCount(6)
        self.global_stock_table.setHorizontalHeaderLabels(["代码", "名称", "初始价格", "发行量", "描述", "操作"])
        h = self.global_stock_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.Stretch)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.global_stock_table.setStyleSheet(TABLE_STYLE)
        global_layout.addWidget(self.global_stock_table)
        main_layout.addWidget(global_group)

        room_group = QGroupBox("🏠 房间股票池管理")
        room_group.setStyleSheet(GROUPBOX_STYLE)
        room_layout = QVBoxLayout(room_group)

        self.room_info_label = QLabel("未选择房间")
        self.room_info_label.setStyleSheet("color: #888888; padding: 8px;")
        room_layout.addWidget(self.room_info_label)

        rtb = QHBoxLayout()
        self.add_to_room_btn = QPushButton("➕ 添加股票到房间")
        self.add_to_room_btn.setStyleSheet(BTN_STYLE_BLUE)
        self.add_to_room_btn.clicked.connect(self.on_add_to_room)
        self.add_to_room_btn.setEnabled(False)
        rtb.addWidget(self.add_to_room_btn)
        self.refresh_room_btn = QPushButton("🔄 刷新")
        self.refresh_room_btn.setStyleSheet(BTN_STYLE_GRAY)
        self.refresh_room_btn.clicked.connect(self.on_refresh_room)
        self.refresh_room_btn.setEnabled(False)
        rtb.addWidget(self.refresh_room_btn)
        rtb.addStretch()
        room_layout.addLayout(rtb)

        self.room_stock_table = QTableWidget()
        self.room_stock_table.setColumnCount(6)
        self.room_stock_table.setHorizontalHeaderLabels(["代码", "名称", "当前价格", "初始价格", "发行量", "操作"])
        rh = self.room_stock_table.horizontalHeader()
        for i in range(6):
            rh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.room_stock_table.setStyleSheet(TABLE_STYLE)
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
            eb = QPushButton("编辑")
            eb.setStyleSheet("QPushButton{background:#2d5d8d;color:#fff;border:none;border-radius:4px;padding:4px 12px}QPushButton:hover{background:#3d6d9d}")
            eb.clicked.connect(lambda checked, s=stock: self.on_edit_stock(s))
            self.global_stock_table.setCellWidget(row, 5, eb)

    def update_room_stocks(self, stocks: List[dict]):
        self.room_stocks = stocks
        self.room_stock_table.setRowCount(len(stocks))
        for row, stock in enumerate(stocks):
            self.room_stock_table.setItem(row, 0, QTableWidgetItem(stock.get("code", "")))
            self.room_stock_table.setItem(row, 1, QTableWidgetItem(stock.get("name", "")))
            self.room_stock_table.setItem(row, 2, QTableWidgetItem(f"¥{stock.get('current_price', 0):,.2f}"))
            self.room_stock_table.setItem(row, 3, QTableWidgetItem(f"¥{stock.get('initial_price', 0):,.2f}"))
            self.room_stock_table.setItem(row, 4, QTableWidgetItem(f"{stock.get('issued_shares', 0):,}"))
            rb = QPushButton("移除")
            rb.setStyleSheet("QPushButton{background:#8d2d2d;color:#fff;border:none;border-radius:4px;padding:4px 12px}QPushButton:hover{background:#9d3d3d}")
            rb.clicked.connect(lambda checked, s=stock: self.on_remove_from_room(s))
            self.room_stock_table.setCellWidget(row, 5, rb)

    def on_create_stock(self):
        dialog = CreateStockDialog(self)
        if dialog.exec() == 1:
            data = dialog.get_stock_data()
            if data:
                self.create_stock_signal.emit(data)

    def on_edit_stock(self, stock: dict):
        dialog = EditStockDialog(self, stock)
        if dialog.exec() == 1:
            data = dialog.get_stock_data()
            if data:
                data["stock_id"] = stock.get("id")
                self.update_stock_signal.emit(data)

    def on_add_to_room(self):
        if not self.current_room_id:
            QMessageBox.warning(self, "警告", "请先选择一个房间")
            return
        dialog = SelectStockDialog(self, self.all_stocks)
        if dialog.exec() == 1:
            selected = dialog.get_selected_stock()
            if selected:
                price, ok = QInputDialog.getDouble(self, "设定初始价格", f"为 {selected['code']} 设定初始价格:", selected.get("initial_price", 100.0), 0.01, 1e9, 2)
                if ok:
                    self.add_to_room_signal.emit({"room_id": self.current_room_id, "stock_code": selected["code"], "current_price": price})

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
        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("确定")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addRow(bl)

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
        self.setWindowTitle("编辑股票")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        self.code_edit = QLineEdit(self.stock_data.get("code", ""))
        layout.addRow("股票代码:", self.code_edit)
        self.name_edit = QLineEdit(self.stock_data.get("name", ""))
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
        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("保存")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addRow(bl)

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
        self.setWindowTitle("选择股票")
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("从全局股票池中选择一个股票添加到房间:"))
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "初始价格", "发行量"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.setRowCount(len(self.stocks))
        for row, stock in enumerate(self.stocks):
            self.table.setItem(row, 0, QTableWidgetItem(stock.get("code", "")))
            self.table.setItem(row, 1, QTableWidgetItem(stock.get("name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(f"¥{stock.get('initial_price', 0):,.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{stock.get('issued_shares', 0):,}"))
        layout.addWidget(self.table)
        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("确定")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addLayout(bl)

    def get_selected_stock(self) -> Optional[dict]:
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return self.stocks[row] if row < len(self.stocks) else None


# ==================== 调试控制台组件 ====================

class DebugConsoleWidget(QWidget):
    """调试控制台 - 显示所有 WebSocket 通信、系统日志和错误信息"""

    # 最大行数限制，防止内存溢出
    MAX_LINES = 5000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._auto_scroll = True
        self._show_sent = True
        self._show_received = True
        self._show_system = True
        self._show_error = True
        self._line_count = 0
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── 标题 ──
        title_label = QLabel("🔧 调试控制台")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 4px 0;")
        layout.addWidget(title_label)

        # ── 工具栏 ──
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.line_count_label = QLabel("共 0 条")
        self.line_count_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        toolbar.addWidget(self.line_count_label)

        toolbar.addStretch()

        # 过滤复选框
        self.filter_sent_check = QCheckBox("📤 发送")
        self.filter_sent_check.setChecked(True)
        self.filter_sent_check.setStyleSheet("color: #4fc3f7; font-size: 11px;")
        self.filter_sent_check.stateChanged.connect(lambda s: setattr(self, '_show_sent', s == Qt.Checked))
        toolbar.addWidget(self.filter_sent_check)

        self.filter_recv_check = QCheckBox("📥 接收")
        self.filter_recv_check.setChecked(True)
        self.filter_recv_check.setStyleSheet("color: #81c784; font-size: 11px;")
        self.filter_recv_check.stateChanged.connect(lambda s: setattr(self, '_show_received', s == Qt.Checked))
        toolbar.addWidget(self.filter_recv_check)

        self.filter_system_check = QCheckBox("⚙️ 系统")
        self.filter_system_check.setChecked(True)
        self.filter_system_check.setStyleSheet("color: #ffb74d; font-size: 11px;")
        self.filter_system_check.stateChanged.connect(lambda s: setattr(self, '_show_system', s == Qt.Checked))
        toolbar.addWidget(self.filter_system_check)

        self.filter_error_check = QCheckBox("❌ 错误")
        self.filter_error_check.setChecked(True)
        self.filter_error_check.setStyleSheet("color: #e57373; font-size: 11px;")
        self.filter_error_check.stateChanged.connect(lambda s: setattr(self, '_show_error', s == Qt.Checked))
        toolbar.addWidget(self.filter_error_check)

        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.setStyleSheet("color: #cccccc; font-size: 11px;")
        self.auto_scroll_check.stateChanged.connect(lambda s: setattr(self, '_auto_scroll', s == Qt.Checked))
        toolbar.addWidget(self.auto_scroll_check)

        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setStyleSheet(BTN_STYLE_GRAY)
        self.clear_btn.clicked.connect(self.clear_console)
        toolbar.addWidget(self.clear_btn)

        layout.addLayout(toolbar)

        # ── 控制台文本区域 ──
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setLineWrapMode(QTextEdit.NoWrap)  # 不自动换行，确保长内容完整显示
        self.console_text.setStyleSheet(
            "QTextEdit { background-color: #0d0d0d; color: #cccccc; "
            "border: 1px solid #333333; border-radius: 4px; "
            "font-family: 'Consolas', 'Courier New', 'Microsoft YaHei'; "
            "font-size: 11px; padding: 6px; }"
        )
        layout.addWidget(self.console_text, 1)  # stretch=1 让文本区域占满剩余空间

        # ── 连接状态栏 ──
        status_bar = QHBoxLayout()
        self.connection_status = QLabel("● 未连接")
        self.connection_status.setStyleSheet("color: #e57373; font-size: 12px; font-weight: bold;")
        status_bar.addWidget(self.connection_status)
        status_bar.addStretch()
        self.msg_stats_label = QLabel("发送: 0 | 接收: 0 | 错误: 0")
        self.msg_stats_label.setStyleSheet("color: #888888; font-size: 11px;")
        status_bar.addWidget(self.msg_stats_label)
        layout.addLayout(status_bar)

        # 统计计数
        self._sent_count = 0
        self._recv_count = 0
        self._error_count = 0

    def _get_timestamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def _append_line(self, html_line: str):
        """追加一行到控制台，带行数限制"""
        self.console_text.append(html_line)
        self._line_count += 1
        self.line_count_label.setText(f"共 {self._line_count} 条")

        # 超过最大行数时截断前面的内容
        if self._line_count > self.MAX_LINES:
            cursor = self.console_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, self._line_count - self.MAX_LINES)
            cursor.removeSelectedText()
            self._line_count = self.MAX_LINES

        # 自动滚动
        if self._auto_scroll:
            cursor = self.console_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.console_text.setTextCursor(cursor)
            self.console_text.ensureCursorVisible()

    def _update_stats(self):
        self.msg_stats_label.setText(
            f"发送: {self._sent_count} | 接收: {self._recv_count} | 错误: {self._error_count}"
        )

    def log_sent(self, msg_type: str, data_summary: str):
        """记录发送的消息"""
        if not self._show_sent:
            return
        self._sent_count += 1
        self._update_stats()
        ts = self._get_timestamp()
        # 对 data_summary 进行 HTML 转义
        safe_summary = data_summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        line = (
            f'<span style="color:#555555;">[{ts}]</span> '
            f'<span style="color:#4fc3f7;">📤 SEND</span> '
            f'<span style="color:#64b5f6;">{msg_type}</span> '
            f'<span style="color:#90a4ae;">{safe_summary}</span>'
        )
        self._append_line(line)

    def log_received(self, msg_type: str, data_summary: str):
        """记录接收的消息"""
        if not self._show_received:
            return
        self._recv_count += 1
        self._update_stats()
        ts = self._get_timestamp()
        safe_summary = data_summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        line = (
            f'<span style="color:#555555;">[{ts}]</span> '
            f'<span style="color:#81c784;">📥 RECV</span> '
            f'<span style="color:#a5d6a7;">{msg_type}</span> '
            f'<span style="color:#90a4ae;">{safe_summary}</span>'
        )
        self._append_line(line)

    def log_system(self, message: str):
        """记录系统事件"""
        if not self._show_system:
            return
        ts = self._get_timestamp()
        safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        line = (
            f'<span style="color:#555555;">[{ts}]</span> '
            f'<span style="color:#ffb74d;">⚙️ SYS </span> '
            f'<span style="color:#ffe0b2;">{safe_msg}</span>'
        )
        self._append_line(line)

    def log_error(self, message: str):
        """记录错误信息"""
        self._error_count += 1
        self._update_stats()
        if not self._show_error:
            return
        ts = self._get_timestamp()
        safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        line = (
            f'<span style="color:#555555;">[{ts}]</span> '
            f'<span style="color:#e57373;">❌ ERR </span> '
            f'<span style="color:#ef9a9a;">{safe_msg}</span>'
        )
        self._append_line(line)

    def log_python_logging(self, message: str, level: int):
        """记录 Python logging 输出"""
        if level >= logging.ERROR:
            self.log_error(message)
        elif level >= logging.WARNING:
            if not self._show_system:
                return
            ts = self._get_timestamp()
            safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            line = (
                f'<span style="color:#555555;">[{ts}]</span> '
                f'<span style="color:#fff176;">⚠️ WARN</span> '
                f'<span style="color:#fff9c4;">{safe_msg}</span>'
            )
            self._append_line(line)
        else:
            self.log_system(message)

    def set_connected(self, connected: bool):
        """更新连接状态显示"""
        if connected:
            self.connection_status.setText("● 已连接")
            self.connection_status.setStyleSheet("color: #81c784; font-size: 12px; font-weight: bold;")
        else:
            self.connection_status.setText("● 未连接")
            self.connection_status.setStyleSheet("color: #e57373; font-size: 12px; font-weight: bold;")

    def clear_console(self):
        """清空控制台"""
        self.console_text.clear()
        self._line_count = 0
        self._sent_count = 0
        self._recv_count = 0
        self._error_count = 0
        self.line_count_label.setText("共 0 条")
        self._update_stats()


# ==================== 创建房间对话框 ====================

class CreateRoomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("确定")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addRow(bl)

    def get_room_data(self) -> Optional[dict]:
        if self.result() == 1:
            mode_map = {"秒级": "second", "小时级": "hour", "天级": "day", "月级": "month"}
            return {"name": self.name_edit.text(), "step_mode": mode_map[self.mode_combo.currentText()], "initial_capital": self.capital_spin.value()}
        return None


# ==================== 管理员主窗口 ====================

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
        self.setup_logging_redirect()
        # 参与者列表自动刷新定时器（每 5 秒轮询一次）
        self.participant_refresh_timer = QTimer(self)
        self.participant_refresh_timer.setInterval(5000)
        self.participant_refresh_timer.timeout.connect(self._auto_refresh_participants)
        self.connect_to_server()

    def setup_ui(self):
        self.setWindowTitle("Stonk - 管理员控制台")
        self.setMinimumSize(1400, 900)
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        self.create_room_button = QPushButton("➕ 创建房间")
        self.create_room_button.setStyleSheet(BTN_STYLE_GREEN)
        toolbar.addWidget(self.create_room_button)
        self.refresh_button = QPushButton("🔄 刷新")
        self.refresh_button.setStyleSheet(BTN_STYLE_GRAY)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧：房间列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_lbl = QLabel("📋 房间列表")
        left_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        left_lbl.setStyleSheet("color: #ffffff; padding: 8px;")
        left_layout.addWidget(left_lbl)
        self.room_list = QTableWidget()
        self.room_list.setColumnCount(5)
        self.room_list.setHorizontalHeaderLabels(["名称", "模式", "状态", "人数", "机器人"])
        self.room_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.room_list.setSelectionMode(QTableWidget.SingleSelection)
        self.room_list.itemSelectionChanged.connect(self.on_room_selected)
        self.room_list.setStyleSheet(TABLE_STYLE)
        left_layout.addWidget(self.room_list)
        splitter.addWidget(left_panel)

        # 右侧：标签页
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #444444; border-radius: 4px; background-color: #1e1e1e; }"
            "QTabBar::tab { background-color: #3c3c3c; color: #ffffff; padding: 10px 20px; margin-right: 2px; }"
            "QTabBar::tab:selected { background-color: #1e1e1e; }"
        )

        # 房间控制（含参与者列表 + 操作日志）
        self.room_control = RoomControlWidget()
        self.tabs.addTab(self.room_control, "🏠 房间控制")

        # 新闻发布
        self.news_publisher = NewsPublisher()
        self.tabs.addTab(self.news_publisher, "📰 新闻发布")

        # 财报发布
        self.report_publisher = ReportPublisher()
        self.tabs.addTab(self.report_publisher, "📊 财报发布")

        # 机器人管理
        self.robot_management = RobotManagementWidget()
        self.tabs.addTab(self.robot_management, "🤖 机器人管理")

        # 股票管理
        self.stock_management = StockManagementWidget()
        self.tabs.addTab(self.stock_management, "📈 股票管理")

        # 调试控制台
        self.debug_console = DebugConsoleWidget()
        self.tabs.addTab(self.debug_console, "🔧 调试控制台")

        right_layout.addWidget(self.tabs)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)

    def setup_styles(self):
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }")

    def connect_signals(self):
        self.create_room_button.clicked.connect(self.on_create_room)
        self.refresh_button.clicked.connect(self.on_refresh)
        self.room_control.control_signal.connect(self.on_room_control)
        self.room_control.refresh_participants_signal.connect(self.on_list_room_participants)
        self.room_control.get_operation_log_signal.connect(self.on_get_operation_log)
        self.room_control.kick_user_signal.connect(self.on_kick_user)
        self.news_publisher.publish_news_signal.connect(self.on_publish_news)
        self.report_publisher.publish_report_signal.connect(self.on_publish_report)
        self.robot_management.create_robot_signal.connect(self.on_create_robot)
        self.robot_management.update_robot_signal.connect(self.on_update_robot)
        self.robot_management.delete_robot_signal.connect(self.on_delete_robot)
        self.robot_management.list_robots_signal.connect(self.on_list_robots)
        self.robot_management.add_to_room_signal.connect(self.on_add_robot_to_room)
        self.robot_management.remove_from_room_signal.connect(self.on_remove_robot_from_room)
        self.robot_management.list_room_robots_signal.connect(self.on_list_room_robots)
        self.stock_management.create_stock_signal.connect(self.on_create_stock)
        self.stock_management.update_stock_signal.connect(self.on_update_stock)
        self.stock_management.list_stocks_signal.connect(self.on_list_stocks)
        self.stock_management.add_to_room_signal.connect(self.on_add_stock_to_room)
        self.stock_management.remove_from_room_signal.connect(self.on_remove_stock_from_room)
        self.stock_management.list_room_stocks_signal.connect(self.on_list_room_stocks)

    def setup_logging_redirect(self):
        """将 Python logging 输出重定向到调试控制台"""
        qt_handler = QtLogHandler(self.debug_console.log_python_logging)
        qt_handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
        qt_handler.setLevel(logging.DEBUG)
        # 添加到根 logger，捕获所有模块的日志
        root_logger = logging.getLogger()
        root_logger.addHandler(qt_handler)
        self.debug_console.log_system("调试控制台已启动，正在捕获所有日志输出...")

    def connect_to_server(self):
        self.debug_console.log_system(f"正在连接到服务器 ws://{HOST}:{PORT} ...")
        self.ws_client = WebSocketClientThread(HOST, PORT)
        self.ws_client.connected_signal.connect(self.on_connected)
        self.ws_client.disconnected_signal.connect(self.on_disconnected)
        self.ws_client.message_received_signal.connect(self.on_message_received)
        self.ws_client.error_signal.connect(self.on_connection_error)
        self.ws_client.start()

    def on_connected(self):
        self.connected = True
        self.statusBar().showMessage("已连接到服务器", 5000)
        self.debug_console.set_connected(True)
        self.debug_console.log_system(f"已成功连接到服务器 ws://{HOST}:{PORT}")
        self.request_room_list()
        self.on_list_stocks()

    def on_disconnected(self):
        self.connected = False
        self.statusBar().showMessage("与服务器断开连接", 5000)
        self.debug_console.set_connected(False)
        self.debug_console.log_error("与服务器断开连接")
        self._stop_participant_refresh_timer()

    def on_connection_error(self, error: str):
        self.connected = False
        self.statusBar().showMessage(error, 10000)
        self.debug_console.set_connected(False)
        self.debug_console.log_error(f"连接错误: {error}")

    def _summarize_data(self, data: dict, max_len: int = 200) -> str:
        """生成消息数据的摘要，用于调试控制台显示"""
        try:
            summary = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            if len(summary) > max_len:
                return summary[:max_len] + "..."
            return summary
        except Exception:
            return str(data)[:max_len]

    def on_message_received(self, message: dict):
        msg_type = message.get("type")
        data = message.get("data", {})

        # 记录到调试控制台
        self.debug_console.log_received(
            msg_type or "UNKNOWN",
            self._summarize_data(data)
        )

        if msg_type == MessageType.ROOM_LIST.value:
            self.update_room_list(data.get("rooms", []))
        elif msg_type == MessageType.SUCCESS.value:
            self.statusBar().showMessage(data.get("message", "操作成功"), 3000)
            QTimer.singleShot(300, self.request_room_list)
        elif msg_type == MessageType.ERROR.value:
            self.statusBar().showMessage(f"错误：{data.get('error', '未知错误')}", 5000)
            self.debug_console.log_error(f"服务器返回错误: {data.get('error', '未知错误')}")
        elif msg_type == MessageType.STOCK_LIST.value:
            self.stock_management.update_global_stocks(data.get("stocks", []))
        elif msg_type == MessageType.ROOM_STOCK_LIST.value:
            if data.get("room_id") == self.current_room_id:
                self.stock_management.update_room_stocks(data.get("stocks", []))
        elif msg_type == MessageType.ROBOT_LIST.value:
            self.robot_management.update_global_robots(data.get("robots", []))
        elif msg_type == MessageType.ROOM_ROBOT_LIST.value:
            if data.get("room_id") == self.current_room_id:
                self.robot_management.update_room_robots(data.get("robots", []))
        elif msg_type == MessageType.ROOM_PARTICIPANT_LIST.value:
            recv_room_id = data.get("room_id")
            users = data.get("users", [])
            robots = data.get("robots", [])
            self.debug_console.log_system(
                f"收到参与者列表: room_id={recv_room_id}, "
                f"current_room_id={self.current_room_id}, "
                f"匹配={'是' if recv_room_id == self.current_room_id else '否'}, "
                f"真人={len(users)}, 机器人={len(robots)}"
            )
            if recv_room_id == self.current_room_id:
                self.room_control.update_participants(users, robots)
        elif msg_type == MessageType.STEP_READY_UPDATE.value:
            recv_room_id = data.get("room_id")
            if recv_room_id == self.current_room_id:
                users_info = data.get("users", [])
                ready_count = data.get("ready_count", 0)
                total_count = data.get("total_count", 0)
                self.room_control.update_ready_status(users_info, ready_count, total_count)
        elif msg_type == MessageType.OPERATION_LOG.value:
            room_id = data.get("room_id")
            if room_id == self.current_room_id:
                if data.get("is_full_log"):
                    self.room_control.load_full_operation_log(data.get("entries", []))
                else:
                    entry = data.get("entry")
                    if entry:
                        self.room_control.add_operation_log_entry(entry)

    def send_message(self, message):
        if self.ws_client and self.connected:
            # 记录到调试控制台
            try:
                if isinstance(message, str):
                    parsed = json.loads(message)
                else:
                    parsed = message
                msg_type = parsed.get("type", "UNKNOWN")
                data = parsed.get("data", {})
                self.debug_console.log_sent(msg_type, self._summarize_data(data))
            except Exception:
                self.debug_console.log_sent("RAW", str(message)[:200])
            self.ws_client.send_message(message)
        else:
            self.statusBar().showMessage("未连接到服务器", 3000)
            self.debug_console.log_error("发送失败: 未连接到服务器")

    def request_room_list(self):
        self.send_message(create_message(MessageType.ROOM_LIST, {}))

    def on_create_room(self):
        dialog = CreateRoomDialog(self)
        if dialog.exec() == 1:
            data = dialog.get_room_data()
            if data:
                self.send_message(create_message(MessageType.CREATE_ROOM, data))
                QTimer.singleShot(500, self.request_room_list)

    def on_refresh(self):
        self.request_room_list()

    def on_room_control(self, action: str, data: dict):
        if not self.current_room_id:
            QMessageBox.warning(self, "警告", "请先选择一个房间")
            return
        message_map = {
            "step_forward": MessageType.ADMIN_STEP_FORWARD,
            "fast_forward": MessageType.ADMIN_FAST_FORWARD,
            "pause": MessageType.ADMIN_PAUSE,
            "resume": MessageType.ADMIN_RESUME,
            "destroy_room": MessageType.ADMIN_DESTROY_ROOM
        }
        msg_type = message_map.get(action)
        if msg_type:
            payload = {"room_id": self.current_room_id, **data}
            if action == "fast_forward":
                payload["start"] = True
                payload["speed"] = self.room_control.speed_spin.value()
            self.send_message(create_message(msg_type, payload))

    def on_publish_news(self, news_data: dict):
        if not news_data.get("room_id"):
            QMessageBox.warning(self, "警告", "请先选择要发布新闻的房间")
            return
        self.send_message(create_message(MessageType.ADMIN_PUBLISH_NEWS, news_data))

    def on_publish_report(self, report_data: dict):
        if not report_data.get("room_id"):
            QMessageBox.warning(self, "警告", "请先选择要发布财报的房间")
            return
        self.send_message(create_message(MessageType.ADMIN_PUBLISH_REPORT, report_data))

    def on_list_room_participants(self, room_id: str):
        self.send_message(create_message(MessageType.ADMIN_LIST_ROOM_PARTICIPANTS, {"room_id": room_id}))

    def on_get_operation_log(self, room_id: str):
        self.send_message(create_message(MessageType.ADMIN_GET_OPERATION_LOG, {"room_id": room_id}))

    def on_kick_user(self, user_id: str):
        pass  # 暂未实现

    def on_create_robot(self, data: dict):
        self.send_message(create_message(MessageType.ADMIN_CREATE_ROBOT, data))

    def on_update_robot(self, data: dict):
        self.send_message(create_message(MessageType.ADMIN_SET_ROBOT_STRATEGY, data))

    def on_delete_robot(self, robot_id: str):
        self.send_message(create_message(MessageType.ADMIN_DELETE_ROBOT, {"robot_id": robot_id}))

    def on_list_robots(self):
        self.send_message(create_message(MessageType.ADMIN_LIST_ROBOTS, {}))

    def on_add_robot_to_room(self, data: dict):
        self.send_message(create_message(MessageType.ADMIN_ADD_ROBOT_TO_ROOM, data))

    def on_remove_robot_from_room(self, robot_id: str):
        self.send_message(create_message(MessageType.ADMIN_REMOVE_ROBOT_FROM_ROOM, {"robot_id": robot_id}))

    def on_list_room_robots(self, room_id: str):
        self.send_message(create_message(MessageType.ADMIN_LIST_ROOM_ROBOTS, {"room_id": room_id}))

    def on_create_stock(self, data: dict):
        self.send_message(create_message(MessageType.ADMIN_CREATE_STOCK, data))

    def on_update_stock(self, data: dict):
        self.send_message(create_message(MessageType.ADMIN_UPDATE_STOCK, data))

    def on_list_stocks(self):
        self.send_message(create_message(MessageType.ADMIN_LIST_STOCKS, {}))

    def on_add_stock_to_room(self, data: dict):
        self.send_message(create_message(MessageType.ADMIN_ADD_STOCK_TO_ROOM, data))

    def on_remove_stock_from_room(self, data: dict):
        self.send_message(create_message(MessageType.ADMIN_REMOVE_STOCK_FROM_ROOM, data))

    def on_list_room_stocks(self, room_id: str):
        self.send_message(create_message(MessageType.ADMIN_LIST_ROOM_STOCKS, {"room_id": room_id}))

    def update_room_list(self, rooms: List[dict]):
        prev_room_id = self.current_room_id
        self.rooms_data = {room["id"]: room for room in rooms}

        # 阻塞信号，防止重建列表时误触发 on_room_selected
        self.room_list.blockSignals(True)
        self.room_list.setRowCount(len(rooms))
        for row, room in enumerate(rooms):
            name_item = QTableWidgetItem(room.get("name", ""))
            name_item.setData(Qt.UserRole, room["id"])  # 将 room_id 存入 item，避免依赖 dict 顺序
            self.room_list.setItem(row, 0, name_item)
            self.room_list.setItem(row, 1, QTableWidgetItem(room.get("step_mode", "")))
            self.room_list.setItem(row, 2, QTableWidgetItem(room.get("status", "")))
            self.room_list.setItem(row, 3, QTableWidgetItem(str(room.get("user_count", 0))))
            self.room_list.setItem(row, 4, QTableWidgetItem(str(room.get("robot_count", 0))))

        # 恢复之前的选中状态（静默恢复，不触发 on_room_selected）
        if prev_room_id and prev_room_id in self.rooms_data:
            for row in range(self.room_list.rowCount()):
                item = self.room_list.item(row, 0)
                if item and item.data(Qt.UserRole) == prev_room_id:
                    self.room_list.selectRow(row)
                    break
            # 用最新数据刷新房间信息标签（状态/步数/模式可能已变化）
            self.room_control.set_room(prev_room_id, self.rooms_data[prev_room_id])

        self.room_list.blockSignals(False)

        rooms_dict = {room["id"]: room.get("name", "Unknown") for room in rooms}
        self.news_publisher.update_rooms(rooms_dict)
        self.report_publisher.update_rooms(rooms_dict)

    def on_room_selected(self):
        selected = self.room_list.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        name_item = self.room_list.item(row, 0)
        if not name_item:
            return
        # 从 item 数据中读取 room_id，避免依赖 dict 键顺序
        room_id = name_item.data(Qt.UserRole)
        if not room_id:
            return

        # 若选中的是同一个房间，跳过（避免重复请求）
        if room_id == self.current_room_id:
            return

        room_info = self.rooms_data.get(room_id, {})
        self.current_room_id = room_id

        # 更新房间控制
        self.room_control.set_room(room_id, room_info)

        # 更新机器人管理
        self.robot_management.set_current_room(room_id, room_info)

        # 更新股票管理
        self.stock_management.set_current_room(room_id, room_info)

        # 自动刷新参与者列表和操作日志
        self.on_list_room_participants(room_id)
        self.on_get_operation_log(room_id)

        # 启动参与者列表自动刷新定时器
        self._start_participant_refresh_timer()

    def _auto_refresh_participants(self):
        """定时自动刷新参与者列表（每 5 秒）"""
        if self.current_room_id and self.connected:
            self.on_list_room_participants(self.current_room_id)

    def _start_participant_refresh_timer(self):
        """启动参与者列表自动刷新定时器"""
        if not self.participant_refresh_timer.isActive():
            self.participant_refresh_timer.start()
            self.debug_console.log_system("参与者列表自动刷新已启动（每 5 秒）")

    def _stop_participant_refresh_timer(self):
        """停止参与者列表自动刷新定时器"""
        if self.participant_refresh_timer.isActive():
            self.participant_refresh_timer.stop()

    def closeEvent(self, event):
        self._stop_participant_refresh_timer()
        if self.ws_client:
            self.ws_client.stop()
            self.ws_client.wait(2000)
        event.accept()


def run_admin_ui():
    """启动管理员 UI"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(
        "QWidget { background-color: #1e1e1e; color: #ffffff; font-family: 'Microsoft YaHei', 'Segoe UI'; font-size: 12px; }"
        "QLabel { color: #ffffff; }"
        "QLineEdit { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }"
        "QTextEdit { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }"
        "QComboBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }"
        "QComboBox::drop-down { border: none; }"
        "QComboBox QAbstractItemView { background-color: #3c3c3c; color: #ffffff; selection-background-color: #3a7abd; }"
        "QDoubleSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }"
        "QSpinBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 6px; }"
        "QScrollBar:vertical { background-color: #2b2b2b; width: 12px; }"
        "QScrollBar::handle:vertical { background-color: #555555; border-radius: 6px; min-height: 20px; }"
        "QScrollBar:horizontal { background-color: #2b2b2b; height: 12px; }"
        "QScrollBar::handle:horizontal { background-color: #555555; border-radius: 6px; min-width: 20px; }"
        "QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }"
        "QCheckBox { color: #cccccc; }"
        "QDialog { background-color: #2b2b2b; }"
        "QStatusBar { background-color: #1e1e1e; color: #aaaaaa; }"
    )
    window = AdminMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_admin_ui()
