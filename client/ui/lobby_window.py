"""
Stonk - 大厅界面

房间列表和房间管理界面。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QDialog, QSpinBox, QComboBox
)
from PySide6.QtCore import Signal, Qt
from client.ui.widgets import StylizedButton, StylizedLineEdit, StylizedLabel
from client.config import COLORS


class LobbyWindow(QWidget):
    """大厅界面"""
    
    # 信号
    room_joined = Signal(str)  # room_id
    logout_requested = Signal()
    refresh_requested = Signal()
    create_room_requested = Signal(str, str, float)  # name, step_mode, initial_capital
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 标题和按钮
        title_layout = QHBoxLayout()
        title = StylizedLabel("房间大厅")
        title.set_title_style()
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = StylizedButton("刷新")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        title_layout.addWidget(refresh_btn)
        
        # 创建房间按钮
        create_btn = StylizedButton("创建房间")
        create_btn.set_success_style()
        create_btn.clicked.connect(self._on_create_room_clicked)
        title_layout.addWidget(create_btn)
        
        # 登出按钮
        logout_btn = StylizedButton("登出")
        logout_btn.set_danger_style()
        logout_btn.clicked.connect(self.logout_requested.emit)
        title_layout.addWidget(logout_btn)
        
        layout.addLayout(title_layout)
        
        # 房间表格
        self.room_table = QTableWidget()
        self.room_table.setColumnCount(6)
        self.room_table.setHorizontalHeaderLabels([
            "房间名称", "步进模式", "状态", "人数", "机器人数", "操作"
        ])
        self.room_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['info']};
                gridline-color: {COLORS['info']};
            }}
            QHeaderView::section {{
                background-color: #0a0a0a;
                color: {COLORS['text']};
                padding: 5px;
                border: none;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
        """)
        self.room_table.setAlternatingRowColors(True)
        self.room_table.resizeColumnsToContents()
        layout.addWidget(self.room_table)
        
        self.setLayout(layout)
    
    def _on_create_room_clicked(self):
        """处理创建房间按钮点击"""
        dialog = CreateRoomDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, step_mode, initial_capital = dialog.get_values()
            self.create_room_requested.emit(name, step_mode, initial_capital)
    
    def load_rooms(self, rooms: list):
        """加载房间列表"""
        self.room_table.setRowCount(len(rooms))
        
        for row, room in enumerate(rooms):
            # 房间名称
            name_item = QTableWidgetItem(room["name"])
            name_item.setForeground(Qt.white)
            self.room_table.setItem(row, 0, name_item)
            
            # 步进模式
            mode_map = {
                "second": "秒级",
                "hour": "小时级",
                "day": "天级",
                "month": "月级"
            }
            mode_item = QTableWidgetItem(mode_map.get(room["step_mode"], room["step_mode"]))
            mode_item.setForeground(Qt.white)
            self.room_table.setItem(row, 1, mode_item)
            
            # 状态
            status_map = {
                "running": "运行中",
                "paused": "暂停",
                "fast_forward": "快进中",
                "completed": "已完成"
            }
            status_item = QTableWidgetItem(status_map.get(room["status"], room["status"]))
            status_item.setForeground(Qt.white)
            self.room_table.setItem(row, 2, status_item)
            
            # 人数
            user_count_item = QTableWidgetItem(str(room["user_count"]))
            user_count_item.setForeground(Qt.white)
            self.room_table.setItem(row, 3, user_count_item)
            
            # 机器人数
            robot_count_item = QTableWidgetItem(str(room["robot_count"]))
            robot_count_item.setForeground(Qt.white)
            self.room_table.setItem(row, 4, robot_count_item)
            
            # 操作按钮
            join_btn = StylizedButton("加入")
            join_btn.set_success_style()
            room_id = room["id"]
            join_btn.clicked.connect(lambda checked, rid=room_id: self.room_joined.emit(rid))
            self.room_table.setCellWidget(row, 5, join_btn)
        
        self.room_table.resizeColumnsToContents()


class CreateRoomDialog(QDialog):
    """创建房间对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建房间")
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        self.setGeometry(100, 100, 400, 300)
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # 房间名称
        name_label = StylizedLabel("房间名称")
        self.name_input = StylizedLineEdit()
        self.name_input.setPlaceholderText("输入房间名称")
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        
        # 步进模式
        mode_label = StylizedLabel("步进模式")
        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['info']};
                border-radius: 4px;
                padding: 5px;
            }}
        """)
        self.mode_combo.addItems(["秒级 (second)", "小时级 (hour)", "天级 (day)", "月级 (month)"])
        layout.addWidget(mode_label)
        layout.addWidget(self.mode_combo)
        
        # 初始资金
        capital_label = StylizedLabel("初始资金")
        self.capital_spin = QSpinBox()
        self.capital_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['info']};
                border-radius: 4px;
                padding: 5px;
            }}
        """)
        self.capital_spin.setMinimum(1000)
        self.capital_spin.setMaximum(10000000)
        self.capital_spin.setValue(100000)
        self.capital_spin.setSingleStep(10000)
        layout.addWidget(capital_label)
        layout.addWidget(self.capital_spin)
        
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        
        create_btn = StylizedButton("创建")
        create_btn.set_success_style()
        create_btn.clicked.connect(self.accept)
        button_layout.addWidget(create_btn)
        
        cancel_btn = StylizedButton("取消")
        cancel_btn.set_danger_style()
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_values(self) -> tuple:
        """获取输入值"""
        name = self.name_input.text().strip()
        mode_text = self.mode_combo.currentText()
        # 从 "秒级 (second)" 中提取 "second"
        mode = mode_text.split("(")[1].rstrip(")")
        capital = float(self.capital_spin.value())
        
        return name, mode, capital
