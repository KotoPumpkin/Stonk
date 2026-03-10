"""
交易管理器
处理买入、卖出、持仓管理（支持做空）
"""
from datetime import datetime
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from models import Account, Position, Trade


class TradeManager:
    """
    交易管理器 - 处理所有交易操作
    支持做多（正持仓）和做空（负持仓）
    """
    
    def __init__(self, session: Session):
        """
        初始化交易管理器
        :param session: 数据库会话
        """
        self.session = session
    
    def buy(
        self,
        account_id: int,
        stock_code: str,
        quantity: float,
        price: float,
        timestamp: datetime = None
    ) -> Tuple[bool, str]:
        """
        买入股票
        - 如果无持仓或正持仓：增加持仓（做多）
        - 如果负持仓（做空状态）：减少空头持仓（平空）
        
        :param account_id: 账户ID
        :param stock_code: 股票代码
        :param quantity: 买入数量（正数）
        :param price: 买入价格
        :param timestamp: 交易时间（默认为当前时间）
        :return: (成功标志, 消息)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        if quantity <= 0:
            return False, "买入数量必须大于0"
        
        # 获取账户
        account = self.session.query(Account).filter(Account.id == account_id).first()
        if not account:
            return False, f"账户 {account_id} 不存在"
        
        # 计算交易金额
        trade_amount = quantity * price
        
        # 检查现金是否足够
        if account.cash < trade_amount:
            return False, f"现金不足：需要 {trade_amount:.2f}，可用 {account.cash:.2f}"
        
        # 获取或创建持仓记录
        position = self.session.query(Position).filter(
            Position.account_id == account_id,
            Position.stock_code == stock_code
        ).first()
        
        if position is None:
            # 新建持仓（做多）
            position = Position(
                account_id=account_id,
                stock_code=stock_code,
                quantity=quantity,
                avg_cost=price,
                updated_at=timestamp
            )
            self.session.add(position)
        else:
            # 更新现有持仓
            if position.quantity >= 0:
                # 当前是多头或无持仓，增加多头
                new_quantity = position.quantity + quantity
                position.avg_cost = (position.avg_cost * position.quantity + price * quantity) / new_quantity
                position.quantity = new_quantity
            else:
                # 当前是空头，买入减少空头（平空）
                position.quantity += quantity
                # 如果平空后变成多头，重新计算成本
                if position.quantity > 0:
                    position.avg_cost = price
            
            position.updated_at = timestamp
        
        # 扣除现金
        account.cash -= trade_amount
        account.updated_at = timestamp
        
        # 记录交易
        trade = Trade(
            account_id=account_id,
            stock_code=stock_code,
            trade_type='buy',
            quantity=quantity,
            price=price,
            timestamp=timestamp
        )
        self.session.add(trade)
        
        # 提交事务
        try:
            self.session.commit()
            return True, f"买入成功：{quantity} 股 {stock_code} @ {price:.2f}"
        except Exception as e:
            self.session.rollback()
            return False, f"交易失败：{str(e)}"
    
    def sell(
        self,
        account_id: int,
        stock_code: str,
        quantity: float,
        price: float,
        timestamp: datetime = None,
        allow_short: bool = True
    ) -> Tuple[bool, str]:
        """
        卖出股票
        - 如果有正持仓：减少持仓（平多）
        - 如果持仓不足且允许做空：创建或增加负持仓（做空）
        
        :param account_id: 账户ID
        :param stock_code: 股票代码
        :param quantity: 卖出数量（正数）
        :param price: 卖出价格
        :param timestamp: 交易时间
        :param allow_short: 是否允许做空
        :return: (成功标志, 消息)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        if quantity <= 0:
            return False, "卖出数量必须大于0"
        
        # 获取账户
        account = self.session.query(Account).filter(Account.id == account_id).first()
        if not account:
            return False, f"账户 {account_id} 不存在"
        
        # 获取或创建持仓记录
        position = self.session.query(Position).filter(
            Position.account_id == account_id,
            Position.stock_code == stock_code
        ).first()
        
        # 计算交易金额
        trade_amount = quantity * price
        
        if position is None:
            # 无持仓
            if not allow_short:
                return False, f"无持仓，无法卖出"
            
            # 创建空头持仓
            position = Position(
                account_id=account_id,
                stock_code=stock_code,
                quantity=-quantity,  # 负数表示空头
                avg_cost=price,
                updated_at=timestamp
            )
            self.session.add(position)
            
            # 卖空获得现金
            account.cash += trade_amount
            
        else:
            # 有持仓
            if position.quantity > 0:
                # 当前是多头，卖出减少多头
                if position.quantity >= quantity:
                    # 持仓足够，正常平多
                    position.quantity -= quantity
                    account.cash += trade_amount
                else:
                    # 持仓不足
                    if not allow_short:
                        return False, f"持仓不足：持有 {position.quantity}，卖出 {quantity}"
                    
                    # 先平掉所有多头，剩余部分做空
                    remaining = quantity - position.quantity
                    account.cash += position.quantity * price  # 平多部分
                    position.quantity = -remaining  # 做空部分
                    position.avg_cost = price  # 重置成本为做空价格
                    account.cash += remaining * price  # 做空获得现金
            
            elif position.quantity < 0:
                # 当前是空头，继续做空增加空头
                new_quantity = position.quantity - quantity
                position.avg_cost = (abs(position.avg_cost * position.quantity) + price * quantity) / abs(new_quantity)
                position.quantity = new_quantity
                account.cash += trade_amount
            
            else:
                # 持仓为0
                if not allow_short:
                    return False, "持仓为0，无法卖出"
                
                # 做空
                position.quantity = -quantity
                position.avg_cost = price
                account.cash += trade_amount
            
            position.updated_at = timestamp
        
        account.updated_at = timestamp
        
        # 记录交易
        trade = Trade(
            account_id=account_id,
            stock_code=stock_code,
            trade_type='sell',
            quantity=quantity,
            price=price,
            timestamp=timestamp
        )
        self.session.add(trade)
        
        # 提交事务
        try:
            self.session.commit()
            return True, f"卖出成功：{quantity} 股 {stock_code} @ {price:.2f}"
        except Exception as e:
            self.session.rollback()
            return False, f"交易失败：{str(e)}"
    
    def get_position(self, account_id: int, stock_code: str) -> Optional[Position]:
        """
        获取持仓信息
        :param account_id: 账户ID
        :param stock_code: 股票代码
        :return: Position对象或None
        """
        return self.session.query(Position).filter(
            Position.account_id == account_id,
            Position.stock_code == stock_code
        ).first()
    
    def get_all_positions(self, account_id: int) -> list:
        """
        获取账户所有持仓
        :param account_id: 账户ID
        :return: Position列表
        """
        return self.session.query(Position).filter(
            Position.account_id == account_id,
            Position.quantity != 0  # 只返回非零持仓
        ).all()
    
    def calculate_position_value(
        self,
        position: Position,
        current_price: float
    ) -> Dict[str, float]:
        """
        计算持仓价值和盈亏
        :param position: 持仓对象
        :param current_price: 当前价格
        :return: 包含市值、成本、盈亏等信息的字典
        """
        quantity = position.quantity
        avg_cost = position.avg_cost
        
        # 成本（买入总金额）
        cost = abs(quantity) * avg_cost
        
        # 市值（当前价值）
        if quantity > 0:
            # 多头：市值 = 数量 × 当前价格
            market_value = quantity * current_price
            unrealized_pnl = market_value - cost
        else:
            # 空头：市值 = -数量 × 当前价格（负值表示欠债）
            market_value = quantity * current_price  # 负数
            # 空头盈亏 = 卖空价格 - 当前价格
            unrealized_pnl = cost - abs(quantity) * current_price
        
        # 收益率
        pnl_rate = (unrealized_pnl / cost * 100) if cost > 0 else 0
        
        return {
            'quantity': quantity,
            'avg_cost': avg_cost,
            'current_price': current_price,
            'cost': cost,
            'market_value': market_value,
            'unrealized_pnl': unrealized_pnl,
            'pnl_rate': pnl_rate
        }
    
    def calculate_total_asset(
        self,
        account_id: int,
        current_prices: Dict[str, float]
    ) -> Dict[str, float]:
        """
        计算账户总资产
        总资产 = 现金 + 所有持仓市值
        
        :param account_id: 账户ID
        :param current_prices: 当前价格字典 {stock_code: price}
        :return: 资产信息字典
        """
        account = self.session.query(Account).filter(Account.id == account_id).first()
        if not account:
            return None
        
        # 现金
        cash = account.cash
        
        # 计算所有持仓市值
        positions = self.get_all_positions(account_id)
        total_position_value = 0
        total_unrealized_pnl = 0
        
        for position in positions:
            if position.stock_code in current_prices:
                current_price = current_prices[position.stock_code]
                pos_info = self.calculate_position_value(position, current_price)
                total_position_value += pos_info['market_value']
                total_unrealized_pnl += pos_info['unrealized_pnl']
        
        # 总资产
        total_asset = cash + total_position_value
        
        # 总收益率
        initial_capital = account.initial_capital
        total_pnl_rate = ((total_asset - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
        
        return {
            'cash': cash,
            'position_value': total_position_value,
            'total_asset': total_asset,
            'unrealized_pnl': total_unrealized_pnl,
            'initial_capital': initial_capital,
            'total_pnl_rate': total_pnl_rate
        }
    
    def get_trade_history(
        self,
        account_id: int,
        stock_code: str = None,
        limit: int = 100
    ) -> list:
        """
        获取交易历史
        :param account_id: 账户ID
        :param stock_code: 股票代码（可选，为None则返回所有）
        :param limit: 返回记录数量限制
        :return: Trade列表
        """
        query = self.session.query(Trade).filter(Trade.account_id == account_id)
        
        if stock_code:
            query = query.filter(Trade.stock_code == stock_code)
        
        query = query.order_by(Trade.timestamp.desc()).limit(limit)
        
        return query.all()
    
    def close_position(
        self,
        account_id: int,
        stock_code: str,
        price: float,
        timestamp: datetime = None
    ) -> Tuple[bool, str]:
        """
        平仓（关闭所有持仓）
        :param account_id: 账户ID
        :param stock_code: 股票代码
        :param price: 平仓价格
        :param timestamp: 时间戳
        :return: (成功标志, 消息)
        """
        position = self.get_position(account_id, stock_code)
        
        if not position or position.quantity == 0:
            return False, f"没有 {stock_code} 的持仓"
        
        if position.quantity > 0:
            # 多头，卖出平仓
            return self.sell(account_id, stock_code, position.quantity, price, timestamp, allow_short=False)
        else:
            # 空头，买入平仓
            return self.buy(account_id, stock_code, abs(position.quantity), price, timestamp)
