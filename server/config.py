"""
Stonk 服务器配置模块

服务器的全局配置参数。
"""

from shared.constants import (
    SERVER_HOST,
    SERVER_PORT,
    SERVER_MAX_ROOMS,
    SERVER_MAX_USERS_PER_ROOM,
    SERVER_HEARTBEAT_INTERVAL,
    DB_PATH,
)

# ==================== WebSocket 服务器配置 ====================

# 服务器监听地址和端口
HOST = SERVER_HOST
PORT = SERVER_PORT

# 最大房间数和每个房间的最大用户数
MAX_ROOMS = SERVER_MAX_ROOMS
MAX_USERS_PER_ROOM = SERVER_MAX_USERS_PER_ROOM

# 心跳检测间隔（秒）
HEARTBEAT_INTERVAL = SERVER_HEARTBEAT_INTERVAL

# ==================== 数据库配置 ====================

DATABASE_PATH = DB_PATH

# ==================== 日志配置 ====================

LOG_LEVEL = "INFO"
LOG_FILE = "server.log"

# ==================== 交易配置 ====================

# 价格生成引擎参数
PRICE_ENGINE_MODEL = "random_walk"  # random_walk, mean_reversion, trend_following
PRICE_VOLATILITY = 0.02             # 2% 波动率
PRICE_DRIFT = 0.0001                # 每步漂移

# 交易撮合配置
TRADING_COMMISSION_RATE = 0.001     # 0.1% 手续费
SLIPPAGE = 0.0                      # 滑点（简化版设为 0）

# ==================== 机器人配置 ====================

# 每个房间默认机器人数量
DEFAULT_ROBOTS_PER_ROOM = {
    "retail": 2,           # 散户游资
    "institution": 2,      # 正规机构
    "short_long": 1        # 做空/做多组织
}

# ==================== 步进配置 ====================

# 秒级步进时每秒的价格更新数
SECOND_STEPS_PER_MINUTE = 60

# ==================== 超时配置 ====================

# 客户端心跳超时（秒）
CLIENT_HEARTBEAT_TIMEOUT = 120

# 步进确认超时（秒）
STEP_CONFIRMATION_TIMEOUT = 30
