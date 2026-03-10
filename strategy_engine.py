"""
机器人策略引擎
实现策略接口和示例策略
"""
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from models import User, Account, UserType
from trade_manager import TradeManager


class TradingStrategy(ABC):
    """
    交易策略基类（抽象类）
    所有策略必须继承此类并实现generate_signal方法
    """
    
    def __init__(self, user_id: int, session: Session, stock_code: str):
        """
        初始化策略
        :param user_id: 用户ID（机器人用户）
        :param session: 数据库会话
        :param stock_code: 股票代码
        """
        self.user_id = user_id
        self.session = session
        self.stock_code = stock_code
        
        # 获取用户
        self.user = self.session.query(User).filter(User.id == user_id).first()
        if not self.user:
            raise ValueError(f"User {user_id} 不存在")
        
        if self.user.user_type != UserType.ROBOT:
            raise ValueError(f"User {user_id} 不是机器人用户")
        
        # 获取账户
        account = self.session.query(Account).filter(Account.user_id == user_id).first()
        if not account:
            raise ValueError(f"User {user_id} 没有关联账户")
        
        self.account_id = account.id
        self.trade_manager = TradeManager(session)
    
    @abstractmethod
    def generate_signal(
        self,
        kline_df: pd.DataFrame,
        current_price: float,
        timestamp: datetime
    ) -> Tuple[str, Optional[float]]:
        """
        生成交易信号（抽象方法，子类必须实现）
        
        :param kline_df: K线数据DataFrame，包含列：[timestamp, open, high, low, close, volume]
        :param current_price: 当前价格
        :param timestamp: 当前时间戳
        :return: (信号类型, 交易数量) 
                 信号类型: 'buy', 'sell', 'hold'
                 交易数量: None表示不交易，正数表示交易数量
        """
        pass
    
    def execute_signal(
        self,
        signal: str,
        quantity: Optional[float],
        current_price: float,
        timestamp: datetime
    ) -> Tuple[bool, str]:
        """
        执行交易信号
        :param signal: 信号类型 ('buy', 'sell', 'hold')
        :param quantity: 交易数量
        :param current_price: 当前价格
        :param timestamp: 时间戳
        :return: (成功标志, 消息)
        """
        if signal == 'hold' or quantity is None or quantity <= 0:
            return True, "持仓不变"
        
        if signal == 'buy':
            return self.trade_manager.buy(
                self.account_id,
                self.stock_code,
                quantity,
                current_price,
                timestamp
            )
        elif signal == 'sell':
            return self.trade_manager.sell(
                self.account_id,
                self.stock_code,
                quantity,
                current_price,
                timestamp,
                allow_short=True
            )
        else:
            return False, f"未知信号类型: {signal}"
    
    def get_current_position(self):
        """获取当前持仓"""
        return self.trade_manager.get_position(self.account_id, self.stock_code)
    
    def get_account_info(self):
        """获取账户信息"""
        return self.session.query(Account).filter(Account.id == self.account_id).first()


class MeanReversionStrategy(TradingStrategy):
    """
    均值回归策略
    当价格跌破移动平均线一定百分比时买入，涨破一定百分比时卖出
    """
    
    def __init__(
        self,
        user_id: int,
        session: Session,
        stock_code: str,
        ma_period: int = 20,
        buy_threshold: float = -0.02,  # 跌2%买入
        sell_threshold: float = 0.02,   # 涨2%卖出
        trade_size: float = 100.0       # 每次交易数量
    ):
        """
        初始化均值回归策略
        :param user_id: 机器人用户ID
        :param session: 数据库会话
        :param stock_code: 股票代码
        :param ma_period: 移动平均周期
        :param buy_threshold: 买入阈值（负数，表示跌幅）
        :param sell_threshold: 卖出阈值（正数，表示涨幅）
        :param trade_size: 每次交易数量
        """
        super().__init__(user_id, session, stock_code)
        self.ma_period = ma_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.trade_size = trade_size
    
    def generate_signal(
        self,
        kline_df: pd.DataFrame,
        current_price: float,
        timestamp: datetime
    ) -> Tuple[str, Optional[float]]:
        """
        生成交易信号
        """
        # 数据不足，无法计算
        if len(kline_df) < self.ma_period:
            return 'hold', None
        
        # 计算移动平均
        ma = kline_df['close'].tail(self.ma_period).mean()
        
        # 计算偏离率
        deviation = (current_price - ma) / ma
        
        # 获取当前持仓
        position = self.get_current_position()
        current_quantity = position.quantity if position else 0
        
        # 生成信号
        if deviation <= self.buy_threshold and current_quantity >= 0:
            # 价格跌破阈值，且当前非空头，买入
            return 'buy', self.trade_size
        elif deviation >= self.sell_threshold and current_quantity <= 0:
            # 价格涨破阈值，且当前非多头，卖出
            return 'sell', self.trade_size
        else:
            return 'hold', None


class MomentumStrategy(TradingStrategy):
    """
    动量策略
    当价格上涨趋势强劲时买入，下跌趋势强劲时卖出
    """
    
    def __init__(
        self,
        user_id: int,
        session: Session,
        stock_code: str,
        short_period: int = 5,
        long_period: int = 20,
        trade_size: float = 100.0
    ):
        """
        初始化动量策略
        :param user_id: 机器人用户ID
        :param session: 数据库会话
        :param stock_code: 股票代码
        :param short_period: 短期均线周期
        :param long_period: 长期均线周期
        :param trade_size: 每次交易数量
        """
        super().__init__(user_id, session, stock_code)
        self.short_period = short_period
        self.long_period = long_period
        self.trade_size = trade_size
        self.last_signal = None  # 记录上一次信号，避免重复交易
    
    def generate_signal(
        self,
        kline_df: pd.DataFrame,
        current_price: float,
        timestamp: datetime
    ) -> Tuple[str, Optional[float]]:
        """
        生成交易信号（基于双均线交叉）
        """
        if len(kline_df) < self.long_period:
            return 'hold', None
        
        # 计算短期和长期移动平均
        short_ma = kline_df['close'].tail(self.short_period).mean()
        long_ma = kline_df['close'].tail(self.long_period).mean()
        
        # 获取前一周期的均线（用于判断交叉）
        if len(kline_df) > self.long_period:
            prev_short_ma = kline_df['close'].iloc[-self.short_period-1:-1].mean()
            prev_long_ma = kline_df['close'].iloc[-self.long_period-1:-1].mean()
        else:
            return 'hold', None
        
        # 判断金叉和死叉
        golden_cross = (prev_short_ma <= prev_long_ma) and (short_ma > long_ma)
        death_cross = (prev_short_ma >= prev_long_ma) and (short_ma < long_ma)
        
        # 获取当前持仓
        position = self.get_current_position()
        current_quantity = position.quantity if position else 0
        
        # 生成信号
        if golden_cross and self.last_signal != 'buy':
            # 金叉，买入
            self.last_signal = 'buy'
            return 'buy', self.trade_size
        elif death_cross and self.last_signal != 'sell':
            # 死叉，卖出
            self.last_signal = 'sell'
            return 'sell', self.trade_size
        else:
            return 'hold', None


class RSIStrategy(TradingStrategy):
    """
    RSI策略
    基于相对强弱指数的超买超卖策略
    """
    
    def __init__(
        self,
        user_id: int,
        session: Session,
        stock_code: str,
        rsi_period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
        trade_size: float = 100.0
    ):
        """
        初始化RSI策略
        :param user_id: 机器人用户ID
        :param session: 数据库会话
        :param stock_code: 股票代码
        :param rsi_period: RSI计算周期
        :param oversold: 超卖阈值
        :param overbought: 超买阈值
        :param trade_size: 每次交易数量
        """
        super().__init__(user_id, session, stock_code)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.trade_size = trade_size
    
    def calculate_rsi(self, prices: pd.Series) -> float:
        """
        计算RSI指标
        :param prices: 价格序列
        :return: RSI值
        """
        if len(prices) < self.rsi_period + 1:
            return 50  # 数据不足，返回中性值
        
        # 计算价格变化
        delta = prices.diff()
        
        # 分离涨跌
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        
        # 计算RS和RSI
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def generate_signal(
        self,
        kline_df: pd.DataFrame,
        current_price: float,
        timestamp: datetime
    ) -> Tuple[str, Optional[float]]:
        """
        生成交易信号
        """
        if len(kline_df) < self.rsi_period + 1:
            return 'hold', None
        
        # 计算RSI
        rsi = self.calculate_rsi(kline_df['close'])
        
        # 获取当前持仓
        position = self.get_current_position()
        current_quantity = position.quantity if position else 0
        
        # 生成信号
        if rsi < self.oversold and current_quantity <= 0:
            # 超卖，买入
            return 'buy', self.trade_size
        elif rsi > self.overbought and current_quantity >= 0:
            # 超买，卖出
            return 'sell', self.trade_size
        else:
            return 'hold', None


class SimplePriceDropStrategy(TradingStrategy):
    """
    简单价格下跌策略
    当价格下跌超过一定百分比时买入
    """
    
    def __init__(
        self,
        user_id: int,
        session: Session,
        stock_code: str,
        drop_threshold: float = 0.02,  # 2%跌幅
        rise_threshold: float = 0.02,  # 2%涨幅
        lookback_period: int = 10,
        trade_size: float = 100.0
    ):
        """
        初始化简单价格下跌策略
        :param user_id: 机器人用户ID
        :param session: 数据库会话
        :param stock_code: 股票代码
        :param drop_threshold: 买入跌幅阈值
        :param rise_threshold: 卖出涨幅阈值
        :param lookback_period: 回看周期
        :param trade_size: 每次交易数量
        """
        super().__init__(user_id, session, stock_code)
        self.drop_threshold = drop_threshold
        self.rise_threshold = rise_threshold
        self.lookback_period = lookback_period
        self.trade_size = trade_size
    
    def generate_signal(
        self,
        kline_df: pd.DataFrame,
        current_price: float,
        timestamp: datetime
    ) -> Tuple[str, Optional[float]]:
        """
        生成交易信号
        """
        if len(kline_df) < self.lookback_period:
            return 'hold', None
        
        # 获取回看周期的最高价和最低价
        recent_high = kline_df['high'].tail(self.lookback_period).max()
        recent_low = kline_df['low'].tail(self.lookback_period).min()
        
        # 计算当前价格相对于最高价的跌幅
        drop_from_high = (current_price - recent_high) / recent_high
        
        # 计算当前价格相对于最低价的涨幅
        rise_from_low = (current_price - recent_low) / recent_low
        
        # 获取当前持仓
        position = self.get_current_position()
        current_quantity = position.quantity if position else 0
        
        # 生成信号
        if drop_from_high <= -self.drop_threshold and current_quantity >= 0:
            # 从高点跌超过阈值，买入
            return 'buy', self.trade_size
        elif rise_from_low >= self.rise_threshold and current_quantity <= 0:
            # 从低点涨超过阈值，卖出
            return 'sell', self.trade_size
        else:
            return 'hold', None


class StrategyEngine:
    """
    策略引擎 - 管理所有机器人的策略
    """
    
    def __init__(self, session: Session):
        """
        初始化策略引擎
        :param session: 数据库会话
        """
        self.session = session
        self.strategies: Dict[int, TradingStrategy] = {}  # {bot_id: strategy}
    
    def register_strategy(self, bot_id: int, strategy: TradingStrategy):
        """
        注册策略
        :param bot_id: 机器人ID
        :param strategy: 策略实例
        """
        self.strategies[bot_id] = strategy
    
    def create_strategy(
        self,
        user_id: int,
        stock_code: str,
        strategy_type: str,
        **kwargs
    ) -> TradingStrategy:
        """
        创建并注册策略
        :param user_id: 机器人用户ID
        :param stock_code: 股票代码
        :param strategy_type: 策略类型 ('mean_reversion', 'momentum', 'rsi', 'simple_drop')
        :param kwargs: 策略参数
        :return: 策略实例
        """
        strategy_map = {
            'mean_reversion': MeanReversionStrategy,
            'momentum': MomentumStrategy,
            'rsi': RSIStrategy,
            'simple_drop': SimplePriceDropStrategy
        }
        
        if strategy_type not in strategy_map:
            raise ValueError(f"未知策略类型: {strategy_type}")
        
        strategy_class = strategy_map[strategy_type]
        strategy = strategy_class(user_id, self.session, stock_code, **kwargs)
        self.register_strategy(user_id, strategy)
        
        return strategy
    
    def run_strategy(
        self,
        bot_id: int,
        kline_df: pd.DataFrame,
        current_price: float,
        timestamp: datetime,
        execute: bool = True
    ) -> Tuple[str, Optional[float], Optional[Tuple[bool, str]]]:
        """
        运行策略
        :param bot_id: 机器人ID
        :param kline_df: K线数据
        :param current_price: 当前价格
        :param timestamp: 时间戳
        :param execute: 是否执行交易
        :return: (信号, 数量, 执行结果)
        """
        if bot_id not in self.strategies:
            return 'hold', None, None
        
        strategy = self.strategies[bot_id]
        
        # 生成信号
        signal, quantity = strategy.generate_signal(kline_df, current_price, timestamp)
        
        # 执行交易
        result = None
        if execute and signal != 'hold' and quantity is not None:
            result = strategy.execute_signal(signal, quantity, current_price, timestamp)
        
        return signal, quantity, result
    
    def run_all_strategies(
        self,
        kline_data: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float],
        timestamp: datetime,
        execute: bool = True
    ) -> Dict[int, Tuple[str, Optional[float], Optional[Tuple[bool, str]]]]:
        """
        运行所有策略
        :param kline_data: K线数据字典 {stock_code: DataFrame}
        :param current_prices: 当前价格字典 {stock_code: price}
        :param timestamp: 时间戳
        :param execute: 是否执行交易
        :return: 结果字典 {bot_id: (signal, quantity, result)}
        """
        results = {}
        
        for bot_id, strategy in self.strategies.items():
            stock_code = strategy.stock_code
            
            if stock_code in kline_data and stock_code in current_prices:
                kline_df = kline_data[stock_code]
                current_price = current_prices[stock_code]
                
                result = self.run_strategy(
                    bot_id,
                    kline_df,
                    current_price,
                    timestamp,
                    execute
                )
                results[bot_id] = result
        
        return results
    
    def get_strategy(self, bot_id: int) -> Optional[TradingStrategy]:
        """获取策略实例"""
        return self.strategies.get(bot_id)
    
    def remove_strategy(self, bot_id: int):
        """移除策略"""
        if bot_id in self.strategies:
            del self.strategies[bot_id]
