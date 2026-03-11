"""
价格生成引擎 - Price Generation Engine

支持多种价格模型：
- 随机游走模型 (Random Walk)
- 均值回归模型 (Mean Reversion)
- 趋势跟踪模型 (Trend Following)

支持动态调整：
- 波动率调整
- 新闻情绪修正
- 管理员干预
"""

import random
import math
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class PriceModel(Enum):
    """价格生成模型类型"""
    RANDOM_WALK = "random_walk"           # 随机游走
    MEAN_REVERSION = "mean_reversion"     # 均值回归
    TREND_FOLLOWING = "trend_following"   # 趋势跟踪


@dataclass
class PriceConfig:
    """价格生成配置"""
    model: PriceModel = PriceModel.RANDOM_WALK
    volatility: float = 0.02              # 波动率 (默认 2%)
    drift: float = 0.0001                 # 漂移率 (默认 0.01%)
    mean_reversion_speed: float = 0.1     # 均值回归速度
    trend_strength: float = 0.05          # 趋势强度
    news_sentiment: float = 0.0           # 新闻情绪 (-1 到 1)
    news_impact: float = 0.1              # 新闻影响权重


@dataclass
class StockPriceState:
    """股票价格状态"""
    stock_code: str
    current_price: float
    base_price: float                     # 基准价格（用于均值回归）
    history: List[float] = field(default_factory=list)  # 价格历史
    config: PriceConfig = field(default_factory=PriceConfig)


class PriceEngine:
    """价格生成引擎"""
    
    def __init__(self):
        """初始化价格引擎"""
        self.stocks: Dict[str, StockPriceState] = {}
        self.random_seed: Optional[int] = None
        self._stock_id_counter: int = 1  # 用于生成唯一股票ID
        
    def set_seed(self, seed: int):
        """设置随机种子（用于测试）"""
        self.random_seed = seed
        random.seed(seed)
        
    def add_stock(
        self,
        code: str,
        name: str,
        initial_price: float,
        volatility: float = 0.02,
        drift: float = 0.0001,
        model: str = "random_walk",
        mean_price: Optional[float] = None,
        reversion_speed: Optional[float] = None
    ) -> int:
        """
        添加股票
        
        Args:
            code: 股票代码
            name: 股票名称
            initial_price: 初始价格
            volatility: 波动率
            drift: 漂移率
            model: 价格模型 ("random_walk", "mean_reversion", "trend_following")
            mean_price: 均值回归的目标价格（用于mean_reversion模型）
            reversion_speed: 均值回归速度（用于mean_reversion模型）
            
        Returns:
            股票ID
        """
        # 创建配置
        config = PriceConfig(
            model=PriceModel(model),
            volatility=volatility,
            drift=drift
        )
        
        # 设置均值回归参数
        if mean_price is not None:
            base_price = mean_price
        else:
            base_price = initial_price
            
        if reversion_speed is not None:
            config.mean_reversion_speed = reversion_speed
            
        # 创建股票状态
        self.stocks[code] = StockPriceState(
            stock_code=code,
            current_price=initial_price,
            base_price=base_price,
            history=[initial_price],
            config=config
        )
        
        stock_id = self._stock_id_counter
        self._stock_id_counter += 1
        return stock_id
        
    def remove_stock(self, code: str) -> bool:
        """
        移除股票
        
        Args:
            code: 股票代码
            
        Returns:
            是否成功移除
        """
        if code in self.stocks:
            del self.stocks[code]
            return True
        return False
        
    def get_stock(self, code: str) -> Optional[Dict]:
        """
        获取股票信息
        
        Args:
            code: 股票代码
            
        Returns:
            股票信息字典
        """
        if code not in self.stocks:
            return None
            
        state = self.stocks[code]
        return {
            "code": code,
            "current_price": state.current_price,
            "base_price": state.base_price,
            "volatility": state.config.volatility,
            "drift": state.config.drift,
            "model": state.config.model.value,
            "history_count": len(state.history)
        }
        
    def register_stock(
        self, 
        stock_code: str, 
        initial_price: float,
        config: Optional[PriceConfig] = None
    ):
        """
        注册股票（兼容旧API）
        
        Args:
            stock_code: 股票代码
            initial_price: 初始价格
            config: 价格配置（可选）
        """
        if config is None:
            config = PriceConfig()
            
        self.stocks[stock_code] = StockPriceState(
            stock_code=stock_code,
            current_price=initial_price,
            base_price=initial_price,
            history=[initial_price],
            config=config
        )
        
    def update_config(self, stock_code: str, config: PriceConfig):
        """
        更新股票配置
        
        Args:
            stock_code: 股票代码
            config: 新的价格配置
        """
        if stock_code in self.stocks:
            self.stocks[stock_code].config = config
            
    def adjust_volatility(self, code: str, new_volatility: float):
        """
        调整波动率
        
        Args:
            code: 股票代码
            new_volatility: 新的波动率
        """
        if code in self.stocks:
            self.stocks[code].config.volatility = max(0.0, new_volatility)
            
    def adjust_drift(self, code: str, new_drift: float):
        """
        调整漂移率
        
        Args:
            code: 股票代码
            new_drift: 新的漂移率
        """
        if code in self.stocks:
            self.stocks[code].config.drift = new_drift
            
    def apply_news_sentiment(self, code: str, sentiment: float, impact: float = 0.1):
        """
        应用新闻情绪
        
        Args:
            code: 股票代码
            sentiment: 情绪值 (-1 到 1)
            impact: 影响权重
        """
        if code in self.stocks:
            sentiment = max(-1.0, min(1.0, sentiment))
            self.stocks[code].config.news_sentiment = sentiment
            self.stocks[code].config.news_impact = impact
            
    def set_news_sentiment(self, stock_code: str, sentiment: float):
        """
        设置新闻情绪（兼容旧API）
        
        Args:
            stock_code: 股票代码
            sentiment: 情绪值 (-1 到 1，负数为消极，正数为积极)
        """
        if stock_code in self.stocks:
            sentiment = max(-1.0, min(1.0, sentiment))
            self.stocks[stock_code].config.news_sentiment = sentiment
            
    def update_price(self, code: str) -> Optional[float]:
        """
        更新股票价格（生成下一个价格）
        
        Args:
            code: 股票代码
            
        Returns:
            新价格
        """
        return self.generate_next_price(code)
        
    def generate_next_price(self, stock_code: str) -> Optional[float]:
        """
        生成下一个价格
        
        Args:
            stock_code: 股票代码
            
        Returns:
            新价格，如果股票不存在则返回 None
        """
        if stock_code not in self.stocks:
            return None
            
        state = self.stocks[stock_code]
        config = state.config
        
        # 根据模型类型生成价格
        if config.model == PriceModel.RANDOM_WALK:
            new_price = self._random_walk(state)
        elif config.model == PriceModel.MEAN_REVERSION:
            new_price = self._mean_reversion(state)
        elif config.model == PriceModel.TREND_FOLLOWING:
            new_price = self._trend_following(state)
        else:
            new_price = state.current_price
            
        # 应用新闻情绪影响
        new_price = self._apply_news_sentiment(new_price, config)
        
        # 确保价格为正
        new_price = max(0.01, new_price)
        
        # 更新状态
        state.current_price = new_price
        state.history.append(new_price)
        
        return new_price
        
    def _random_walk(self, state: StockPriceState) -> float:
        """
        随机游走模型
        
        价格变化 = 当前价格 * (漂移率 + 波动率 * 随机数)
        """
        config = state.config
        random_shock = random.gauss(0, 1)  # 标准正态分布
        
        price_change = state.current_price * (
            config.drift + config.volatility * random_shock
        )
        
        return state.current_price + price_change
        
    def _mean_reversion(self, state: StockPriceState) -> float:
        """
        均值回归模型
        
        价格向基准价格回归，回归速度由 mean_reversion_speed 控制
        """
        config = state.config
        
        # 回归力度
        reversion_force = (state.base_price - state.current_price) * config.mean_reversion_speed
        
        # 随机波动
        random_shock = random.gauss(0, 1)
        volatility_change = state.current_price * config.volatility * random_shock
        
        return state.current_price + reversion_force + volatility_change
        
    def _trend_following(self, state: StockPriceState) -> float:
        """
        趋势跟踪模型
        
        根据最近的价格趋势生成新价格
        """
        config = state.config
        
        # 计算趋势（使用最近 5 个价格点）
        if len(state.history) < 5:
            trend = 0
        else:
            recent_prices = state.history[-5:]
            trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
        # 趋势驱动
        trend_change = state.current_price * trend * config.trend_strength
        
        # 随机波动
        random_shock = random.gauss(0, 1)
        volatility_change = state.current_price * config.volatility * random_shock
        
        return state.current_price + trend_change + volatility_change
        
    def _apply_news_sentiment(self, price: float, config: PriceConfig) -> float:
        """
        应用新闻情绪影响
        
        Args:
            price: 当前价格
            config: 价格配置
            
        Returns:
            调整后的价格
        """
        if abs(config.news_sentiment) < 0.001:
            return price
            
        # 新闻影响 = 价格 * 情绪值 * 影响权重
        sentiment_change = price * config.news_sentiment * config.news_impact
        
        return price + sentiment_change
        
    def batch_generate(self, stock_codes: Optional[List[str]] = None) -> Dict[str, float]:
        """
        批量生成所有（或指定）股票的新价格
        
        Args:
            stock_codes: 股票代码列表（None 表示所有股票）
            
        Returns:
            {股票代码: 新价格} 的字典
        """
        if stock_codes is None:
            stock_codes = list(self.stocks.keys())
            
        result = {}
        for code in stock_codes:
            new_price = self.generate_next_price(code)
            if new_price is not None:
                result[code] = new_price
                
        return result
        
    def get_all_prices(self) -> Dict[str, float]:
        """
        获取所有股票当前价格
        
        Returns:
            {股票代码: 当前价格} 的字典
        """
        return {
            code: state.current_price 
            for code, state in self.stocks.items()
        }
        
    def get_current_prices(self) -> Dict[str, float]:
        """
        获取所有股票当前价格（兼容旧API）
        
        Returns:
            {股票代码: 当前价格} 的字典
        """
        return self.get_all_prices()
        
    def get_historical_data(self, code: str, limit: Optional[int] = None) -> List[Tuple[int, float]]:
        """
        获取股票历史数据
        
        Args:
            code: 股票代码
            limit: 返回最近 N 条（None 表示全部）
            
        Returns:
            [(索引, 价格), ...] 的列表
        """
        if code not in self.stocks:
            return []
            
        history = self.stocks[code].history
        
        if limit is None:
            result = [(i, price) for i, price in enumerate(history)]
        else:
            start_idx = max(0, len(history) - limit)
            result = [(i, price) for i, price in enumerate(history[start_idx:], start=start_idx)]
            
        return result
        
    def get_price_history(self, stock_code: str, limit: Optional[int] = None) -> List[float]:
        """
        获取股票价格历史（兼容旧API）
        
        Args:
            stock_code: 股票代码
            limit: 返回最近 N 条（None 表示全部）
            
        Returns:
            价格历史列表
        """
        if stock_code not in self.stocks:
            return []
            
        history = self.stocks[stock_code].history
        
        if limit is None:
            return history.copy()
        else:
            return history[-limit:]
            
    def reset_stock(self, stock_code: str):
        """
        重置股票状态（清空历史，回到初始价格）
        
        Args:
            stock_code: 股票代码
        """
        if stock_code in self.stocks:
            state = self.stocks[stock_code]
            state.current_price = state.base_price
            state.history = [state.base_price]
            state.config.news_sentiment = 0.0
            
    def get_statistics(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票统计信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            统计信息字典
        """
        if stock_code not in self.stocks:
            return None
            
        state = self.stocks[stock_code]
        history = state.history
        
        if len(history) < 2:
            return {
                "stock_code": stock_code,
                "current_price": state.current_price,
                "base_price": state.base_price,
                "count": len(history)
            }
            
        # 计算统计指标
        returns = [
            (history[i] - history[i-1]) / history[i-1] 
            for i in range(1, len(history))
        ]
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        min_price = min(history)
        max_price = max(history)
        
        return {
            "stock_code": stock_code,
            "current_price": state.current_price,
            "base_price": state.base_price,
            "min_price": min_price,
            "max_price": max_price,
            "mean_return": mean_return,
            "volatility": std_dev,
            "count": len(history)
        }
