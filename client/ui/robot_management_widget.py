"""
机器人管理组件 - Robot Management Widget

用于管理员界面中管理和监控房间内的机器人账户。
功能包括：
- 机器人列表显示
- 批量添加机器人
- 策略参数编辑
- 实时状态监控
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit,
    QGroupBox, QFormLayout, QMessageBox, QHeaderView,
    QTabWidget, QTextEdit, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from shared.constants import RobotStrategyType


class RobotListWidget(QWidget):
    """机器人列表显示组件"""
    
    # 信号：用户选择某个机器人
    robot_selected = Signal(str)  # robot_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("机器人列表")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        layout.addWidget(title_label)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "策略类型", "初始资金", "当前现金", "持仓市值", "盈亏", "盈亏率"
        ])
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        # 设置选择行为
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        
        # 应用样式
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #444444;
                border: 1px solid #444444;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #3a7abd;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        layout.addWidget(self.table)
        
    def on_selection_changed(self):
        """处理选择变化"""
        selected_rows = self.table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            robot_id = self.table.item(row, 0).text()
            self.robot_selected.emit(robot_id)
            
    def update_robot_list(self, robots: list):
        """
        更新机器人列表
        
        Args:
            robots: 机器人数据列表，每个元素为字典：
                   {robot_id, name, strategy_type, initial_capital, 
                    current_cash, position_value, profit_loss, profit_loss_percent}
        """
        self.table.setRowCount(len(robots))
        
        for row, robot in enumerate(robots):
            # ID
            item_id = QTableWidgetItem(robot.get("robot_id", ""))
            item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, item_id)
            
            # 名称
            item_name = QTableWidgetItem(robot.get("name", ""))
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, item_name)
            
            # 策略类型
            strategy_map = {
                "retail": "散户游资",
                "institution": "正规机构",
                "trend": "趋势追踪"
            }
            strategy_text = strategy_map.get(robot.get("strategy_type", ""), "")
            item_strategy = QTableWidgetItem(strategy_text)
            item_strategy.setFlags(item_strategy.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, item_strategy)
            
            # 初始资金
            item_initial = QTableWidgetItem(f"¥{robot.get('initial_capital', 0):,.2f}")
            item_initial.setFlags(item_initial.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, item_initial)
            
            # 当前现金
            item_cash = QTableWidgetItem(f"¥{robot.get('current_cash', 0):,.2f}")
            item_cash.setFlags(item_cash.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, item_cash)
            
            # 持仓市值
            item_position = QTableWidgetItem(f"¥{robot.get('position_value', 0):,.2f}")
            item_position.setFlags(item_position.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 5, item_position)
            
            # 盈亏
            profit_loss = robot.get("profit_loss", 0)
            item_profit = QTableWidgetItem(f"{'+' if profit_loss >= 0 else ''}¥{profit_loss:,.2f}")
            item_profit.setFlags(item_profit.flags() & ~Qt.ItemIsEditable)
            # 盈亏颜色
            if profit_loss > 0:
                item_profit.setForeground(Qt.green)  # 涨红（国际惯例）
            elif profit_loss < 0:
                item_profit.setForeground(Qt.red)  # 跌绿
            self.table.setItem(row, 6, item_profit)
            
            # 盈亏率
            profit_percent = robot.get("profit_loss_percent", 0)
            item_percent = QTableWidgetItem(f"{'+' if profit_percent >= 0 else ''}{profit_percent:.2f}%")
            item_percent.setFlags(item_percent.flags() & ~Qt.ItemIsEditable)
            if profit_percent > 0:
                item_percent.setForeground(Qt.green)
            elif profit_percent < 0:
                item_percent.setForeground(Qt.red)
            self.table.setItem(row, 7, item_percent)


class AddRobotWidget(QWidget):
    """添加机器人组件"""
    
    # 信号：添加机器人请求
    add_robot_requested = Signal(dict)  # 机器人配置数据
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("添加机器人")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 策略类型选择
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["散户游资", "正规机构", "趋势追踪"])
        self.strategy_combo.setCurrentIndex(0)
        self.strategy_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
            }
        """)
        form_layout.addRow("策略类型:", self.strategy_combo)
        
        # 机器人名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：散户 1 号")
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        form_layout.addRow("机器人名称:", self.name_edit)
        
        # 初始资金
        self.capital_spin = QDoubleSpinBox()
        self.capital_spin.setRange(1000, 10000000)
        self.capital_spin.setValue(100000)
        self.capital_spin.setPrefix("¥ ")
        self.capital_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        form_layout.addRow("初始资金:", self.capital_spin)
        
        # 批量添加数量
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 50)
        self.count_spin.setValue(1)
        self.count_spin.setStyleSheet("""
            QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        form_layout.addRow("添加数量:", self.count_spin)
        
        layout.addLayout(form_layout)
        
        # 添加按钮
        self.add_button = QPushButton("添加机器人")
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #3a7abd;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a8ace;
            }
            QPushButton:pressed {
                background-color: #2a6a9d;
            }
        """)
        self.add_button.clicked.connect(self.on_add_clicked)
        layout.addWidget(self.add_button)
        
        layout.addStretch()
        
    def on_add_clicked(self):
        """处理添加按钮点击"""
        strategy_map = {
            "散户游资": "retail",
            "正规机构": "institution",
            "趋势追踪": "trend"
        }
        
        config = {
            "strategy_type": strategy_map[self.strategy_combo.currentText()],
            "name_prefix": self.name_edit.text() or "机器人",
            "initial_capital": self.capital_spin.value(),
            "count": self.count_spin.value()
        }
        
        self.add_robot_requested.emit(config)
        
        # 清空名称输入
        self.name_edit.clear()


class RobotParamEditor(QWidget):
    """机器人参数编辑器"""
    
    # 信号：参数更新请求
    params_updated = Signal(str, dict)  # robot_id, params
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_robot_id = None
        self.setup_ui()
        
    def setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("策略参数编辑")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # 当前选中机器人信息
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        self.robot_info_label = QLabel("未选择机器人")
        self.robot_info_label.setStyleSheet("color: #888888;")
        info_layout.addWidget(self.robot_info_label)
        
        layout.addWidget(info_frame)
        
        # 参数编辑表单
        self.param_form = QFormLayout()
        
        # 交易频率
        self.trade_freq_spin = QDoubleSpinBox()
        self.trade_freq_spin.setRange(0.0, 1.0)
        self.trade_freq_spin.setSingleStep(0.05)
        self.trade_freq_spin.setValue(0.7)
        self.trade_freq_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        self.param_form.addRow("交易频率:", self.trade_freq_spin)
        
        # 仓位比例
        self.position_ratio_spin = QDoubleSpinBox()
        self.position_ratio_spin.setRange(0.0, 1.0)
        self.position_ratio_spin.setSingleStep(0.05)
        self.position_ratio_spin.setValue(0.3)
        self.position_ratio_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        self.param_form.addRow("仓位比例:", self.position_ratio_spin)
        
        # 情绪权重（仅散户）
        self.sentiment_weight_spin = QDoubleSpinBox()
        self.sentiment_weight_spin.setRange(0.0, 1.0)
        self.sentiment_weight_spin.setSingleStep(0.05)
        self.sentiment_weight_spin.setValue(0.5)
        self.sentiment_weight_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        self.param_form.addRow("情绪权重:", self.sentiment_weight_spin)
        
        # 止损阈值（仅趋势）
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(0.01, 0.5)
        self.stop_loss_spin.setSingleStep(0.01)
        self.stop_loss_spin.setValue(0.1)
        self.stop_loss_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        self.param_form.addRow("止损阈值:", self.stop_loss_spin)
        
        layout.addLayout(self.param_form)
        
        # 更新按钮
        self.update_button = QPushButton("应用参数")
        self.update_button.setStyleSheet("""
            QPushButton {
                background-color: #3a7abd;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a8ace;
            }
            QPushButton:pressed {
                background-color: #2a6a9d;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.update_button.setEnabled(False)
        self.update_button.clicked.connect(self.on_update_clicked)
        layout.addWidget(self.update_button)
        
        layout.addStretch()
        
    def select_robot(self, robot_id: str, robot_info: dict):
        """
        选择要编辑的机器人
        
        Args:
            robot_id: 机器人 ID
            robot_info: 机器人信息字典
        """
        self.current_robot_id = robot_id
        self.robot_info_label.setText(
            f"当前编辑：<b>{robot_info.get('name', '')}</b> "
            f"({robot_info.get('strategy_type', '')})"
        )
        self.robot_info_label.setStyleSheet("color: #ffffff;")
        self.update_button.setEnabled(True)
        
        # 加载当前参数
        params = robot_info.get("params", {})
        self.trade_freq_spin.setValue(params.get("trade_probability", 0.7))
        self.position_ratio_spin.setValue(params.get("position_ratio", 0.3))
        self.sentiment_weight_spin.setValue(params.get("sentiment_weight", 0.5))
        self.stop_loss_spin.setValue(params.get("stop_loss", 0.1))
        
    def clear_selection(self):
        """清除选择"""
        self.current_robot_id = None
        self.robot_info_label.setText("未选择机器人")
        self.robot_info_label.setStyleSheet("color: #888888;")
        self.update_button.setEnabled(False)
        
    def on_update_clicked(self):
        """处理更新按钮点击"""
        if not self.current_robot_id:
            return
            
        params = {
            "trade_probability": self.trade_freq_spin.value(),
            "position_ratio": self.position_ratio_spin.value(),
            "sentiment_weight": self.sentiment_weight_spin.value(),
            "stop_loss": self.stop_loss_spin.value()
        }
        
        self.params_updated.emit(self.current_robot_id, params)


class RobotDecisionLog(QWidget):
    """机器人决策日志组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("决策日志")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00;
                border: 1px solid #444444;
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # 清空按钮
        self.clear_button = QPushButton("清空日志")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        self.clear_button.clicked.connect(self.log_text.clear)
        layout.addWidget(self.clear_button)
        
    def append_log(self, message: str):
        """追加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def update_robot_decisions(self, robot_id: str, decisions: list):
        """
        更新机器人决策显示
        
        Args:
            robot_id: 机器人 ID
            decisions: 决策列表
        """
        self.append_log(f"机器人 {robot_id} 执行了 {len(decisions)} 个决策:")
        for decision in decisions:
            action_text = {
                "buy": "买入",
                "sell": "卖出",
                "hold": "持有"
            }.get(decision.get("action", ""), "")
            
            self.append_log(
                f"  → {action_text} {decision.get('stock_code', '')} "
                f"x{decision.get('quantity', 0)} @ ¥{decision.get('price', 0):.2f}"
            )
            if decision.get("reason"):
                self.append_log(f"    原因：{decision.get('reason')}")


class RobotManagementWidget(QWidget):
    """
    机器人管理主组件
    
    整合所有子组件，提供完整的机器人管理功能
    """
    
    # 信号
    add_robot_signal = Signal(dict)  # 添加机器人配置
    update_params_signal = Signal(str, dict)  # 更新参数 (robot_id, params)
    remove_robot_signal = Signal(str)  # 移除机器人
    set_sentiment_signal = Signal(float)  # 设置房间情绪
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """设置 UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # 左侧：机器人列表和添加面板
        left_panel = QVBoxLayout()
        
        # 机器人列表
        self.robot_list = RobotListWidget()
        self.robot_list.robot_selected.connect(self.on_robot_selected)
        left_panel.addWidget(self.robot_list, stretch=2)
        
        # 添加机器人面板
        self.add_robot = AddRobotWidget()
        self.add_robot.add_robot_requested.connect(self.add_robot_signal.emit)
        left_panel.addWidget(self.add_robot, stretch=1)
        
        main_layout.addLayout(left_panel, stretch=2)
        
        # 右侧：参数编辑器和决策日志
        right_panel = QVBoxLayout()
        
        # 参数编辑器
        self.param_editor = RobotParamEditor()
        self.param_editor.params_updated.connect(self.update_params_signal.emit)
        right_panel.addWidget(self.param_editor, stretch=1)
        
        # 决策日志
        self.decision_log = RobotDecisionLog()
        right_panel.addWidget(self.decision_log, stretch=2)
        
        # 底部控制按钮
        control_layout = QHBoxLayout()
        
        # 情绪控制
        sentiment_group = QGroupBox("市场情绪")
        sentiment_layout = QHBoxLayout(sentiment_group)
        
        self.sentiment_combo = QComboBox()
        self.sentiment_combo.addItems(["积极", "中立", "消极"])
        self.sentiment_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        sentiment_layout.addWidget(self.sentiment_combo)
        
        self.sentiment_button = QPushButton("应用")
        self.sentiment_button.setStyleSheet("""
            QPushButton {
                background-color: #3a7abd;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
        """)
        self.sentiment_button.clicked.connect(self.on_sentiment_clicked)
        sentiment_layout.addWidget(self.sentiment_button)
        
        control_layout.addWidget(sentiment_group)
        
        # 移除机器人按钮
        self.remove_button = QPushButton("移除机器人")
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #bd3a3a;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ce4a4a;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self.on_remove_clicked)
        control_layout.addWidget(self.remove_button)
        
        right_panel.addLayout(control_layout)
        
        main_layout.addLayout(right_panel, stretch=1)
        
        # 整体样式
        self.setStyleSheet("""
            RobotManagementWidget {
                background-color: #1e1e1e;
            }
        """)
        
    def connect_signals(self):
        """连接内部信号"""
        pass
        
    def on_robot_selected(self, robot_id: str):
        """处理机器人选择"""
        # 这里需要从外部获取机器人详细信息
        # 暂时只启用移除按钮
        self.remove_button.setEnabled(True)
        self.selected_robot_id = robot_id
        
    def on_remove_clicked(self):
        """处理移除按钮点击"""
        if hasattr(self, 'selected_robot_id'):
            reply = QMessageBox.question(
                self,
                "确认移除",
                f"确定要移除机器人 {self.selected_robot_id} 吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.remove_robot_signal.emit(self.selected_robot_id)
                self.param_editor.clear_selection()
                self.remove_button.setEnabled(False)
                
    def on_sentiment_clicked(self):
        """处理情绪设置按钮点击"""
        sentiment_map = {
            "积极": 0.5,
            "中立": 0.0,
            "消极": -0.5
        }
        sentiment = sentiment_map.get(self.sentiment_combo.currentText(), 0.0)
        self.set_sentiment_signal.emit(sentiment)
        
    def update_robot_list(self, robots: list):
        """更新机器人列表"""
        self.robot_list.update_robot_list(robots)
        
    def update_robot_params(self, robot_id: str, robot_info: dict):
        """更新单个机器人信息显示"""
        self.param_editor.select_robot(robot_id, robot_info)
        
    def log_decision(self, robot_id: str, decisions: list):
        """记录决策日志"""
        self.decision_log.update_robot_decisions(robot_id, decisions)


if __name__ == "__main__":
    # 测试代码
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = RobotManagementWidget()
    
    # 模拟数据
    test_robots = [
        {
            "robot_id": "r001",
            "name": "散户 1 号",
            "strategy_type": "retail",
            "initial_capital": 100000,
            "current_cash": 95000,
            "position_value": 12000,
            "profit_loss": 7000,
            "profit_loss_percent": 7.0
        },
        {
            "robot_id": "r002",
            "name": "机构 1 号",
            "strategy_type": "institution",
            "initial_capital": 500000,
            "current_cash": 450000,
            "position_value": 60000,
            "profit_loss": 10000,
            "profit_loss_percent": 2.0
        },
        {
            "robot_id": "r003",
            "name": "趋势 1 号",
            "strategy_type": "trend",
            "initial_capital": 200000,
            "current_cash": 180000,
            "position_value": 25000,
            "profit_loss": 5000,
            "profit_loss_percent": 2.5
        }
    ]
    
    widget.update_robot_list(test_robots)
    widget.show()
    
    sys.exit(app.exec())
