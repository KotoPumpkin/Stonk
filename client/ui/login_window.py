"""
Stonk - 登录界面

用户登录和注册界面，包含服务器地址连接功能。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Signal, Qt
from client.ui.widgets import StylizedButton, StylizedLineEdit, StylizedLabel
from client.config import COLORS, SERVER_ADDRESS, SERVER_PORT_NUM


class LoginWindow(QWidget):
    """登录界面"""
    
    # 信号
    login_requested = Signal(str, str)  # username, password
    register_requested = Signal(str, str)  # username, password
    connect_requested = Signal(str, int)  # host, port
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        self.current_mode = "login"  # login 或 register
        self._is_connected = False
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)
        
        # 标题
        self.title = StylizedLabel("Stonk - 股票模拟交易系统")
        self.title.set_title_style()
        self.title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title)
        
        # ==================== 服务器连接区域 ====================
        self.server_frame = QFrame()
        self.server_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['panel']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        server_layout = QVBoxLayout()
        server_layout.setSpacing(8)
        
        server_title = StylizedLabel("服务器连接")
        server_title.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['info']};
                font-weight: bold;
                font-size: 14px;
            }}
        """)
        server_layout.addWidget(server_title)
        
        # 服务器地址输入行
        addr_layout = QHBoxLayout()
        addr_layout.setSpacing(8)
        
        addr_label = StylizedLabel("地址:")
        addr_label.setFixedWidth(40)
        addr_layout.addWidget(addr_label)
        
        self.server_host_input = StylizedLineEdit()
        self.server_host_input.setPlaceholderText("服务器地址")
        self.server_host_input.setText(SERVER_ADDRESS)
        addr_layout.addWidget(self.server_host_input)
        
        port_label = StylizedLabel("端口:")
        port_label.setFixedWidth(40)
        addr_layout.addWidget(port_label)
        
        self.server_port_input = StylizedLineEdit()
        self.server_port_input.setPlaceholderText("端口")
        self.server_port_input.setText(str(SERVER_PORT_NUM))
        self.server_port_input.setFixedWidth(80)
        addr_layout.addWidget(self.server_port_input)
        
        self.connect_btn = StylizedButton("连接")
        self.connect_btn.set_success_style()
        self.connect_btn.setFixedWidth(80)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        addr_layout.addWidget(self.connect_btn)
        
        server_layout.addLayout(addr_layout)
        
        # 连接状态标签
        self.connection_status_label = StylizedLabel("● 未连接")
        self.connection_status_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['danger']};
                font-size: 12px;
                padding: 4px 0px;
            }}
        """)
        server_layout.addWidget(self.connection_status_label)
        
        self.server_frame.setLayout(server_layout)
        self.layout.addWidget(self.server_frame)
        
        # ==================== 登录/注册内容区域 ====================
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(12)
        
        # 初始显示登录界面
        self._show_login_form()
        
        self.layout.addLayout(self.content_layout)
        self.layout.addStretch()
        
        self.setLayout(self.layout)
        
        # 初始状态：禁用登录/注册表单
        self._set_form_enabled(False)
    
    def _clear_content(self):
        """清空内容区"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 递归清理子布局中的控件
                self._clear_layout(item.layout())
    
    def _clear_layout(self, layout):
        """递归清空布局"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _show_login_form(self):
        """显示登录表单"""
        self._clear_content()
        self.current_mode = "login"
        
        # 用户名
        username_label = StylizedLabel("用户名")
        self.login_username = StylizedLineEdit()
        self.login_username.setPlaceholderText("输入用户名")
        self.content_layout.addWidget(username_label)
        self.content_layout.addWidget(self.login_username)
        
        # 密码
        password_label = StylizedLabel("密码")
        self.login_password = StylizedLineEdit()
        self.login_password.setPlaceholderText("输入密码")
        self.login_password.setEchoMode(StylizedLineEdit.Password)
        self.content_layout.addWidget(password_label)
        self.content_layout.addWidget(self.login_password)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.login_btn = StylizedButton("登录")
        self.login_btn.set_success_style()
        self.login_btn.clicked.connect(self._on_login_clicked)
        button_layout.addWidget(self.login_btn)
        
        self.switch_to_register_btn = StylizedButton("注册新账户")
        self.switch_to_register_btn.clicked.connect(self._on_switch_to_register)
        button_layout.addWidget(self.switch_to_register_btn)
        
        self.content_layout.addLayout(button_layout)
        
        # 根据连接状态设置表单可用性
        self._set_form_enabled(self._is_connected)
    
    def _show_register_form(self):
        """显示注册表单"""
        self._clear_content()
        self.current_mode = "register"
        
        # 用户名
        username_label = StylizedLabel("用户名")
        self.register_username = StylizedLineEdit()
        self.register_username.setPlaceholderText("输入用户名")
        self.content_layout.addWidget(username_label)
        self.content_layout.addWidget(self.register_username)
        
        # 密码
        password_label = StylizedLabel("密码")
        self.register_password = StylizedLineEdit()
        self.register_password.setPlaceholderText("输入密码")
        self.register_password.setEchoMode(StylizedLineEdit.Password)
        self.content_layout.addWidget(password_label)
        self.content_layout.addWidget(self.register_password)
        
        # 确认密码
        confirm_label = StylizedLabel("确认密码")
        self.register_confirm = StylizedLineEdit()
        self.register_confirm.setPlaceholderText("确认密码")
        self.register_confirm.setEchoMode(StylizedLineEdit.Password)
        self.content_layout.addWidget(confirm_label)
        self.content_layout.addWidget(self.register_confirm)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.register_btn = StylizedButton("注册")
        self.register_btn.set_success_style()
        self.register_btn.clicked.connect(self._on_register_clicked)
        button_layout.addWidget(self.register_btn)
        
        self.back_to_login_btn = StylizedButton("返回登录")
        self.back_to_login_btn.clicked.connect(self._on_switch_to_login)
        button_layout.addWidget(self.back_to_login_btn)
        
        self.content_layout.addLayout(button_layout)
        
        # 根据连接状态设置表单可用性
        self._set_form_enabled(self._is_connected)
    
    def _set_form_enabled(self, enabled: bool):
        """设置登录/注册表单的启用状态"""
        if self.current_mode == "login":
            if hasattr(self, 'login_username'):
                self.login_username.setEnabled(enabled)
            if hasattr(self, 'login_password'):
                self.login_password.setEnabled(enabled)
            if hasattr(self, 'login_btn'):
                self.login_btn.setEnabled(enabled)
            if hasattr(self, 'switch_to_register_btn'):
                self.switch_to_register_btn.setEnabled(enabled)
        elif self.current_mode == "register":
            if hasattr(self, 'register_username'):
                self.register_username.setEnabled(enabled)
            if hasattr(self, 'register_password'):
                self.register_password.setEnabled(enabled)
            if hasattr(self, 'register_confirm'):
                self.register_confirm.setEnabled(enabled)
            if hasattr(self, 'register_btn'):
                self.register_btn.setEnabled(enabled)
            if hasattr(self, 'back_to_login_btn'):
                self.back_to_login_btn.setEnabled(enabled)
    
    def _on_connect_clicked(self):
        """处理连接按钮点击"""
        host = self.server_host_input.text().strip()
        port_text = self.server_port_input.text().strip()
        
        if not host:
            self._show_error("请输入服务器地址")
            return
        
        if not port_text:
            self._show_error("请输入端口号")
            return
        
        try:
            port = int(port_text)
            if port < 1 or port > 65535:
                self._show_error("端口号必须在 1-65535 之间")
                return
        except ValueError:
            self._show_error("端口号必须为数字")
            return
        
        # 更新状态为连接中
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("连接中...")
        self.server_host_input.setEnabled(False)
        self.server_port_input.setEnabled(False)
        self.connection_status_label.setText("● 连接中...")
        self.connection_status_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['warning']};
                font-size: 12px;
                padding: 4px 0px;
            }}
        """)
        
        # 发射连接请求信号
        self.connect_requested.emit(host, port)
    
    def on_connect_success(self):
        """连接成功回调"""
        self._is_connected = True
        self.connection_status_label.setText("● 已连接")
        self.connection_status_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['success']};
                font-size: 12px;
                padding: 4px 0px;
            }}
        """)
        self.connect_btn.setText("已连接")
        self.connect_btn.setEnabled(False)
        self.server_host_input.setEnabled(False)
        self.server_port_input.setEnabled(False)
        
        # 启用登录/注册表单
        self._set_form_enabled(True)
    
    def on_connect_failure(self, error_message: str):
        """连接失败回调"""
        self._is_connected = False
        self.connection_status_label.setText(f"● 连接失败")
        self.connection_status_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['danger']};
                font-size: 12px;
                padding: 4px 0px;
            }}
        """)
        self.connect_btn.setText("连接")
        self.connect_btn.setEnabled(True)
        self.server_host_input.setEnabled(True)
        self.server_port_input.setEnabled(True)
        
        # 禁用登录/注册表单
        self._set_form_enabled(False)
        
        # 显示错误消息
        self._show_error(error_message)
    
    def on_disconnected(self):
        """断开连接回调（用于连接中断时重置状态）"""
        self._is_connected = False
        self.connection_status_label.setText("● 未连接")
        self.connection_status_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['danger']};
                font-size: 12px;
                padding: 4px 0px;
            }}
        """)
        self.connect_btn.setText("连接")
        self.connect_btn.setEnabled(True)
        self.server_host_input.setEnabled(True)
        self.server_port_input.setEnabled(True)
        
        # 禁用登录/注册表单
        self._set_form_enabled(False)
    
    def _on_login_clicked(self):
        """处理登录按钮点击"""
        username = self.login_username.text().strip()
        password = self.login_password.text()
        
        if not username or not password:
            self._show_error("请输入用户名和密码")
            return
        
        self.login_requested.emit(username, password)
    
    def _on_register_clicked(self):
        """处理注册按钮点击"""
        username = self.register_username.text().strip()
        password = self.register_password.text()
        confirm = self.register_confirm.text()
        
        if not username or not password or not confirm:
            self._show_error("请填写所有字段")
            return
        
        if password != confirm:
            self._show_error("两次输入的密码不一致")
            return
        
        if len(password) < 6:
            self._show_error("密码长度至少为6位")
            return
        
        self.register_requested.emit(username, password)
    
    def _on_switch_to_register(self):
        """切换到注册界面"""
        self._show_register_form()
    
    def _on_switch_to_login(self):
        """切换到登录界面"""
        self._show_login_form()
    
    def _show_error(self, message: str):
        """显示错误消息"""
        error_label = StylizedLabel(f"❌ {message}")
        error_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['danger']};
                font-weight: bold;
                padding: 8px;
                background-color: {COLORS['panel']};
                border-radius: 4px;
            }}
        """)
        self.content_layout.insertWidget(0, error_label)
    
    def clear_inputs(self):
        """清空输入框"""
        if self.current_mode == "login":
            self.login_username.clear()
            self.login_password.clear()
        else:
            self.register_username.clear()
            self.register_password.clear()
            self.register_confirm.clear()
    
    def show_message(self, message: str, is_error: bool = False):
        """显示消息"""
        if is_error:
            self._show_error(message)
        else:
            info_label = StylizedLabel(f"✓ {message}")
            info_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['success']};
                    font-weight: bold;
                    padding: 8px;
                    background-color: {COLORS['panel']};
                    border-radius: 4px;
                }}
            """)
            self.content_layout.insertWidget(0, info_label)
