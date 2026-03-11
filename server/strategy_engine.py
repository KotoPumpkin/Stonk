"""
策略引擎 - Strategy Engine

实现三类机器人交易策略：
1. 散户游资 (Retail) - 高频、追涨杀跌、受新闻情绪影响剧烈
2. 正规机构 (Institution) - 价值导向、低换手率、对财报数据敏感
3. 做空/做多组织 (Trend) - 趋势追踪、单边操作倾向

支持：
- 策略参数动态调整
- 新闻/财报事件响应
- 批量决策执行
"""

import random
import math
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime


class StrategyType(Enum):
    """策略类型枚举"""
    RETAIL = "retail"           # 散户游资
    INSTITUTION = "institution" # 正规机构
    TREND = "trend"             # 做空/做多组织（趋势追踪）


class TradeAction(Enum):
    """交易动作"""
    BUY = "buy"         # 买入
    SELL = "sell"       # 卖出
    HOLD = "hold"       # 持有（不操作）


@dataclass
class StrategyConfig:
    """策略配置基类"""
    # 通用参数
    max_position_ratio: float = 0.8      # 最大持仓比例（占总资金）
    min_cash_reserve: float = 0.1        # 最小现金保留比例
    trade_probability: float = 0.7       # 交易概率（每步是否交易的概率）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RetailConfig(StrategyConfig):
    """散户游资策略配置"""
    momentum_window: int = 3             # 动量计算窗口（最近 N 步）
    sentiment_weight: float = 0.5        # 新闻情绪权重
    trade_frequency: float = 0.8         # 交易频率（更高频）
    position_ratio: float = 0.3          # 单次交易仓位比例
    panic_threshold: float = -0.05       # 恐慌阈值（跌幅超过此值恐慌卖出）
    fomo_threshold: float = 0.05         # FOMO 阈值（涨幅超过此值追涨）


@dataclass
class InstitutionConfig(StrategyConfig):
    """正规机构策略配置"""
    valuation_weight: float = 0.6        # 估值权重
    rebalance_threshold: float = 0.1     # 再平衡阈值（偏离目标仓位 10% 才调整）
    report_sensitivity: float = 0.4      # 财报敏感度
    position_ratio: float = 0.5          # 单次交易仓位比例
    pe_threshold: float = 20.0           # PE 估值阈值
    roe_threshold: float = 0.15          # ROE 阈值


@dataclass
class TrendConfig(StrategyConfig):
    """趋势追踪策略配置"""
    trend_window: int = 10               # 趋势计算窗口
    trend_threshold: float = 0.03        # 趋势触发阈值
    bias: str = "long"                   # 偏好方向："long"或"short"
    leverage: float = 1.0                # 杠杆倍数
    position_ratio: float = 0.4          # 单次交易仓位比例
    stop_loss: float = 0.1               # 止损阈值


@dataclass
class RobotState:
    """机器人状态"""
    robot_id: str
    room_id: str
    name: str
    strategy_type: StrategyType
    cash: float
    holdings: Dict[str, int] = field(default_factory=dict)  # {stock_code: quantity}
    cost_basis: Dict[str, float] = field(default_factory=dict)  # {stock_code: avg_cost}
    decision_history: List[Dict] = field(default_factory=list)
    last_step: int = 0
    
    def get_position_value(self, prices: Dict[str, float]) -> float:
        """计算持仓市值"""
        return sum(
            qty * prices.get(code, 0) 
            for code, qty in self.holdings.items()
        )
    
    def get_total_value(self, prices: Dict[str, float]) -> float:
        """计算总资产"""
        return self.cash + self.get_position_value(prices)
    
    def get_profit_loss(self, prices: Dict[str, float]) -> float:
        """计算盈亏"""
        total_cost = sum(
            qty * self.cost_basis.get(code, 0)
            for code, qty in self.holdings.items()
        )
        current_value = self.get_position_value(prices)
        return current_value - total_cost


@dataclass
class TradeDecision:
    """交易决策"""
    robot_id: str
    stock_code: str
    action: TradeAction
    quantity: int = 0
    reason: str = ""
    confidence: float = 0.0  # 决策置信度 (0-1)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "robot_id": self.robot_id,
            "stock_code": self.stock_code,
            "action": self.action.value,
            "quantity": self.quantity,
            "reason": self.reason,
            "confidence": self.confidence
        }


class BaseStrategy:
    """策略基类"""
    
    def __init__(self, config: StrategyConfig):
        """初始化策略"""
        self.config = config
        self.sentiment_bias: float = 0.0  # 当前情绪偏向
        self.report_impact: Dict[str, float] = {}  # 财报影响 {stock_code: impact}
        
    def set_sentiment(self, sentiment: float):
        """设置情绪偏向 (-1 到 1)"""
        self.sentiment_bias = max(-1.0, min(1.0, sentiment))
        
    def apply_report_impact(self, stock_code: str, impact: float):
        """应用财报影响"""
        self.report_impact[stock_code] = impact
        
    def calculate_position_size(
        self, 
        cash: float, 
        price: float, 
        current_position: int,
        total_value: float
    ) -> int:
        """计算合适的仓位大小"""
        # 可用资金
        available_cash = cash - (total_value * self.config.min_cash_reserve)
        if available_cash <= 0:
            return 0
            
        # 根据配置的比例计算
        target_value = total_value * self.config.position_ratio
        current_value = current_position * price
        
        # 需要调整的金额
        adjust_value = target_value - current_value
        
        if abs(adjust_value) < price:
            return 0
            
        quantity = int(abs(adjust_value) / price)
        return max(0, quantity)
    
    def decide(
        self, 
        state: RobotState, 
        prices: Dict[str, float],
        price_history: Dict[str, List[float]],
        available_stocks: List[str]
    ) -> List[TradeDecision]:
        """
        生成交易决策
        
        Args:
            state: 机器人状态
            prices: 当前价格 {stock_code: price}
            price_history: 价格历史 {stock_code: [prices]}
            available_stocks: 可交易股票列表
            
        Returns:
            交易决策列表
        """
        raise NotImplementedError("Subclasses must implement decide()")


class RetailStrategy(BaseStrategy):
    """
    散户游资策略
    
    特点：
    - 高频交易，追涨杀跌
    - 受新闻情绪影响剧烈
    - 基于短期动量做决策
    - 随机性较大
    """
    
    def __init__(self, config: Optional[RetailConfig] = None):
        if config is None:
            config = RetailConfig()
        super().__init__(config)
        self.config: RetailConfig
        
    def decide(
        self, 
        state: RobotState, 
        prices: Dict[str, float],
        price_history: Dict[str, List[float]],
        available_stocks: List[str]
    ) -> List[TradeDecision]:
        decisions = []
        
        # 随机决定是否交易（模拟散户的冲动性）
        if random.random() > self.config.trade_frequency:
            return decisions
            
        total_value = state.get_total_value(prices)
        
        for stock_code in available_stocks:
            if stock_code not in price_history or len(price_history[stock_code]) < 2:
                continue
                
            history = price_history[stock_code]
            current_price = prices[stock_code]
            
            # 计算短期动量（最近 N 步的涨跌幅）
            window = min(self.config.momentum_window, len(history) - 1)
            if window < 1:
                continue
                
            start_price = history[-window - 1]
            momentum = (current_price - start_price) / start_price if start_price > 0 else 0
            
            # 结合情绪偏向
            adjusted_momentum = momentum + self.sentiment_bias * self.config.sentiment_weight
            
            current_position = state.holdings.get(stock_code, 0)
            
            # 决策逻辑
            action = TradeAction.HOLD
            quantity = 0
            reason = ""
            confidence = 0.0
            
            # 追涨：涨幅超过 FOMO 阈值
            if adjusted_momentum > self.config.fomo_threshold:
                action = TradeAction.BUY
                quantity = self.calculate_position_size(
                    state.cash, current_price, current_position, total_value
                )
                reason = f"FOMO: momentum={momentum:.2%}, sentiment={self.sentiment_bias:.2f}"
                confidence = min(1.0, abs(adjusted_momentum) / self.config.fomo_threshold)
                
            # 杀跌：跌幅超过恐慌阈值
            elif adjusted_momentum < self.config.panic_threshold:
                if current_position > 0:
                    action = TradeAction.SELL
                    quantity = min(current_position, int(current_position * 0.5))  # 卖出一半
                    reason = f"PANIC: momentum={momentum:.2%}, sentiment={self.sentiment_bias:.2f}"
                    confidence = min(1.0, abs(adjusted_momentum) / abs(self.config.panic_threshold))
                    
            # 持仓已有盈利且动量反转
            elif current_position > 0 and momentum < 0 and state.cost_basis.get(stock_code, 0) < current_price:
                action = TradeAction.SELL
                quantity = min(current_position, int(current_position * 0.3))
                reason = f"Take profit: momentum reversed"
                confidence = 0.5
                
            if action != TradeAction.HOLD and quantity > 0:
                decisions.append(TradeDecision(
                    robot_id=state.robot_id,
                    stock_code=stock_code,
                    action=action,
                    quantity=quantity,
                    reason=reason,
                    confidence=confidence
                ))
                
        return decisions


class InstitutionStrategy(BaseStrategy):
    """
    正规机构策略
    
    特点：
    - 价值导向，低换手率
    - 对财报数据敏感
    - 基于均值回归和基本面估值
    - 持仓周期长
    """
    
    def __init__(self, config: Optional[InstitutionConfig] = None):
        if config is None:
            config = InstitutionConfig()
        super().__init__(config)
        self.config: InstitutionConfig
        self.target_positions: Dict[str, float] = {}  # 目标仓位比例
        
    def decide(
        self, 
        state: RobotState, 
        prices: Dict[str, float],
        price_history: Dict[str, List[float]],
        available_stocks: List[str]
    ) -> List[TradeDecision]:
        decisions = []
        
        # 机构交易频率较低
        if random.random() > 0.3:  # 只有 30% 的概率每步交易
            return decisions
            
        total_value = state.get_total_value(prices)
        
        for stock_code in available_stocks:
            if stock_code not in price_history or len(price_history[stock_code]) < 20:
                continue
                
            history = price_history[stock_code]
            current_price = prices[stock_code]
            
            # 计算长期均线（20 步）
            ma20 = sum(history[-20:]) / 20
            
            # 计算估值偏离度（价格相对均线的偏离）
            deviation = (current_price - ma20) / ma20 if ma20 > 0 else 0
            
            # 获取财报影响
            report_factor = self.report_impact.get(stock_code, 0) * self.config.report_sensitivity
            
            # 综合估值评分（负偏离 + 正面财报 = 低估）
            valuation_score = -deviation + report_factor
            
            current_position = state.holdings.get(stock_code, 0)
            current_value = current_position * current_price
            current_ratio = current_value / total_value if total_value > 0 else 0
            
            # 决策逻辑
            action = TradeAction.HOLD
            quantity = 0
            reason = ""
            confidence = 0.0
            
            # 低估时买入（价格低于均线且有正面财报）
            if valuation_score > self.config.rebalance_threshold:
                target_ratio = self.config.position_ratio
                if current_ratio < target_ratio - self.config.rebalance_threshold:
                    action = TradeAction.BUY
                    quantity = self.calculate_position_size(
                        state.cash, current_price, current_position, total_value
                    )
                    reason = f"Undervalued: deviation={deviation:.2%}, report={report_factor:.2f}"
                    confidence = min(1.0, valuation_score / self.config.rebalance_threshold) * self.config.valuation_weight
                    
            # 高估时卖出（价格高于均线）
            elif valuation_score < -self.config.rebalance_threshold:
                if current_position > 0:
                    # 如果严重高估，全部卖出；否则部分减仓
                    if valuation_score < -self.config.rebalance_threshold * 2:
                        quantity = current_position
                        reason = f"Overvalued: sell all"
                    else:
                        quantity = int(current_position * 0.2)
                        reason = f"Reduce position: deviation={deviation:.2%}"
                    
                    action = TradeAction.SELL
                    confidence = min(1.0, abs(valuation_score) / self.config.rebalance_threshold) * self.config.valuation_weight
                    
            if action != TradeAction.HOLD and quantity > 0:
                decisions.append(TradeDecision(
                    robot_id=state.robot_id,
                    stock_code=stock_code,
                    action=action,
                    quantity=quantity,
                    reason=reason,
                    confidence=confidence
                ))
                
        return decisions


class TrendStrategy(BaseStrategy):
    """
    趋势追踪策略（做空/做多组织）
    
    特点：
    - 趋势追踪，明显单边操作倾向
    - 基于中长期趋势做决策
    - 可配置偏好方向
    - 有止损机制
    """
    
    def __init__(self, config: Optional[TrendConfig] = None):
        if config is None:
            config = TrendConfig()
        super().__init__(config)
        self.config: TrendConfig
        
    def decide(
        self, 
        state: RobotState, 
        prices: Dict[str, float],
        price_history: Dict[str, List[float]],
        available_stocks: List[str]
    ) -> List[TradeDecision]:
        decisions = []
        
        # 检查交易概率
        if random.random() > self.config.trade_probability:
            return decisions
            
        total_value = state.get_total_value(prices)
        
        for stock_code in available_stocks:
            if stock_code not in price_history or len(price_history[stock_code]) < self.config.trend_window:
                continue
                
            history = price_history[stock_code]
            current_price = prices[stock_code]
            
            # 计算趋势（最近 N 步的涨跌幅）
            window = self.config.trend_window
            start_price = history[-window]
            trend = (current_price - start_price) / start_price if start_price > 0 else 0
            
            # 应用偏好方向
            if self.config.bias == "long":
                adjusted_trend = trend  # 做多偏好，顺势而为
            else:  # short
                adjusted_trend = -trend  # 做空偏好，反向操作
            
            current_position = state.holdings.get(stock_code, 0)
            
            # 检查止损
            if current_position > 0:
                cost = state.cost_basis.get(stock_code, 0)
                if cost > 0:
                    loss_ratio = (current_price - cost) / cost
                    if loss_ratio < -self.config.stop_loss:
                        # 触发止损
                        decisions.append(TradeDecision(
                            robot_id=state.robot_id,
                            stock_code=stock_code,
                            action=TradeAction.SELL,
                            quantity=current_position,
                            reason=f"Stop loss: loss={loss_ratio:.2%}",
                            confidence=1.0
                        ))
                        continue
            
            # 决策逻辑
            action = TradeAction.HOLD
            quantity = 0
            reason = ""
            confidence = 0.0
            
            # 趋势强劲时跟随
            if abs(adjusted_trend) > self.config.trend_threshold:
                if adjusted_trend > 0:
                    # 上涨趋势，买入
                    action = TradeAction.BUY
                    quantity = self.calculate_position_size(
                        state.cash, current_price, current_position, total_value
                    )
                    reason = f"Trend follow: trend={trend:.2%}, bias={self.config.bias}"
                    confidence = min(1.0, abs(adjusted_trend) / self.config.trend_threshold)
                else:
                    # 下跌趋势，卖出（如果有持仓）
                    if current_position > 0:
                        action = TradeAction.SELL
                        quantity = min(current_position, int(current_position * 0.5))
                        reason = f"Trend reverse: trend={trend:.2%}, bias={self.config.bias}"
                        confidence = min(1.0, abs(adjusted_trend) / self.config.trend_threshold)
                        
            if action != TradeAction.HOLD and quantity > 0:
                decisions.append(TradeDecision(
                    robot_id=state.robot_id,
                    stock_code=stock_code,
                    action=action,
                    quantity=quantity,
                    reason=reason,
                    confidence=confidence
                ))
                
        return decisions


class StrategyEngine:
    """策略引擎主类"""
    
    def __init__(self):
        """初始化策略引擎"""
        self.robots: Dict[str, RobotState] = {}  # robot_id -> RobotState
        self.strategies: Dict[str, BaseStrategy] = {}  # robot_id -> Strategy
        self.room_robots: Dict[str, List[str]] = {}  # room_id -> [robot_ids]
        self._random_seed: Optional[int] = None
        
    def set_seed(self, seed: int):
        """设置随机种子（用于测试）"""
        self._random_seed = seed
        random.seed(seed)
        
    def create_strategy(self, strategy_type: StrategyType, config: Optional[Dict] = None) -> BaseStrategy:
        """
        创建策略实例
        
        Args:
            strategy_type: 策略类型
            config: 策略配置字典（可选）
            
        Returns:
            策略实例
        """
        if strategy_type == StrategyType.RETAIL:
            if config:
                return RetailStrategy(RetailConfig.from_dict(config))
            return RetailStrategy()
        elif strategy_type == StrategyType.INSTITUTION:
            if config:
                return InstitutionStrategy(InstitutionConfig.from_dict(config))
            return InstitutionStrategy()
        elif strategy_type == StrategyType.TREND:
            if config:
                return TrendStrategy(TrendConfig.from_dict(config))
            return TrendStrategy()
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    def register_robot(
        self,
        robot_id: str,
        room_id: str,
        name: str,
        strategy_type: StrategyType,
        initial_cash: float,
        config: Optional[Dict] = None
    ) -> RobotState:
        """
        注册机器人
        
        Args:
            robot_id: 机器人 ID
            room_id: 房间 ID
            name: 机器人名称
            strategy_type: 策略类型
            initial_cash: 初始资金
            config: 策略配置（可选）
            
        Returns:
            RobotState 对象
        """
        # 创建机器人状态
        state = RobotState(
            robot_id=robot_id,
            room_id=room_id,
            name=name,
            strategy_type=strategy_type,
            cash=initial_cash
        )
        
        # 创建策略
        strategy = self.create_strategy(strategy_type, config)
        
        # 存储
        self.robots[robot_id] = state
        self.strategies[robot_id] = strategy
        
        # 添加到房间列表
        if room_id not in self.room_robots:
            self.room_robots[room_id] = []
        self.room_robots[room_id].append(robot_id)
        
        return state
    
    def remove_robot(self, robot_id: str) -> bool:
        """
        移除机器人
        
        Args:
            robot_id: 机器人 ID
            
        Returns:
            是否成功
        """
        if robot_id not in self.robots:
            return False
            
        state = self.robots[robot_id]
        
        # 从房间列表中删除
        if state.room_id in self.room_robots:
            self.room_robots[state.room_id].remove(robot_id)
            
        del self.robots[robot_id]
        del self.strategies[robot_id]
        return True
    
    def get_robot_state(self, robot_id: str) -> Optional[RobotState]:
        """获取机器人状态"""
        return self.robots.get(robot_id)
    
    def get_room_robots(self, room_id: str) -> List[str]:
        """获取房间内所有机器人 ID"""
        return self.room_robots.get(room_id, [])
    
    def update_robot_cash(self, robot_id: str, new_cash: float) -> bool:
        """更新机器人现金"""
        if robot_id in self.robots:
            self.robots[robot_id].cash = new_cash
            return True
        return False
    
    def update_robot_holdings(
        self, 
        robot_id: str, 
        stock_code: str, 
        quantity: int, 
        price: float
    ) -> bool:
        """
        更新机器人持仓
        
        Args:
            robot_id: 机器人 ID
            stock_code: 股票代码
            quantity: 数量变化（正数买入，负数卖出）
            price: 成交价格
        """
        if robot_id not in self.robots:
            return False
            
        state = self.robots[robot_id]
        current_qty = state.holdings.get(stock_code, 0)
        new_qty = current_qty + quantity
        
        if new_qty == 0:
            # 清仓
            state.holdings.pop(stock_code, None)
            state.cost_basis.pop(stock_code, None)
        else:
            state.holdings[stock_code] = new_qty
            # 更新成本价
            if quantity > 0:
                # 买入：加权平均
                total_cost = current_qty * state.cost_basis.get(stock_code, 0) + quantity * price
                state.cost_basis[stock_code] = total_cost / new_qty
            # 卖出时成本价不变
                
        return True
    
    def set_sentiment(self, robot_id: str, sentiment: float) -> bool:
        """设置机器人情绪偏向"""
        if robot_id in self.strategies:
            self.strategies[robot_id].set_sentiment(sentiment)
            return True
        return False
    
    def set_room_sentiment(self, room_id: str, sentiment: float) -> int:
        """
        设置房间内所有机器人的情绪偏向
        
        Returns:
            设置的机器人数量
        """
        count = 0
        for robot_id in self.room_robots.get(room_id, []):
            if self.set_sentiment(robot_id, sentiment):
                count += 1
        return count
    
    def apply_report_impact(
        self, 
        robot_id: str, 
        stock_code: str, 
        impact: float
    ) -> bool:
        """应用财报影响到机器人"""
        if robot_id in self.strategies:
            self.strategies[robot_id].apply_report_impact(stock_code, impact)
            return True
        return False
    
    def update_robot_params(self, robot_id: str, params: Dict[str, Any]) -> bool:
        """
        动态更新机器人策略参数
        
        Args:
            robot_id: 机器人 ID
            params: 参数字典
            
        Returns:
            是否成功
        """
        if robot_id not in self.strategies:
            return False
            
        strategy = self.strategies[robot_id]
        
        for key, value in params.items():
            if hasattr(strategy.config, key):
                setattr(strategy.config, key, value)
                
        return True
    
    def execute_decisions(
        self,
        room_id: str,
        prices: Dict[str, float],
        price_history: Dict[str, List[float]],
        available_stocks: List[str]
    ) -> List[TradeDecision]:
        """
        执行房间内所有机器人的决策
        
        Args:
            room_id: 房间 ID
            prices: 当前价格
            price_history: 价格历史
            available_stocks: 可交易股票列表
            
        Returns:
            所有交易决策列表
        """
        all_decisions = []
        
        for robot_id in self.room_robots.get(room_id, []):
            if robot_id not in self.robots:
                continue
                
            state = self.robots[robot_id]
            strategy = self.strategies[robot_id]
            
            # 生成决策
            decisions = strategy.decide(state, prices, price_history, available_stocks)
            all_decisions.extend(decisions)
            
            # 记录决策历史
            for decision in decisions:
                state.decision_history.append({
                    "step": state.last_step,
                    "decision": decision.to_dict()
                })
                # 限制历史记录长度
                if len(state.decision_history) > 100:
                    state.decision_history = state.decision_history[-100:]
                    
            state.last_step += 1
            
        return all_decisions
    
    def get_robot_summary(self, robot_id: str, prices: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        获取机器人摘要信息
        
        Args:
            robot_id: 机器人 ID
            prices: 当前价格
            
        Returns:
            摘要信息字典
        """
        if robot_id not in self.robots:
            return None
            
        state = self.robots[robot_id]
        total_value = state.get_total_value(prices)
        profit_loss = state.get_profit_loss(prices)
        
        return {
            "robot_id": robot_id,
            "name": state.name,
            "strategy_type": state.strategy_type.value,
            "cash": state.cash,
            "holdings": state.holdings.copy(),
            "cost_basis": state.cost_basis.copy(),
            "total_value": total_value,
            "profit_loss": profit_loss,
            "profit_loss_percent": (profit_loss / (total_value - profit_loss) * 100) if total_value > profit_loss else 0,
            "decision_count": len(state.decision_history)
        }
    
    def get_all_robot_summaries(self, room_id: str, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """获取房间内所有机器人的摘要"""
        summaries = []
        for robot_id in self.room_robots.get(room_id, []):
            summary = self.get_robot_summary(robot_id, prices)
            if summary:
                summaries.append(summary)
        return summaries
    
    def reset_robot(self, robot_id: str, initial_cash: float) -> bool:
        """重置机器人状态"""
        if robot_id not in self.robots:
            return False
            
        state = self.robots[robot_id]
        state.cash = initial_cash
        state.holdings.clear()
        state.cost_basis.clear()
        state.decision_history.clear()
        state.last_step = 0
        
        return True
    
    def clear_room(self, room_id: str):
        """清空房间内所有机器人"""
        for robot_id in self.room_robots.get(room_id, []).copy():
            self.remove_robot(robot_id)
