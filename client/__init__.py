"""
Stonk 股票模拟交易系统 - 客户端包

本包包含客户端的核心逻辑：WebSocket 通信、UI 界面、
用户交互逻辑等。
"""

import logging
import sys
from client.config import LOG_LEVEL, LOG_FILE

# ==================== 日志配置 ====================

def setup_logging():
    """
    配置客户端日志系统，输出到控制台和文件。
    """
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # 清除现有的处理器（避免重复）
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # 控制台处理器 - 确保日志输出到控制台
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器 - 同时记录到文件
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(getattr(logging, LOG_LEVEL))
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create log file handler: {e}")
    
    logging.info("Client logging initialized")

# 初始化日志配置
setup_logging()

__version__ = "1.0.0"
__author__ = "Development Team"
