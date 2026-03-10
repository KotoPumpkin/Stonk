"""
数据库模型定义
使用 SQLAlchemy ORM 定义所有数据表
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

Base = declarative_base()


class UserType(enum.Enum):
    """用户类型枚举"""
    ADMIN = "admin"  # 管理员
    ROBOT = "robot"  # 机器人账户
    HUMAN = "human"  # 真人账户


class RobotStrategy(enum.Enum):
    """机器人策略类型枚举"""
    RETAIL = "retail"  # 散户游资策略
    INSTITUTION = "institution"  # 正规机构策略
    SHORT_SELLER = "short_seller"  # 做空组织策略


class User(Base):
    """
    用户模型
    区分管理员、机器人、真人三类账户
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(100), nullable=False)  # 实际应用中应加密存储
    user_type = Column(Enum(UserType), nullable=False)
    
    # 机器人专用字段：策略类型
    strategy_type = Column(Enum(RobotStrategy), nullable=True)
    
    # 是否在线（用于真人账户）
    is_online = Column(Boolean, default=False)
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联账户信息（一对一）
    account = relationship("Account", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, type={self.user_type.value})>"


class Account(Base):
    """
    账户模型
    存储账户的资金信息
    """
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    
    # 现金余额
    cash = Column(Float, default=0.0, nullable=False)
    
    # 初始资金（用于计算收益率）
    initial_capital = Column(Float, default=0.0, nullable=False)
    
    # 最后更新时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联用户
    user = relationship("User", back_populates="account")
    
    # 关联持仓（一对多）
    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")
    
    # 关联交易历史（一对多）
    trades = relationship("Trade", back_populates="account", cascade="all, delete-orphan")
    
    def get_total_asset(self, current_prices):
        """
        计算总资产 = 现金 + 所有持仓市值
        :param current_prices: dict {stock_code: current_price}
        :return: 总资产值
        """
        total = self.cash
        for position in self.positions:
            if position.stock_code in current_prices:
                total += position.quantity * current_prices[position.stock_code]
        return total
    
    def __repr__(self):
        return f"<Account(user_id={self.user_id}, cash={self.cash:.2f})>"


class Position(Base):
    """
    持仓模型
    支持正持仓（做多）和负持仓（做空）
    """
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    stock_code = Column(String(20), nullable=False, index=True)
    
    # 持仓数量（可以为负数，表示做空）
    quantity = Column(Float, default=0.0, nullable=False)
    
    # 平均成本价
    avg_cost = Column(Float, default=0.0, nullable=False)
    
    # 最后更新时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联账户
    account = relationship("Account", back_populates="positions")
    
    # 联合唯一约束：一个账户对同一股票只有一条持仓记录
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
    
    def __repr__(self):
        return f"<Position(account_id={self.account_id}, stock={self.stock_code}, qty={self.quantity})>"


class Stock(Base):
    """
    股票模型
    存储股票基本信息和价格生成参数
    """
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), unique=True, nullable=False, index=True)
    stock_name = Column(String(100), nullable=False)
    
    # 价格生成参数（几何布朗运动）
    initial_price = Column(Float, nullable=False)  # 初始价格
    drift = Column(Float, default=0.0)  # 漂移率 μ
    volatility = Column(Float, default=0.2)  # 波动率 σ
    
    # 是否启用
    is_active = Column(Boolean, default=True)
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联价格历史（一对多）
    price_history = relationship("PriceHistory", back_populates="stock", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Stock(code={self.stock_code}, name={self.stock_name}, price={self.initial_price})>"


class PriceHistory(Base):
    """
    价格历史模型
    存储 OHLCV 数据，支持不同时间粒度
    """
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), ForeignKey('stocks.stock_code'), nullable=False, index=True)
    
    # 时间戳（步进时间）
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # 时间粒度（second, minute, hour, day, month）
    timeframe = Column(String(20), nullable=False, index=True)
    
    # OHLCV 数据
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)  # 成交量（可选）
    
    # 关联股票
    stock = relationship("Stock", back_populates="price_history")
    
    # 联合索引：加速查询
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
    
    def __repr__(self):
        return f"<PriceHistory(stock={self.stock_code}, time={self.timestamp}, close={self.close_price})>"


class Trade(Base):
    """
    交易记录模型
    记录所有买卖交易
    """
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    stock_code = Column(String(20), nullable=False, index=True)
    
    # 交易类型（buy/sell）
    trade_type = Column(String(10), nullable=False)
    
    # 交易数量（正数）
    quantity = Column(Float, nullable=False)
    
    # 交易价格
    price = Column(Float, nullable=False)
    
    # 交易时间
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    
    # 关联账户
    account = relationship("Account", back_populates="trades")
    
    def __repr__(self):
        return f"<Trade(account={self.account_id}, {self.trade_type} {self.quantity} {self.stock_code} @ {self.price})>"


class SystemState(Base):
    """
    系统状态模型
    存储当前系统运行状态
    """
    __tablename__ = 'system_state'
    
    id = Column(Integer, primary_key=True)
    
    # 当前时间（模拟时间）
    current_time = Column(DateTime, nullable=False)
    
    # 当前步进模式（ultra_short, short, day, month）
    step_mode = Column(String(20), nullable=False)
    
    # 步进计数器
    step_count = Column(Integer, default=0)
    
    # 是否处于快进状态
    is_fast_forward = Column(Boolean, default=False)
    
    # 最后更新时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<SystemState(mode={self.step_mode}, step={self.step_count}, time={self.current_time})>"


# 数据库引擎和会话工厂
def get_engine(db_path='trading_system.db'):
    """创建数据库引擎"""
    return create_engine(f'sqlite:///{db_path}', echo=False)


def get_session(engine):
    """创建数据库会话"""
    Session = sessionmaker(bind=engine)
    return Session()


def init_database(db_path='trading_system.db'):
    """
    初始化数据库
    创建所有表
    """
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine
