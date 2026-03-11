"""
Stonk - 登录界面

用户登录和注册界面。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt
from client.ui.widgets import StylizedButton, StylizedLineEdit, StylizedLabel
from client.config import COLORS


class LoginWindow(QWidget):
    """登录界面"""
    
    # 信号
    login_requested = Signal(str, str)  # username, password
    register_requested = Signal(str, str)  # username, password
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        self.current_mode = "login"  # login 或 register
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
        
        # 内容容器
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(12)
        
        # 初始显示登录界面
        self._show_login_form()
        
        self.layout.addLayout(self.content_layout)
        self.layout.addStretch()
        
        self.setLayout(self.layout)
    
    def _clear_content(self):
        """清空内容区"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
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
        
        login_btn = StylizedButton("登录")
        login_btn.set_success_style()
        login_btn.clicked.connect(self._on_login_clicked)
        button_layout.addWidget(login_btn)
        
        register_btn = StylizedButton("注册新账户")
        register_btn.clicked.connect(self._on_switch_to_register)
        button_layout.addWidget(register_btn)
        
        self.content_layout.addLayout(button_layout)
    
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
        
        register_btn = StylizedButton("注册")
        register_btn.set_success_style()
        register_btn.clicked.connect(self._on_register_clicked)
        button_layout.addWidget(register_btn)
        
        back_btn = StylizedButton("返回登录")
        back_btn.clicked.connect(self._on_switch_to_login)
        button_layout.addWidget(back_btn)
        
        self.content_layout.addLayout(button_layout)
    
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
