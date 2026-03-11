"""
Stonk - 主窗口

主应用窗口，管理页面切换和客户端生命周期。
"""

import asyncio
import logging
import threading
from typing import Optional
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal, QObject
from client.ui.login_window import LoginWindow
from client.ui.lobby_window import LobbyWindow
from client.ui.trading_window import TradingWindow
from client.websocket_client import WebSocketClient
from client.config import WINDOW_WIDTH, WINDOW_HEIGHT

logger = logging.getLogger(__name__)


class AsyncSignalBridge(QObject):
    """
    异步操作与 Qt UI 之间的信号桥梁。
    用于从异步线程安全地更新 UI。
    """
    connect_success = Signal()
    connect_failure = Signal(str)
    login_success = Signal()
    login_failure = Signal(str)
    register_success = Signal()
    register_failure = Signal(str)
    rooms_loaded = Signal(list)
    room_joined = Signal(str)
    room_join_failed = Signal(str)
    room_created = Signal()
    room_create_failed = Signal(str)


class StonkMainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stonk - 股票模拟交易系统")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # 创建 WebSocket 客户端
        self.client = WebSocketClient()
        self.client_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        
        # 创建信号桥梁
        self.bridge = AsyncSignalBridge()
        
        # 创建页面
        self.stacked = QStackedWidget()
        self.login_window = LoginWindow()
        self.lobby_window = LobbyWindow()
        self.trading_window: Optional[TradingWindow] = None
        
        self.stacked.addWidget(self.login_window)
        self.stacked.addWidget(self.lobby_window)
        
        self.setCentralWidget(self.stacked)
        
        # 连接信号
        self._connect_signals()
        
        # 启动异步事件循环线程
        self._start_async_loop()
    
    def _start_async_loop(self):
        """启动后台异步事件循环线程"""
        self.client_loop = asyncio.new_event_loop()
        
        def run_loop():
            asyncio.set_event_loop(self.client_loop)
            self.client_loop.run_forever()
        
        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()
    
    def _connect_signals(self):
        """连接信号"""
        # 登录窗口信号
        self.login_window.connect_requested.connect(self._on_connect_requested)
        self.login_window.login_requested.connect(self._on_login_requested)
        self.login_window.register_requested.connect(self._on_register_requested)
        
        # 大厅窗口信号
        self.lobby_window.logout_requested.connect(self._on_logout_requested)
        self.lobby_window.refresh_requested.connect(self._on_refresh_requested)
        self.lobby_window.room_joined.connect(self._on_room_joined)
        self.lobby_window.create_room_requested.connect(self._on_create_room_requested)
        
        # 异步桥梁信号 -> UI 更新
        self.bridge.connect_success.connect(self._handle_connect_success)
        self.bridge.connect_failure.connect(self._handle_connect_failure)
        self.bridge.login_success.connect(self._handle_login_success)
        self.bridge.login_failure.connect(self._handle_login_failure)
        self.bridge.register_success.connect(self._handle_register_success)
        self.bridge.register_failure.connect(self._handle_register_failure)
        self.bridge.rooms_loaded.connect(self._handle_rooms_loaded)
        self.bridge.room_joined.connect(self._handle_room_joined)
        self.bridge.room_join_failed.connect(self._handle_room_join_failed)
        self.bridge.room_created.connect(self._handle_room_created)
        self.bridge.room_create_failed.connect(self._handle_room_create_failed)
    
    # ==================== 连接处理 ====================
    
    def _on_connect_requested(self, host: str, port: int):
        """处理连接请求"""
        async def async_connect():
            try:
                # 如果之前已连接，先断开
                if self.client.connected:
                    await self.client.disconnect()
                
                success = await self.client.connect(host, port)
                if success:
                    logger.info(f"Connected to server {host}:{port}")
                    self.bridge.connect_success.emit()
                else:
                    self.bridge.connect_failure.emit(
                        f"无法连接到服务器 {host}:{port}，请检查地址是否正确以及服务器是否运行"
                    )
            except Exception as e:
                logger.error(f"Error connecting to server: {e}")
                self.bridge.connect_failure.emit(
                    f"连接服务器出错: {str(e)}"
                )
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_connect(), self.client_loop)
    
    def _handle_connect_success(self):
        """处理连接成功（UI 线程）"""
        self.login_window.on_connect_success()
    
    def _handle_connect_failure(self, error_message: str):
        """处理连接失败（UI 线程）"""
        self.login_window.on_connect_failure(error_message)
        QMessageBox.warning(
            self, "连接失败", error_message
        )
    
    # ==================== 登录处理 ====================
    
    def _on_login_requested(self, username: str, password: str):
        """处理登录请求"""
        async def async_login():
            try:
                if await self.client.login(username, password):
                    logger.info(f"Logged in as {username}")
                    self.bridge.login_success.emit()
                    
                    # 加载房间列表
                    rooms = await self.client.get_room_list()
                    if rooms is not None:
                        self.bridge.rooms_loaded.emit(rooms)
                else:
                    self.bridge.login_failure.emit("登录失败，请检查用户名和密码")
            except Exception as e:
                logger.error(f"Login error: {e}")
                self.bridge.login_failure.emit(f"登录出错: {str(e)}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_login(), self.client_loop)
    
    def _handle_login_success(self):
        """处理登录成功（UI 线程）"""
        self.login_window.clear_inputs()
    
    def _handle_login_failure(self, error_message: str):
        """处理登录失败（UI 线程）"""
        self.login_window.show_message(error_message, is_error=True)
    
    # ==================== 注册处理 ====================
    
    def _on_register_requested(self, username: str, password: str):
        """处理注册请求"""
        async def async_register():
            try:
                if await self.client.register(username, password):
                    logger.info(f"Registered as {username}")
                    self.bridge.register_success.emit()
                    
                    # 加载房间列表
                    rooms = await self.client.get_room_list()
                    if rooms is not None:
                        self.bridge.rooms_loaded.emit(rooms)
                else:
                    self.bridge.register_failure.emit("注册失败，用户名可能已存在")
            except Exception as e:
                logger.error(f"Register error: {e}")
                self.bridge.register_failure.emit(f"注册出错: {str(e)}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_register(), self.client_loop)
    
    def _handle_register_success(self):
        """处理注册成功（UI 线程）"""
        self.login_window.show_message("注册成功，已自动登录")
        self.login_window.clear_inputs()
        self.login_window._show_login_form()
    
    def _handle_register_failure(self, error_message: str):
        """处理注册失败（UI 线程）"""
        self.login_window.show_message(error_message, is_error=True)
    
    # ==================== 房间列表处理 ====================
    
    def _handle_rooms_loaded(self, rooms: list):
        """处理房间列表加载完成（UI 线程）"""
        self.lobby_window.load_rooms(rooms)
        self.stacked.setCurrentWidget(self.lobby_window)
    
    # ==================== 登出处理 ====================
    
    def _on_logout_requested(self):
        """处理登出请求"""
        async def async_logout():
            try:
                await self.client.logout()
                logger.info("Logged out")
            except Exception as e:
                logger.error(f"Logout error: {e}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_logout(), self.client_loop)
        
        # 返回登录界面
        self.stacked.setCurrentWidget(self.login_window)
    
    # ==================== 刷新处理 ====================
    
    def _on_refresh_requested(self):
        """处理刷新请求"""
        async def async_refresh():
            try:
                rooms = await self.client.get_room_list()
                if rooms is not None:
                    self.bridge.rooms_loaded.emit(rooms)
            except Exception as e:
                logger.error(f"Refresh error: {e}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_refresh(), self.client_loop)
    
    # ==================== 加入房间处理 ====================
    
    def _on_room_joined(self, room_id: str):
        """处理加入房间请求"""
        async def async_join():
            try:
                if await self.client.join_room(room_id):
                    logger.info(f"Joined room {room_id}")
                    self.bridge.room_joined.emit(room_id)
                else:
                    self.bridge.room_join_failed.emit("加入房间失败")
            except Exception as e:
                logger.error(f"Join room error: {e}")
                self.bridge.room_join_failed.emit(f"加入房间出错: {str(e)}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_join(), self.client_loop)
    
    def _handle_room_joined(self, room_id: str):
        """处理加入房间成功（UI 线程）"""
        self.trading_window = TradingWindow(self.client, room_id)
        self.stacked.addWidget(self.trading_window)
        self.stacked.setCurrentWidget(self.trading_window)
        
        # 连接交易窗口信号
        self.trading_window.exit_room_requested.connect(self._on_exit_room)
    
    def _handle_room_join_failed(self, error_message: str):
        """处理加入房间失败（UI 线程）"""
        QMessageBox.warning(self, "失败", error_message)
    
    # ==================== 退出房间处理 ====================
    
    def _on_exit_room(self):
        """处理退出房间请求"""
        async def async_exit():
            try:
                if self.client.room_id:
                    await self.client.leave_room(self.client.room_id)
                    logger.info("Exited room")
                
                # 刷新房间列表
                rooms = await self.client.get_room_list()
                if rooms is not None:
                    self.bridge.rooms_loaded.emit(rooms)
            except Exception as e:
                logger.error(f"Exit room error: {e}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_exit(), self.client_loop)
        
        # 移除交易窗口
        if self.trading_window:
            self.stacked.removeWidget(self.trading_window)
            self.trading_window.deleteLater()
            self.trading_window = None
        
        self.stacked.setCurrentWidget(self.lobby_window)
    
    # ==================== 创建房间处理 ====================
    
    def _on_create_room_requested(self, name: str, step_mode: str, initial_capital: float):
        """处理创建房间请求"""
        async def async_create():
            try:
                room_id = await self.client.create_room(name, step_mode, initial_capital)
                if room_id:
                    logger.info(f"Created room {room_id}")
                    self.bridge.room_created.emit()
                    
                    # 刷新房间列表
                    rooms = await self.client.get_room_list()
                    if rooms is not None:
                        self.bridge.rooms_loaded.emit(rooms)
                else:
                    self.bridge.room_create_failed.emit("创建房间失败")
            except Exception as e:
                logger.error(f"Create room error: {e}")
                self.bridge.room_create_failed.emit(f"创建房间出错: {str(e)}")
        
        if self.client_loop:
            asyncio.run_coroutine_threadsafe(async_create(), self.client_loop)
    
    def _handle_room_created(self):
        """处理创建房间成功（UI 线程）"""
        QMessageBox.information(self, "成功", "房间创建成功")
    
    def _handle_room_create_failed(self, error_message: str):
        """处理创建房间失败（UI 线程）"""
        QMessageBox.critical(self, "错误", error_message)
    
    # ==================== 窗口关闭 ====================
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.client_loop and self.client.connected:
            async def async_disconnect():
                try:
                    await self.client.disconnect()
                except:
                    pass
            
            future = asyncio.run_coroutine_threadsafe(async_disconnect(), self.client_loop)
            try:
                future.result(timeout=3)
            except:
                pass
        
        # 停止事件循环
        if self.client_loop:
            self.client_loop.call_soon_threadsafe(self.client_loop.stop)
        
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
