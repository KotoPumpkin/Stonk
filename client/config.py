"""
Stonk 客户端配置模块

客户端的全局配置参数。
"""

import os
from shared.constants import (
    SERVER_CONNECT_HOST,
    SERVER_PORT,
    CLIENT_RECONNECT_INTERVAL,
    CLIENT_RECONNECT_MAX_TRIES,
    CLIENT_HEARTBEAT_TIMEOUT,
)

# ==================== 服务器连接配置 ====================

# 服务器地址和端口
# 可通过环境变量 STONK_SERVER_HOST 和 STONK_SERVER_PORT 覆盖
# 例如：set STONK_SERVER_HOST=192.168.1.100
SERVER_ADDRESS = os.environ.get("STONK_SERVER_HOST", SERVER_CONNECT_HOST)
try:
    SERVER_PORT_NUM = int(os.environ.get("STONK_SERVER_PORT", SERVER_PORT))
except ValueError:
    SERVER_PORT_NUM = SERVER_PORT

# 重连配置
RECONNECT_INTERVAL = CLIENT_RECONNECT_INTERVAL      # 秒
RECONNECT_MAX_TRIES = CLIENT_RECONNECT_MAX_TRIES
HEARTBEAT_TIMEOUT = CLIENT_HEARTBEAT_TIMEOUT        # 秒

# ==================== UI 配置 ====================

# 窗口大小
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900

# 主题和样式
THEME = "dark"  # dark, light

# 配色方案
COLORS = {
    "background": "#1a1a1a",
    "panel": "#2d2d2d",
    "text": "#ffffff",
    "text_secondary": "#cccccc",
    "success": "#00ff00",
    "danger": "#ff0000",
    "warning": "#ffaa00",
    "info": "#00aaff",
}

# 字体
FONT_FAMILY = "Microsoft YaHei"  # 或 "Segoe UI"
FONT_SIZE_NORMAL = 12
FONT_SIZE_TITLE = 16
FONT_SIZE_LARGE = 20

# ==================== 交易界面配置 ====================

# 图表类型根据步进模式自动选择
CHART_UPDATE_INTERVAL = 100  # 毫秒

# 每页显示的持仓数量
POSITIONS_PER_PAGE = 10

# ==================== 日志配置 ====================

LOG_LEVEL = "INFO"
LOG_FILE = "client.log"

# ==================== 本地数据存储 ====================

# 用户本地数据文件
LOCAL_DATA_DIR = "./data"
USER_CREDENTIALS_FILE = "./data/credentials.json"

# 缓存配置
CACHE_ENABLED = True
CACHE_EXPIRY = 3600  # 秒
