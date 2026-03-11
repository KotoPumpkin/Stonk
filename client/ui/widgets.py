"""
Stonk - 自定义控件模块

实现样式化的 PySide6 控件。
"""

from PySide6.QtWidgets import QPushButton, QLineEdit, QLabel, QWidget
from PySide6.QtCore import Qt
from client.config import COLORS, FONT_FAMILY, FONT_SIZE_NORMAL


class StylizedButton(QPushButton):
    """样式化按钮"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: {COLORS['background']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-family: {FONT_FAMILY};
                font-size: {FONT_SIZE_NORMAL}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0088cc;
            }}
            QPushButton:pressed {{
                background-color: #006699;
            }}
        """)
    
    def set_success_style(self):
        """设置成功风格"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: {COLORS['background']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-family: {FONT_FAMILY};
                font-size: {FONT_SIZE_NORMAL}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #00dd00;
            }}
            QPushButton:pressed {{
                background-color: #00aa00;
            }}
        """)
    
    def set_danger_style(self):
        """设置危险风格"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: {COLORS['background']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-family: {FONT_FAMILY};
                font-size: {FONT_SIZE_NORMAL}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #ff3333;
            }}
            QPushButton:pressed {{
                background-color: #cc0000;
            }}
        """)


class StylizedLineEdit(QLineEdit):
    """样式化输入框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['panel']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['info']};
                border-radius: 4px;
                padding: 8px;
                font-family: {FONT_FAMILY};
                font-size: {FONT_SIZE_NORMAL}px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['success']};
            }}
        """)


class StylizedLabel(QLabel):
    """样式化标签"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-family: {FONT_FAMILY};
                font-size: {FONT_SIZE_NORMAL}px;
            }}
        """)
    
    def set_title_style(self):
        """设置标题风格"""
        self.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-family: {FONT_FAMILY};
                font-size: 16px;
                font-weight: bold;
            }}
        """)
