"""
交易撮合引擎 - Trade Matching Engine

功能：
- 订单簿管理 (Order Book)
- 买卖挂单处理
- 撮合成交逻辑
- 成交价格计算
- 资产更新
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from collections import defaultdict


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"       # 买入
    SELL = "sell"     # 卖出


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"       # 待成交
    PARTIAL = "partial"       # 部分成交
    FILLED = "filled"         # 完全成交
    CANCELLED = "cancelled"   # 已取消


@dataclass
class Order:
    """订单"""
    order_id: str
    user_id: str
    stock_code: str
    side: OrderSide
    quantity: int
    price: float
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.PENDING
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    @property
    def remaining_quantity(self) -> int:
        """剩余数量"""
        return self.quantity - self.filled_quantity
        
    def is_active(self) -> bool:
        """订单是否仍然活跃"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]


@dataclass
class Trade:
    """成交记录"""
    trade_id: str
    buy_order_id: str
    sell_order_id: str
    buyer_id: str
    seller_id: str
    stock_code: str
    quantity: int
    price: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Position:
    """持仓"""
    stock_code: str
    quantity: int = 0         # 持仓数量（可为负，表示融券）
    cost_basis: float = 0.0   # 成本价
    
    def update_buy(self, quantity: int, price: float):
        """更新买入持仓"""
        total_cost = self.cost_basis * self.quantity + price * quantity
        self.quantity += quantity
        if self.quantity != 0:
            self.cost_basis = total_cost / self.quantity
        else:
            self.cost_basis = 0.0
            
    def update_sell(self, quantity: int):
        """更新卖出持仓"""
        self.quantity -= quantity


@dataclass
class Account:
    """账户"""
    user_id: str
    cash: float                                    # 现金（可为负，表示融资）
    positions: Dict[str, Position] = field(default_factory=dict)  # 持仓
    
    def get_position(self, stock_code: str) -> Position:
        """获取持仓（不存在则创建）"""
        if stock_code not in self.positions:
            self.positions[stock_code] = Position(stock_code=stock_code)
        return self.positions[stock_code]
        
    def calculate_total_value(self, current_prices: Dict[str, float]) -> float:
        """计算总资产"""
        stock_value = sum(
            pos.quantity * current_prices.get(pos.stock_code, 0)
            for pos in self.positions.values()
        )
        return self.cash + stock_value
        
    def calculate_profit_loss(
        self, 
        initial_capital: float,
        current_prices: Dict[str, float]
    ) -> float:
        """计算盈亏"""
        return self.calculate_total_value(current_prices) - initial_capital


class TradeManager:
    """交易撮合管理器"""
    
    def __init__(self):
        """初始化交易管理器"""
        self.orders: Dict[str, Order] = {}                    # 所有订单
        self.accounts: Dict[str, Account] = {}                # 所有账户
        self.order_book: Dict[str, List[Order]] = defaultdict(list)  # 订单簿（按股票代码）
        self.trades: List[Trade] = []                         # 成交记录
        self.order_counter = 0
        self.trade_counter = 0
        
    def create_account(self, user_id: str, initial_cash: float) -> Account:
        """
        创建账户
        
        Args:
            user_id: 用户 ID
            initial_cash: 初始资金
            
        Returns:
            Account 对象
        """
        account = Account(user_id=user_id, cash=initial_cash)
        self.accounts[user_id] = account
        return account
        
    def add_account(self, user_id: str, initial_cash: float) -> Account:
        """
        添加账户（create_account 的别名）
        
        Args:
            user_id: 用户 ID
            initial_cash: 初始资金
            
        Returns:
            Account 对象
        """
        return self.create_account(user_id, initial_cash)
        
    def get_account(self, user_id: str) -> Optional[Account]:
        """
        获取账户
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Account 对象或 None
        """
        return self.accounts.get(user_id)
        
    def place_order(
        self,
        user_id: str,
        stock_code: str,
        side: OrderSide,
        quantity: int,
        price: float
    ) -> Optional[Order]:
        """
        挂单
        
        Args:
            user_id: 用户 ID
            stock_code: 股票代码
            side: 买入或卖出
            quantity: 数量
            price: 价格
            
        Returns:
            Order 对象或 None（如果失败）
        """
        # 检查账户是否存在
        if user_id not in self.accounts:
            return None
            
        # 生成订单 ID
        self.order_counter += 1
        order_id = f"ORD{self.order_counter:08d}"
        
        # 创建订单
        order = Order(
            order_id=order_id,
            user_id=user_id,
            stock_code=stock_code,
            side=side,
            quantity=quantity,
            price=price
        )
        
        # 保存订单
        self.orders[order_id] = order
        self.order_book[stock_code].append(order)
        
        return order
        
    def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单 ID
            
        Returns:
            是否成功
        """
        if order_id not in self.orders:
            return False
            
        order = self.orders[order_id]
        if not order.is_active():
            return False
            
        order.status = OrderStatus.CANCELLED
        return True

    def modify_order(
        self,
        order_id: str,
        new_quantity: Optional[int] = None,
        new_price: Optional[float] = None
    ) -> bool:
        """
        修改订单数量或价格（仅限活跃订单）
        
        Args:
            order_id: 订单 ID
            new_quantity: 新数量（None 表示不修改）
            new_price: 新价格（None 表示不修改）
            
        Returns:
            是否成功
        """
        order = self.orders.get(order_id)
        if not order or not order.is_active():
            return False

        if new_quantity is not None:
            if new_quantity <= 0:
                return False
            # 新数量不能小于已成交数量
            if new_quantity < order.filled_quantity:
                return False
            order.quantity = new_quantity

        if new_price is not None:
            if new_price <= 0:
                return False
            order.price = new_price

        return True
        
    def match_orders(self, stock_code: str, market_price: float) -> List[Trade]:
        """
        撮合订单（简化版：所有订单按市价成交）
        
        Args:
            stock_code: 股票代码
            market_price: 市场价格
            
        Returns:
            成交记录列表
        """
        trades = []
        
        # 获取该股票的所有活跃订单
        active_orders = [
            order for order in self.order_book[stock_code]
            if order.is_active()
        ]
        
        # 按市价成交所有订单
        for order in active_orders:
            trade = self._execute_order(order, market_price)
            if trade:
                trades.append(trade)
                self.trades.append(trade)
                
        return trades
        
    def _execute_order(self, order: Order, price: float) -> Optional[Trade]:
        """
        执行订单
        
        Args:
            order: 订单
            price: 成交价格
            
        Returns:
            Trade 对象或 None
        """
        account = self.accounts.get(order.user_id)
        if not account:
            return None
            
        quantity = order.remaining_quantity
        
        # 执行交易
        if order.side == OrderSide.BUY:
            # 买入：扣除现金，增加持仓
            cost = quantity * price
            account.cash -= cost
            position = account.get_position(order.stock_code)
            position.update_buy(quantity, price)
        else:
            # 卖出：增加现金，减少持仓
            revenue = quantity * price
            account.cash += revenue
            position = account.get_position(order.stock_code)
            position.update_sell(quantity)
            
        # 更新订单状态
        order.filled_quantity = order.quantity
        order.status = OrderStatus.FILLED
        
        # 生成成交记录
        self.trade_counter += 1
        trade_id = f"TRD{self.trade_counter:08d}"
        
        # 简化：买方和卖方都是同一个用户
        trade = Trade(
            trade_id=trade_id,
            buy_order_id=order.order_id if order.side == OrderSide.BUY else "MARKET",
            sell_order_id=order.order_id if order.side == OrderSide.SELL else "MARKET",
            buyer_id=order.user_id if order.side == OrderSide.BUY else "MARKET",
            seller_id=order.user_id if order.side == OrderSide.SELL else "MARKET",
            stock_code=order.stock_code,
            quantity=quantity,
            price=price
        )
        
        return trade
        
    def get_account_summary(
        self,
        user_id: str,
        current_prices: Dict[str, float],
        initial_capital: float
    ) -> Optional[Dict]:
        """
        获取账户摘要
        
        Args:
            user_id: 用户 ID
            current_prices: 当前价格字典
            initial_capital: 初始资金
            
        Returns:
            账户摘要字典
        """
        account = self.accounts.get(user_id)
        if not account:
            return None
            
        total_value = account.calculate_total_value(current_prices)
        profit_loss = account.calculate_profit_loss(initial_capital, current_prices)
        
        positions_list = [
            {
                "stock_code": pos.stock_code,
                "quantity": pos.quantity,
                "cost_basis": pos.cost_basis,
                "current_price": current_prices.get(pos.stock_code, 0),
                "market_value": pos.quantity * current_prices.get(pos.stock_code, 0),
                "profit_loss": pos.quantity * current_prices.get(pos.stock_code, 0) - pos.quantity * pos.cost_basis
            }
            for pos in account.positions.values()
            if pos.quantity != 0
        ]
        
        return {
            "user_id": user_id,
            "cash": account.cash,
            "total_value": total_value,
            "profit_loss": profit_loss,
            "profit_loss_percent": (profit_loss / initial_capital * 100) if initial_capital > 0 else 0,
            "positions": positions_list
        }
        
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """
        获取订单状态
        
        Args:
            order_id: 订单 ID
            
        Returns:
            订单状态字典
        """
        order = self.orders.get(order_id)
        if not order:
            return None
            
        return {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "stock_code": order.stock_code,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "filled_quantity": order.filled_quantity,
            "remaining_quantity": order.remaining_quantity,
            "status": order.status.value,
            "created_at": order.created_at
        }
        
    def get_user_orders(self, user_id: str, active_only: bool = False) -> List[Dict]:
        """
        获取用户的所有订单
        
        Args:
            user_id: 用户 ID
            active_only: 是否只返回活跃订单
            
        Returns:
            订单列表
        """
        orders = [
            order for order in self.orders.values()
            if order.user_id == user_id
        ]
        
        if active_only:
            orders = [order for order in orders if order.is_active()]
            
        return [self.get_order_status(order.order_id) for order in orders]
        
    def get_recent_trades(self, stock_code: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        获取最近的成交记录
        
        Args:
            stock_code: 股票代码（None 表示所有股票）
            limit: 返回数量限制
            
        Returns:
            成交记录列表
        """
        trades = self.trades
        
        if stock_code:
            trades = [t for t in trades if t.stock_code == stock_code]
            
        trades = trades[-limit:]
        
        return [
            {
                "trade_id": t.trade_id,
                "stock_code": t.stock_code,
                "quantity": t.quantity,
                "price": t.price,
                "buyer_id": t.buyer_id,
                "seller_id": t.seller_id,
                "timestamp": t.timestamp
            }
            for t in trades
        ]
        
    def reset(self):
        """重置所有数据"""
        self.orders.clear()
        self.accounts.clear()
        self.order_book.clear()
        self.trades.clear()
        self.order_counter = 0
        self.trade_counter = 0
