"""
Stonk - 主窗口

主应用窗口，管理页面切换和客户端生命周期。
"""

import asyncio
import logging
from typing import Optional
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtCore import Qt, QThread, pyqtSignal
from client.ui.login_window import LoginWindow
from client.ui.lobby_window import LobbyWindow
from client.websocket_client import WebSocketClient
from client.config import WINDOW_WIDTH, WINDOW_HEIGHT

logger = logging.getLogger(__name__)


class StonkMainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stonk - 股票模拟交易系统")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # 创建 WebSocket 客户端
        self.client = WebSocketClient()
        self.client_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 创建页面
        self.stacked = QStackedWidget()
        self.login_window = LoginWindow()
        self.lobby_window = LobbyWindow()
        
        self.stacked.addWidget(self.login_window)
        self.stacked.addWidget(self.lobby_window)
        
        self.setCentralWidget(self.stacked)
        
        # 连接信号
        self._connect_signals()
        
        # 初始化客户端
        self._init_client()
    
    def _connect_signals(self):
        """连接信号"""
        # 登录窗口信号
        self.login_window.login_requested.connect(self._on_login_requested)
        self.login_window.register_requested.connect(self._on_register_requested)
        
        # 大厅窗口信号
        self.lobby_window.logout_requested.connect(self._on_logout_requested)
        self.lobby_window.refresh_requested.connect(self._on_refresh_requested)
        self.lobby_window.room_joined.connect(self._on_room_joined)
        self.lobby_window.create_room_requested.connect(self._on_create_room_requested)
    
    def _init_client(self):
        """初始化客户端"""
        async def async_connect():
            """异步连接"""
            try:
                success = await self.client.connect()
                if success:
                    logger.info("Connected to server")
                    self.stacked.setCurrentWidget(self.login_window)
                else:
                    QMessageBox.critical(self, "连接失败", "无法连接到服务器，请检查服务器是否运行")
                    self.close()
            except Exception as e:
                logger.error(f"Error connecting to server: {e}")
                QMessageBox.critical(self, "连接失败", f"连接服务器出错: {str(e)}")
                self.close()
        
        # 在新的线程中运行异步操作
        self.client_loop = asyncio.new_event_loop()
        
        def run_async():
            asyncio.set_event_loop(self.client_loop)
            self.client_loop.run_until_complete(async_connect())
        
        thread = QThread()
        thread.run = run_async
        thread.start()
    
    def _on_login_requested(self, username: str, password: str):
        """处理登录请求"""
        async def async_login():
            """异步登录"""
            try:
                if await self.client.login(username, password):
                    logger.info(f"Logged in as {username}")
                    self.login_window.clear_inputs()
                    
                    # 加载房间列表
                    rooms = await self.client.get_room_list()
                    if rooms is not None:
                        self.lobby_window.load_rooms(rooms)
                        self.stacked.setCurrentWidget(self.lobby_window)
                else:
                    self.login_window.show_message("登录失败，请检查用户名和密码", is_error=True)
            except Exception as e:
                logger.error(f"Login error: {e}")
                self.login_window.show_message(f"登录出错: {str(e)}", is_error=True)
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_login(), self.client_loop)
    
    def _on_register_requested(self, username: str, password: str):
        """处理注册请求"""
        async def async_register():
            """异步注册"""
            try:
                if await self.client.register(username, password):
                    logger.info(f"Registered as {username}")
                    self.login_window.show_message("注册成功，已自动登录")
                    self.login_window.clear_inputs()
                    self.login_window._show_login_form()
                    
                    # 加载房间列表
                    rooms = await self.client.get_room_list()
                    if rooms is not None:
                        self.lobby_window.load_rooms(rooms)
                        self.stacked.setCurrentWidget(self.lobby_window)
                else:
                    self.login_window.show_message("注册失败，用户名可能已存在", is_error=True)
            except Exception as e:
                logger.error(f"Register error: {e}")
                self.login_window.show_message(f"注册出错: {str(e)}", is_error=True)
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_register(), self.client_loop)
    
    def _on_logout_requested(self):
        """处理登出请求"""
        async def async_logout():
            """异步登出"""
            try:
                await self.client.logout()
                logger.info("Logged out")
                self.stacked.setCurrentWidget(self.login_window)
            except Exception as e:
                logger.error(f"Logout error: {e}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_logout(), self.client_loop)
    
    def _on_refresh_requested(self):
        """处理刷新请求"""
        async def async_refresh():
            """异步刷新"""
            try:
                rooms = await self.client.get_room_list()
                if rooms is not None:
                    self.lobby_window.load_rooms(rooms)
            except Exception as e:
                logger.error(f"Refresh error: {e}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_refresh(), self.client_loop)
    
    def _on_room_joined(self, room_id: str):
        """处理加入房间请求"""
        async def async_join():
            """异步加入房间"""
            try:
                if await self.client.join_room(room_id):
                    logger.info(f"Joined room {room_id}")
                    QMessageBox.information(self, "成功", "已加入房间")
                else:
                    QMessageBox.warning(self, "失败", "加入房间失败")
            except Exception as e:
                logger.error(f"Join room error: {e}")
                QMessageBox.critical(self, "错误", f"加入房间出错: {str(e)}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_join(), self.client_loop)
    
    def _on_create_room_requested(self, name: str, step_mode: str, initial_capital: float):
        """处理创建房间请求"""
        async def async_create():
            """异步创建房间"""
            try:
                room_id = await self.client.create_room(name, step_mode, initial_capital)
                if room_id:
                    logger.info(f"Created room {room_id}")
                    QMessageBox.information(self, "成功", "房间创建成功")
                    
                    # 刷新房间列表
                    rooms = await self.client.get_room_list()
                    if rooms is not None:
                        self.lobby_window.load_rooms(rooms)
                else:
                    QMessageBox.warning(self, "失败", "创建房间失败")
            except Exception as e:
                logger.error(f"Create room error: {e}")
                QMessageBox.critical(self, "错误", f"创建房间出错: {str(e)}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_create(), self.client_loop)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        async def async_disconnect():
            """异步断开连接"""
            try:
                await self.client.disconnect()
            except:
                pass
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_disconnect(), self.client_loop)
        
        event.accept()


def run_client():
    """运行客户端"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = StonkMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_client()
