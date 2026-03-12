"""
Stonk - 常量定义模块

定义系统中所有的常量、枚举类型等。
"""

from enum import Enum
from typing import Final

# ==================== 步进模式 ====================
class StepMode(Enum):
    """步进模式枚举"""
    SECOND = "second"      # 秒级 - 超短线
    HOUR = "hour"          # 小时级 - 较短线
    DAY = "day"            # 天级 - 短线
    MONTH = "month"        # 月级 - 中线

# ==================== 房间状态 ====================
class RoomStatus(Enum):
    """房间状态枚举"""
    RUNNING = "running"           # 运行中
    PAUSED = "paused"             # 暂停
    FAST_FORWARD = "fast_forward" # 快进中
    COMPLETED = "completed"       # 已完成

# ==================== 机器人策略类型 ====================
class RobotStrategyType(Enum):
    """机器人策略类型枚举"""
    RETAIL = "retail"             # 散户游资 - 高频、追涨杀跌
    INSTITUTION = "institution"   # 正规机构 - 价值导向、低换手
    SHORT_LONG = "short_long"     # 做空/做多组织 - 趋势追踪

# ==================== 订单方向 ====================
class OrderDirection(Enum):
    """订单方向枚举"""
    BUY = "buy"                    # 买入
    SELL = "sell"                 # 卖出

# ==================== 新闻情绪 ====================
class NewsSentiment(Enum):
    """新闻情绪枚举"""
    POSITIVE = "positive"         # 积极
    NEGATIVE = "negative"         # 消极
    NEUTRAL = "neutral"           # 中立

# ==================== 服务器配置常量 ====================
# 服务器绑定地址：使用 0.0.0.0 允许所有网络接口访问，避免 IPv6/IPv4 解析问题
SERVER_HOST: Final[str] = "0.0.0.0"
# 客户端连接的地址（可使用 localhost 或 127.0.0.1）
SERVER_CONNECT_HOST: Final[str] = "127.0.0.1"
SERVER_PORT: Final[int] = 8765
SERVER_MAX_ROOMS: Final[int] = 100
SERVER_MAX_USERS_PER_ROOM: Final[int] = 50
SERVER_HEARTBEAT_INTERVAL: Final[int] = 30  # 秒

# ==================== 客户端配置常量 ====================
CLIENT_RECONNECT_INTERVAL: Final[int] = 5   # 秒
CLIENT_RECONNECT_MAX_TRIES: Final[int] = 10
CLIENT_HEARTBEAT_TIMEOUT: Final[int] = 60   # 秒

# ==================== 数据库配置常量 ====================
DB_PATH: Final[str] = "stonk.db"
DB_INIT_RETRY_TIMES: Final[int] = 3

# ==================== 交易相关常量 ====================
INITIAL_CAPITAL: Final[float] = 100000.0  # 初始资金
MIN_ORDER_QUANTITY: Final[int] = 1
MAX_ORDER_QUANTITY: Final[int] = 1000000

# ==================== 技术指标常量 ====================
MACD_FAST: Final[int] = 12
MACD_SLOW: Final[int] = 26
MACD_SIGNAL: Final[int] = 9
KDJ_PERIOD: Final[int] = 14
RSI_PERIOD: Final[int] = 14
