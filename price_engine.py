"""
价格生成引擎
实现几何布朗运动 (GBM) 算法和K线数据聚合
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from models import Stock, PriceHistory


class PriceGenerator:
    """
    价格生成器 - 实现几何布朗运动 (GBM)
    """
    
    def __init__(self, stock: Stock, dt: float = 1.0):
        """
        初始化价格生成器
        :param stock: Stock对象，包含股票信息和GBM参数
        :param dt: 时间步长（天），例如 1/252 表示1分钟（假设每天252个交易分钟）
        """
        self.stock = stock
        self.current_price = stock.initial_price
        self.drift = stock.drift  # μ
        self.volatility = stock.volatility  # σ
        self.dt = dt
    
    def generate_next_price(self) -> float:
        """
        生成下一个价格（几何布朗运动）
        dS = μ*S*dt + σ*S*dW
        S(t+dt) = S(t) * exp((μ - 0.5*σ²)*dt + σ*√dt*Z)
        :return: 下一个价格
        """
        # 生成标准正态分布随机数
        Z = np.random.standard_normal()
        
        # GBM公式
        drift_term = (self.drift - 0.5 * self.volatility ** 2) * self.dt
        diffusion_term = self.volatility * np.sqrt(self.dt) * Z
        
        # 计算新价格
        self.current_price = self.current_price * np.exp(drift_term + diffusion_term)
        
        # 确保价格不为负（安全检查）
        self.current_price = max(self.current_price, 0.01)
        
        return self.current_price
    
    def generate_batch_prices(self, n_steps: int) -> List[float]:
        """
        批量生成n个价格
        :param n_steps: 步数
        :return: 价格列表
        """
        prices = []
        for _ in range(n_steps):
            prices.append(self.generate_next_price())
        return prices
    
    def reset(self):
        """重置价格到初始值"""
        self.current_price = self.stock.initial_price


class KLineAggregator:
    """
    K线数据聚合器
    将最小时间粒度的价格数据聚合成不同时间周期的K线
    """
    
    def __init__(self, session: Session):
        """
        初始化聚合器
        :param session: 数据库会话
        """
        self.session = session
        self.price_buffer: Dict[str, List[Tuple[datetime, float]]] = {}  # {stock_code: [(time, price), ...]}
    
    def add_tick(self, stock_code: str, timestamp: datetime, price: float):
        """
        添加一个tick价格数据
        :param stock_code: 股票代码
        :param timestamp: 时间戳
        :param price: 价格
        """
        if stock_code not in self.price_buffer:
            self.price_buffer[stock_code] = []
        self.price_buffer[stock_code].append((timestamp, price))
    
    def aggregate_to_kline(
        self,
        stock_code: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, float]:
        """
        将缓冲区的tick数据聚合成K线
        :param stock_code: 股票代码
        :param timeframe: 时间粒度 (minute, hour, day, month)
        :param start_time: 开始时间
        :param end_time: 结束时间
        :return: OHLCV字典
        """
        if stock_code not in self.price_buffer:
            return None
        
        # 筛选时间范围内的数据
        ticks = [
            (t, p) for t, p in self.price_buffer[stock_code]
            if start_time <= t <= end_time
        ]
        
        if not ticks:
            return None
        
        prices = [p for _, p in ticks]
        
        # 计算OHLC
        kline = {
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'volume': len(prices)  # 简化：用tick数量表示成交量
        }
        
        return kline
    
    def save_kline(
        self,
        stock_code: str,
        timestamp: datetime,
        timeframe: str,
        kline_data: Dict[str, float]
    ):
        """
        保存K线数据到数据库
        :param stock_code: 股票代码
        :param timestamp: 时间戳
        :param timeframe: 时间粒度
        :param kline_data: K线数据字典
        """
        price_record = PriceHistory(
            stock_code=stock_code,
            timestamp=timestamp,
            timeframe=timeframe,
            open_price=kline_data['open'],
            high_price=kline_data['high'],
            low_price=kline_data['low'],
            close_price=kline_data['close'],
            volume=kline_data.get('volume', 0)
        )
        self.session.add(price_record)
    
    def aggregate_and_save(
        self,
        stock_code: str,
        current_time: datetime,
        timeframes: List[str] = None
    ):
        """
        聚合并保存K线数据
        :param stock_code: 股票代码
        :param current_time: 当前时间
        :param timeframes: 要聚合的时间粒度列表
        """
        if timeframes is None:
            timeframes = ['minute', 'hour', 'day']
        
        for timeframe in timeframes:
            # 计算时间范围
            start_time, end_time = self._get_time_range(current_time, timeframe)
            
            # 聚合K线
            kline = self.aggregate_to_kline(stock_code, timeframe, start_time, end_time)
            
            if kline:
                # 保存到数据库
                self.save_kline(stock_code, end_time, timeframe, kline)
    
    def _get_time_range(self, current_time: datetime, timeframe: str) -> Tuple[datetime, datetime]:
        """
        根据时间粒度计算时间范围
        :param current_time: 当前时间
        :param timeframe: 时间粒度
        :return: (开始时间, 结束时间)
        """
        if timeframe == 'minute':
            end_time = current_time.replace(second=0, microsecond=0)
            start_time = end_time - timedelta(minutes=1)
        elif timeframe == 'hour':
            end_time = current_time.replace(minute=0, second=0, microsecond=0)
            start_time = end_time - timedelta(hours=1)
        elif timeframe == 'day':
            end_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = end_time - timedelta(days=1)
        elif timeframe == 'month':
            end_time = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # 上个月第一天
            if end_time.month == 1:
                start_time = end_time.replace(year=end_time.year - 1, month=12)
            else:
                start_time = end_time.replace(month=end_time.month - 1)
        else:
            # 默认为秒级
            end_time = current_time
            start_time = end_time - timedelta(seconds=1)
        
        return start_time, end_time
    
    def clear_buffer(self, stock_code: str = None):
        """
        清空缓冲区
        :param stock_code: 股票代码，如果为None则清空所有
        """
        if stock_code:
            self.price_buffer[stock_code] = []
        else:
            self.price_buffer.clear()
    
    def get_latest_klines(
        self,
        stock_code: str,
        timeframe: str,
        n_bars: int = 100
    ) -> pd.DataFrame:
        """
        从数据库获取最新的K线数据
        :param stock_code: 股票代码
        :param timeframe: 时间粒度
        :param n_bars: 获取的K线数量
        :return: DataFrame with columns: [timestamp, open, high, low, close, volume]
        """
        query = self.session.query(PriceHistory).filter(
            PriceHistory.stock_code == stock_code,
            PriceHistory.timeframe == timeframe
        ).order_by(PriceHistory.timestamp.desc()).limit(n_bars)
        
        records = query.all()
        
        if not records:
            return pd.DataFrame()
        
        # 转换为DataFrame（倒序，使最新的在最后）
        df = pd.DataFrame([
            {
                'timestamp': r.timestamp,
                'open': r.open_price,
                'high': r.high_price,
                'low': r.low_price,
                'close': r.close_price,
                'volume': r.volume
            }
            for r in reversed(records)
        ])
        
        return df


class PriceEngine:
    """
    价格引擎 - 统一管理所有股票的价格生成和聚合
    支持两种模式：
    1. 数据库模式：从数据库读取股票信息
    2. 测试模式：直接传入参数
    """
    
    def __init__(self, session: Session = None, dt: float = 1.0/252, 
                 stock_code: str = None, initial_price: float = None,
                 drift: float = None, volatility: float = None):
        """
        初始化价格引擎
        
        数据库模式:
        :param session: 数据库会话
        :param dt: 时间步长（天）
        
        测试模式:
        :param stock_code: 股票代码
        :param initial_price: 初始价格
        :param drift: 漂移率（μ）
        :param volatility: 波动率（σ）
        :param dt: 时间步长（天）
        """
        self.session = session
        self.dt = dt
        self.generators: Dict[str, PriceGenerator] = {}
        self.aggregator = KLineAggregator(session) if session else None
        self.current_prices: Dict[str, float] = {}
        
        # 判断初始化模式
        if stock_code and initial_price is not None and drift is not None and volatility is not None:
            # 测试模式：直接创建单个股票的生成器
            self._initialize_test_mode(stock_code, initial_price, drift, volatility)
        elif session:
            # 数据库模式：初始化所有活跃股票的生成器
            self._initialize_generators()
        else:
            raise ValueError("Must provide either session OR (stock_code, initial_price, drift, volatility)")
    
    def _initialize_test_mode(self, stock_code: str, initial_price: float, drift: float, volatility: float):
        """
        测试模式初始化
        """
        # 创建临时Stock对象
        from types import SimpleNamespace
        stock = SimpleNamespace(
            stock_code=stock_code,
            initial_price=initial_price,
            drift=drift,
            volatility=volatility
        )
        self.generators[stock_code] = PriceGenerator(stock, self.dt)
        self.current_prices[stock_code] = initial_price
    
    def _initialize_generators(self):
        """初始化所有活跃股票的价格生成器"""
        stocks = self.session.query(Stock).filter(Stock.is_active == True).all()
        for stock in stocks:
            self.generators[stock.stock_code] = PriceGenerator(stock, self.dt)
            self.current_prices[stock.stock_code] = stock.initial_price
    
    def step(self, current_time: datetime, save_klines: bool = True) -> Dict[str, float]:
        """
        执行一次价格生成步进
        :param current_time: 当前时间
        :param save_klines: 是否保存K线数据
        :return: 所有股票的当前价格字典 {stock_code: price}
        """
        new_prices = {}
        
        for stock_code, generator in self.generators.items():
            # 生成新价格
            new_price = generator.generate_next_price()
            new_prices[stock_code] = new_price
            self.current_prices[stock_code] = new_price
            
            # 添加到聚合器缓冲区
            self.aggregator.add_tick(stock_code, current_time, new_price)
            
            # 保存秒级原始数据
            if save_klines:
                self.aggregator.save_kline(
                    stock_code,
                    current_time,
                    'second',
                    {'open': new_price, 'high': new_price, 'low': new_price, 'close': new_price, 'volume': 1}
                )
        
        return new_prices
    
    def aggregate_klines(self, current_time: datetime, timeframes: List[str] = None):
        """
        聚合K线数据
        :param current_time: 当前时间
        :param timeframes: 时间粒度列表
        """
        for stock_code in self.generators.keys():
            self.aggregator.aggregate_and_save(stock_code, current_time, timeframes)
    
    def get_current_prices(self) -> Dict[str, float]:
        """获取所有股票的当前价格"""
        return self.current_prices.copy()
    
    def get_price(self, stock_code: str) -> float:
        """获取指定股票的当前价格"""
        return self.current_prices.get(stock_code, 0.0)
    
    def next_price(self) -> float:
        """
        简化方法：生成并返回下一个价格（仅用于单股票测试模式）
        :return: 新价格
        """
        if len(self.generators) != 1:
            raise ValueError("next_price() only works in single-stock test mode")
        
        stock_code = list(self.generators.keys())[0]
        generator = self.generators[stock_code]
        new_price = generator.generate_next_price()
        self.current_prices[stock_code] = new_price
        return new_price
    
    @property
    def current_price(self) -> float:
        """
        属性：获取当前价格（仅用于单股票测试模式）
        """
        if len(self.current_prices) != 1:
            raise ValueError("current_price property only works in single-stock test mode")
        return list(self.current_prices.values())[0]
    
    def get_klines_df(self, stock_code: str, timeframe: str = 'minute', n_bars: int = 100) -> pd.DataFrame:
        """
        获取K线数据DataFrame
        :param stock_code: 股票代码
        :param timeframe: 时间粒度
        :param n_bars: K线数量
        :return: DataFrame
        """
        return self.aggregator.get_latest_klines(stock_code, timeframe, n_bars)
