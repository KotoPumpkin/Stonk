"""
WebSocket 服务器 - 实时通信协议与步进控制器
实现服务端-客户端异步通信和步进管理
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional, List
from enum import Enum
import websockets
from websockets.server import WebSocketServerProtocol
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from models import (User, Account, UserType, Position, Trade, Stock, 
                    FinancialReport, News, NewsImpact, SystemState)
from trade_manager import TradeManager
from price_engine import PriceEngine
from strategy_engine import StrategyEngine
import pandas as pd


class MessageType(Enum):
    """消息类型枚举"""
    STEP_INIT = "STEP_INIT"              # 广播初始状态
    STEP_WAIT = "STEP_WAIT"              # 服务端等待状态
    CLIENT_SUBMIT = "CLIENT_SUBMIT"       # 客户端提交订单
    STEP_UPDATE = "STEP_UPDATE"           # 服务端更新状态
    CLIENT_READY = "CLIENT_READY"         # 客户端完成操作
    ADMIN_FORCE_NEXT = "ADMIN_FORCE_NEXT" # 管理员强制下一步
    FAST_FORWARD_START = "FAST_FORWARD_START"  # 开始快进模式
    FAST_FORWARD_STOP = "FAST_FORWARD_STOP"    # 停止快进模式
    ERROR = "ERROR"                       # 错误消息
    HEARTBEAT = "HEARTBEAT"               # 心跳消息
    
    # 财报相关
    FINANCIAL_REPORT_REQUIRED = "FINANCIAL_REPORT_REQUIRED"  # 需要发布财报
    FINANCIAL_REPORT_SUBMIT = "FINANCIAL_REPORT_SUBMIT"      # 管理员提交财报
    FINANCIAL_REPORT_PUBLISHED = "FINANCIAL_REPORT_PUBLISHED"  # 财报已发布
    
    # 新闻相关
    NEWS_CREATE = "NEWS_CREATE"           # 管理员创建新闻
    NEWS_PUBLISH = "NEWS_PUBLISH"         # 发布待发布的新闻
    NEWS_CONFIRM = "NEWS_CONFIRM"         # 用户确认新闻
    NEWS_BROADCAST = "NEWS_BROADCAST"     # 广播新闻
    
    # 股票管理
    STOCK_UPDATE = "STOCK_UPDATE"         # 更新股票信息（含描述）


class StepController:
    """
    步进控制器
    管理模拟交易的步进过程
    """
    
    def __init__(self, db_url: str, stock_codes: List[str]):
        """
        初始化步进控制器
        :param db_url: 数据库连接URL
        :param stock_codes: 股票代码列表
        """
        self.engine = create_engine(db_url)
        self.SessionMaker = sessionmaker(bind=self.engine)
        self.stock_codes = stock_codes
        
        # 初始化引擎
        self.session = self.SessionMaker()
        self.price_engine = PriceEngine(self.session)  # 只传入session，自动加载数据库中的股票
        self.strategy_engine = StrategyEngine(self.session)
        self.trade_manager = TradeManager(self.session)
        
        # 步进状态
        self.current_step = 0
        self.is_waiting = False
        self.is_fast_forward = False
        
        # 客户端连接管理
        self.connected_clients: Dict[str, WebSocketServerProtocol] = {}  # {user_id: websocket}
        self.human_users: Set[str] = set()  # 真人用户ID集合
        self.ready_users: Set[str] = set()  # 已完成操作的用户ID
        self.admin_users: Set[str] = set()  # 管理员用户ID
        
        # K线数据缓存
        self.kline_history: Dict[str, pd.DataFrame] = {}
        
        # 订单队列
        self.pending_orders: List[Dict] = []
        
        # 系统状态管理
        self.init_system_state()
        
        # 待发布新闻的用户确认追踪
        self.news_confirmations: Dict[int, Set[str]] = {}  # {news_id: set(user_ids)}
    
    def init_system_state(self):
        """初始化或加载系统状态"""
        system_state = self.session.query(SystemState).first()
        if not system_state:
            system_state = SystemState(
                id=1,
                current_time=datetime.now(),
                step_mode='minute',
                step_count=0,
                last_report_year=datetime.now().year - 1,
                requires_financial_report=False,
                has_pending_news=False
            )
            self.session.add(system_state)
            self.session.commit()
        
    async def broadcast(self, message: Dict, exclude: Optional[str] = None):
        """
        广播消息给所有连接的客户端
        :param message: 消息内容
        :param exclude: 排除的用户ID
        """
        disconnected = []
        for user_id, ws in self.connected_clients.items():
            if user_id != exclude:
                try:
                    await ws.send(json.dumps(message))
                except:
                    disconnected.append(user_id)
        
        # 清理断开的连接
        for user_id in disconnected:
            await self.handle_disconnect(user_id)
    
    async def send_to_user(self, user_id: str, message: Dict):
        """
        发送消息给特定用户
        :param user_id: 用户ID
        :param message: 消息内容
        """
        if user_id in self.connected_clients:
            try:
                await self.connected_clients[user_id].send(json.dumps(message))
            except:
                await self.handle_disconnect(user_id)
    
    async def handle_connect(self, user_id: str, websocket: WebSocketServerProtocol):
        """
        处理客户端连接
        :param user_id: 用户ID
        :param websocket: WebSocket连接
        """
        self.connected_clients[user_id] = websocket
        
        # 获取用户信息
        user = self.session.query(User).filter(User.id == int(user_id)).first()
        if user:
            if user.user_type == UserType.HUMAN:
                self.human_users.add(user_id)
            elif user.user_type == UserType.ADMIN:
                self.admin_users.add(user_id)
        
        print(f"用户 {user_id} 已连接")
        
        # 发送当前状态
        await self.send_current_state(user_id)
    
    async def handle_disconnect(self, user_id: str):
        """
        处理客户端断开连接
        :param user_id: 用户ID
        """
        if user_id in self.connected_clients:
            del self.connected_clients[user_id]
        
        self.human_users.discard(user_id)
        self.ready_users.discard(user_id)
        self.admin_users.discard(user_id)
        
        print(f"用户 {user_id} 已断开")
    
    async def send_current_state(self, user_id: str):
        """
        发送当前状态给用户
        :param user_id: 用户ID
        """
        state = await self.get_current_state()
        message = {
            "type": MessageType.STEP_INIT.value,
            "data": state
        }
        await self.send_to_user(user_id, message)
    
    async def get_current_state(self) -> Dict:
        """
        获取当前状态
        :return: 状态字典
        """
        # 获取当前价格
        current_prices = {}
        for stock_code in self.stock_codes:
            price = self.price_engine.get_price(stock_code)
            if price:
                current_prices[stock_code] = price
        
        # 获取所有账户信息
        accounts = self.session.query(Account).all()
        accounts_data = []
        
        for account in accounts:
            user = self.session.query(User).filter(User.id == account.user_id).first()
            
            # 计算总资产
            asset_info = self.trade_manager.calculate_total_asset(
                account.id,
                current_prices
            )
            
            # 获取持仓
            positions = self.trade_manager.get_all_positions(account.id)
            positions_data = []
            for pos in positions:
                if pos.stock_code in current_prices:
                    pos_info = self.trade_manager.calculate_position_value(
                        pos,
                        current_prices[pos.stock_code]
                    )
                    positions_data.append({
                        "stock_code": pos.stock_code,
                        "quantity": pos_info['quantity'],
                        "avg_cost": pos_info['avg_cost'],
                        "current_price": pos_info['current_price'],
                        "market_value": pos_info['market_value'],
                        "unrealized_pnl": pos_info['unrealized_pnl'],
                        "pnl_rate": pos_info['pnl_rate']
                    })
            
            accounts_data.append({
                "user_id": account.user_id,
                "username": user.username,
                "user_type": user.user_type.value,
                "cash": asset_info['cash'],
                "position_value": asset_info['position_value'],
                "total_asset": asset_info['total_asset'],
                "unrealized_pnl": asset_info['unrealized_pnl'],
                "total_pnl_rate": asset_info['total_pnl_rate'],
                "positions": positions_data
            })
        
        return {
            "step": self.current_step,
            "timestamp": datetime.now().isoformat(),
            "prices": current_prices,
            "accounts": accounts_data,
            "is_waiting": self.is_waiting,
            "is_fast_forward": self.is_fast_forward,
            "ready_users": list(self.ready_users),
            "total_human_users": len(self.human_users)
        }
    
    async def handle_client_submit(self, user_id: str, order_data: Dict):
        """
        处理客户端提交订单
        :param user_id: 用户ID
        :param order_data: 订单数据
        """
        # 验证用户
        user = self.session.query(User).filter(User.id == int(user_id)).first()
        if not user or user.user_type != UserType.HUMAN:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "只有真人用户可以提交订单"
            })
            return
        
        # 验证订单
        if not self.validate_order(order_data):
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "订单格式错误"
            })
            return
        
        # 添加到订单队列
        order_data['user_id'] = user_id
        order_data['timestamp'] = datetime.now().isoformat()
        self.pending_orders.append(order_data)
        
        # 发送确认
        await self.send_to_user(user_id, {
            "type": "ORDER_RECEIVED",
            "message": "订单已接收",
            "order": order_data
        })
    
    def validate_order(self, order_data: Dict) -> bool:
        """
        验证订单格式
        :param order_data: 订单数据
        :return: 是否有效
        """
        required_fields = ['action', 'stock_code', 'quantity']
        if not all(field in order_data for field in required_fields):
            return False
        
        if order_data['action'] not in ['buy', 'sell']:
            return False
        
        if order_data['quantity'] <= 0:
            return False
        
        return True
    
    async def handle_client_ready(self, user_id: str):
        """
        处理客户端完成操作
        :param user_id: 用户ID
        """
        if user_id not in self.human_users:
            return
        
        self.ready_users.add(user_id)
        
        # 广播更新
        await self.broadcast({
            "type": "USER_READY",
            "user_id": user_id,
            "ready_count": len(self.ready_users),
            "total_count": len(self.human_users)
        })
        
        # 检查是否所有真人用户都完成
        if len(self.ready_users) >= len(self.human_users):
            await self.execute_step()
    
    async def handle_admin_force_next(self, user_id: str):
        """
        处理管理员强制下一步
        :param user_id: 用户ID
        """
        if user_id not in self.admin_users:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "只有管理员可以强制下一步"
            })
            return
        
        await self.execute_step()
    
    async def handle_fast_forward(self, user_id: str, action: str, steps: int = 10):
        """
        处理快进模式
        :param user_id: 用户ID
        :param action: 'start' 或 'stop'
        :param steps: 快进步数
        """
        if user_id not in self.admin_users:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "只有管理员可以控制快进模式"
            })
            return
        
        if action == 'start':
            self.is_fast_forward = True
            await self.broadcast({
                "type": MessageType.FAST_FORWARD_START.value,
                "steps": steps
            })
            
            # 执行快进
            for i in range(steps):
                if not self.is_fast_forward:
                    break
                await self.execute_step()
                await asyncio.sleep(0.5)  # 短暂延迟以便观察
            
            self.is_fast_forward = False
            await self.broadcast({
                "type": MessageType.FAST_FORWARD_STOP.value
            })
        
        elif action == 'stop':
            self.is_fast_forward = False
            await self.broadcast({
                "type": MessageType.FAST_FORWARD_STOP.value
            })
    
    async def check_step_requirements(self) -> tuple[bool, str]:
        """
        检查步进前的要求
        :return: (是否可以继续, 错误消息)
        """
        system_state = self.session.query(SystemState).first()
        
        # 检查是否需要发布财报
        if system_state.requires_financial_report:
            return False, "需要发布年度财报才能继续"
        
        # 检查是否有待发布的新闻需要所有人确认
        if system_state.has_pending_news:
            pending_news = self.session.query(News).filter(
                News.is_published == True,
                News.published_at.isnot(None)
            ).all()
            
            for news in pending_news:
                import json as json_lib
                confirmed_users = json_lib.loads(news.confirmed_users)
                # 检查是否所有在线真人用户都已确认
                for user_id in self.human_users:
                    if user_id not in confirmed_users:
                        return False, f"所有用户必须确认新闻 '{news.title}' 才能继续"
        
        return True, ""
    
    def check_financial_report_requirement(self):
        """检查是否需要发布年度财报"""
        system_state = self.session.query(SystemState).first()
        current_year = system_state.current_time.year
        
        # 检查是否跨年
        if current_year > system_state.last_report_year:
            # 检查所有股票是否都有该年度的财报
            stocks = self.session.query(Stock).filter(Stock.is_active == True).all()
            missing_reports = []
            
            for stock in stocks:
                report = self.session.query(FinancialReport).filter(
                    FinancialReport.stock_code == stock.stock_code,
                    FinancialReport.year == current_year
                ).first()
                
                if not report:
                    missing_reports.append(stock.stock_code)
            
            if missing_reports:
                system_state.requires_financial_report = True
                self.session.commit()
                return True, missing_reports
        
        return False, []
    
    def publish_pending_news(self):
        """发布待发布的新闻"""
        unpublished_news = self.session.query(News).filter(
            News.is_published == False
        ).all()
        
        if unpublished_news:
            system_state = self.session.query(SystemState).first()
            current_time = system_state.current_time
            
            for news in unpublished_news:
                news.is_published = True
                news.published_at = current_time
                news.confirmed_users = '[]'  # 重置确认列表
            
            system_state.has_pending_news = True
            self.session.commit()
            return unpublished_news
        
        return []
    
    async def execute_step(self):
        """
        执行步进
        """
        # 检查步进要求
        can_proceed, error_msg = await self.check_step_requirements()
        if not can_proceed:
            await self.broadcast({
                "type": MessageType.ERROR.value,
                "message": error_msg
            })
            return
        
        self.is_waiting = False
        self.current_step += 1
        
        print(f"\n=== 执行步进 {self.current_step} ===")
        
        # 更新系统状态时间
        system_state = self.session.query(SystemState).first()
        
        # 根据步进模式增加时间
        step_mode = system_state.step_mode
        if step_mode == 'minute':
            from datetime import timedelta
            system_state.current_time += timedelta(minutes=1)
        elif step_mode == 'day':
            from datetime import timedelta
            system_state.current_time += timedelta(days=1)
        elif step_mode == 'month':
            from datetime import timedelta
            system_state.current_time += timedelta(days=30)
        
        system_state.step_count = self.current_step
        self.session.commit()
        
        # 1. 价格更新 - 使用step方法更新所有价格
        current_prices = self.price_engine.step(datetime.now(), save_klines=True)
        
        # 2. 更新K线历史
        for stock_code in self.stock_codes:
            klines_df = self.price_engine.get_klines_df(stock_code, 'minute', 100)
            if not klines_df.empty:
                self.kline_history[stock_code] = klines_df
        
        # 3. 执行真人用户的待处理订单
        if not self.is_fast_forward:
            for order in self.pending_orders:
                await self.execute_order(order, current_prices)
        
        self.pending_orders.clear()
        
        # 4. 执行机器人策略
        bot_results = self.strategy_engine.run_all_strategies(
            self.kline_history,
            current_prices,
            datetime.now(),
            execute=True
        )
        
        # 5. 提交数据库事务
        self.session.commit()
        
        # 6. 检查是否需要发布财报
        needs_report, missing_stocks = self.check_financial_report_requirement()
        if needs_report:
            await self.broadcast({
                "type": MessageType.FINANCIAL_REPORT_REQUIRED.value,
                "year": system_state.current_time.year,
                "missing_stocks": missing_stocks
            })
        
        # 7. 发布待发布的新闻
        published_news = self.publish_pending_news()
        if published_news:
            news_data = []
            for news in published_news:
                news_data.append({
                    "id": news.id,
                    "title": news.title,
                    "content": news.content,
                    "stock_code": news.stock_code,
                    "impact_type": news.impact_type.value,
                    "impact_strength": news.impact_strength,
                    "published_at": news.published_at.isoformat()
                })
                # 初始化确认追踪
                self.news_confirmations[news.id] = set()
            
            await self.broadcast({
                "type": MessageType.NEWS_BROADCAST.value,
                "news": news_data
            })
        
        # 8. 广播更新
        state = await self.get_current_state()
        await self.broadcast({
            "type": MessageType.STEP_UPDATE.value,
            "data": state,
            "bot_results": {
                str(k): {
                    "signal": v[0],
                    "quantity": v[1],
                    "result": v[2][1] if v[2] else None
                } for k, v in bot_results.items()
            }
        })
        
        # 9. 重置状态，进入等待
        self.ready_users.clear()
        
        if not self.is_fast_forward and len(self.human_users) > 0:
            self.is_waiting = True
            await self.broadcast({
                "type": MessageType.STEP_WAIT.value,
                "message": "等待真人用户操作"
            })
        else:
            # 快进模式或无真人用户，自动继续
            pass
    
    async def execute_order(self, order: Dict, current_prices: Dict):
        """
        执行订单
        :param order: 订单数据
        :param current_prices: 当前价格
        """
        user_id = int(order['user_id'])
        stock_code = order['stock_code']
        action = order['action']
        quantity = order['quantity']
        
        # 获取账户
        account = self.session.query(Account).filter(
            Account.user_id == user_id
        ).first()
        
        if not account:
            return
        
        # 获取当前价格
        if stock_code not in current_prices:
            return
        
        price = current_prices[stock_code]
        
        # 执行交易
        if action == 'buy':
            success, msg = self.trade_manager.buy(
                account.id,
                stock_code,
                quantity,
                price,
                datetime.now()
            )
        else:
            success, msg = self.trade_manager.sell(
                account.id,
                stock_code,
                quantity,
                price,
                datetime.now(),
                allow_short=True
            )
        
        # 发送执行结果
        await self.send_to_user(order['user_id'], {
            "type": "ORDER_EXECUTED",
            "success": success,
            "message": msg,
            "order": order
        })
    
    async def handle_financial_report_submit(self, user_id: str, report_data: Dict):
        """
        处理管理员提交财报
        :param user_id: 用户ID
        :param report_data: 财报数据
        """
        if user_id not in self.admin_users:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "只有管理员可以发布财报"
            })
            return
        
        stock_code = report_data.get('stock_code')
        year = report_data.get('year')
        content = report_data.get('content')
        
        if not stock_code or not year or not content:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "财报数据不完整"
            })
            return
        
        # 创建财报
        system_state = self.session.query(SystemState).first()
        report = FinancialReport(
            stock_code=stock_code,
            year=year,
            content=content,
            published_at=system_state.current_time
        )
        self.session.add(report)
        
        # 检查是否所有股票都有财报了
        stocks = self.session.query(Stock).filter(Stock.is_active == True).all()
        all_reported = True
        for stock in stocks:
            existing_report = self.session.query(FinancialReport).filter(
                FinancialReport.stock_code == stock.stock_code,
                FinancialReport.year == year
            ).first()
            if not existing_report and stock.stock_code != stock_code:
                all_reported = False
                break
        
        if all_reported:
            system_state.requires_financial_report = False
            system_state.last_report_year = year
        
        self.session.commit()
        
        # 广播财报发布
        await self.broadcast({
            "type": MessageType.FINANCIAL_REPORT_PUBLISHED.value,
            "report": {
                "stock_code": stock_code,
                "year": year,
                "content": content,
                "published_at": report.published_at.isoformat()
            },
            "all_reported": all_reported
        })
    
    async def handle_news_create(self, user_id: str, news_data: Dict):
        """
        处理管理员创建新闻
        :param user_id: 用户ID
        :param news_data: 新闻数据
        """
        if user_id not in self.admin_users:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "只有管理员可以创建新闻"
            })
            return
        
        title = news_data.get('title')
        content = news_data.get('content')
        stock_code = news_data.get('stock_code')  # 可为None
        impact_type = news_data.get('impact_type')
        impact_strength = news_data.get('impact_strength', 0.5)
        
        if not title or not content or not impact_type:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "新闻数据不完整"
            })
            return
        
        # 验证影响类型
        try:
            impact_enum = NewsImpact[impact_type.upper()]
        except KeyError:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "无效的影响类型"
            })
            return
        
        # 创建新闻（待发布状态）
        news = News(
            title=title,
            content=content,
            stock_code=stock_code,
            impact_type=impact_enum,
            impact_strength=impact_strength,
            is_published=False
        )
        self.session.add(news)
        self.session.commit()
        
        # 通知管理员
        await self.send_to_user(user_id, {
            "type": "NEWS_CREATED",
            "message": "新闻已创建，将在下一步开始时发布",
            "news": {
                "id": news.id,
                "title": title,
                "content": content,
                "stock_code": stock_code,
                "impact_type": impact_type,
                "impact_strength": impact_strength
            }
        })
    
    async def handle_news_confirm(self, user_id: str, news_id: int):
        """
        处理用户确认新闻
        :param user_id: 用户ID
        :param news_id: 新闻ID
        """
        news = self.session.query(News).filter(News.id == news_id).first()
        if not news or not news.is_published:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "新闻不存在或未发布"
            })
            return
        
        # 更新确认列表
        import json as json_lib
        confirmed_users = json_lib.loads(news.confirmed_users)
        if user_id not in confirmed_users:
            confirmed_users.append(user_id)
            news.confirmed_users = json_lib.dumps(confirmed_users)
            self.session.commit()
        
        # 更新确认追踪
        if news_id in self.news_confirmations:
            self.news_confirmations[news_id].add(user_id)
        
        # 检查是否所有真人用户都已确认
        all_confirmed = all(
            uid in confirmed_users for uid in self.human_users
        )
        
        # 广播确认状态
        await self.broadcast({
            "type": "NEWS_CONFIRMED",
            "news_id": news_id,
            "user_id": user_id,
            "confirmed_count": len(confirmed_users),
            "total_count": len(self.human_users),
            "all_confirmed": all_confirmed
        })
        
        # 如果所有人都确认了，清除待确认状态
        if all_confirmed:
            system_state = self.session.query(SystemState).first()
            # 检查是否还有其他待确认的新闻
            other_pending = self.session.query(News).filter(
                News.is_published == True,
                News.id != news_id
            ).all()
            
            has_other_pending = False
            for other_news in other_pending:
                other_confirmed = json_lib.loads(other_news.confirmed_users)
                if not all(uid in other_confirmed for uid in self.human_users):
                    has_other_pending = True
                    break
            
            if not has_other_pending:
                system_state.has_pending_news = False
                self.session.commit()
    
    async def handle_stock_update(self, user_id: str, stock_data: Dict):
        """
        处理管理员更新股票信息（包括描述）
        :param user_id: 用户ID
        :param stock_data: 股票数据
        """
        if user_id not in self.admin_users:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "只有管理员可以更新股票信息"
            })
            return
        
        stock_code = stock_data.get('stock_code')
        if not stock_code:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "缺少股票代码"
            })
            return
        
        stock = self.session.query(Stock).filter(
            Stock.stock_code == stock_code
        ).first()
        
        if not stock:
            await self.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": "股票不存在"
            })
            return
        
        # 更新字段
        if 'stock_name' in stock_data:
            stock.stock_name = stock_data['stock_name']
        if 'description' in stock_data:
            stock.description = stock_data['description']
        if 'drift' in stock_data:
            stock.drift = stock_data['drift']
        if 'volatility' in stock_data:
            stock.volatility = stock_data['volatility']
        
        self.session.commit()
        
        # 广播更新
        await self.broadcast({
            "type": MessageType.STOCK_UPDATE.value,
            "stock": {
                "stock_code": stock.stock_code,
                "stock_name": stock.stock_name,
                "description": stock.description,
                "drift": stock.drift,
                "volatility": stock.volatility
            }
        })


class WebSocketServer:
    """
    WebSocket 服务器
    """
    
    def __init__(self, step_controller: StepController, host: str = "0.0.0.0", port: int = 8765):
        """
        初始化WebSocket服务器
        :param step_controller: 步进控制器
        :param host: 监听地址
        :param port: 监听端口
        """
        self.controller = step_controller
        self.host = host
        self.port = port
    
    async def handle_client(self, websocket: WebSocketServerProtocol):
        """
        处理客户端连接
        :param websocket: WebSocket连接
        """
        user_id = None
        
        try:
            # 接收第一条消息应该是认证消息
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)
            
            if auth_data.get('type') != 'AUTH':
                await websocket.send(json.dumps({
                    "type": MessageType.ERROR.value,
                    "message": "首条消息必须是认证消息"
                }))
                return
            
            user_id = str(auth_data.get('user_id'))
            
            # 处理连接
            await self.controller.handle_connect(user_id, websocket)
            
            # 消息循环
            async for message in websocket:
                await self.handle_message(user_id, message)
        
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"处理客户端时出错: {e}")
        finally:
            if user_id:
                await self.controller.handle_disconnect(user_id)
    
    async def handle_message(self, user_id: str, message: str):
        """
        处理客户端消息
        :param user_id: 用户ID
        :param message: 消息内容
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == MessageType.CLIENT_SUBMIT.value:
                await self.controller.handle_client_submit(user_id, data.get('order', {}))
            
            elif msg_type == MessageType.CLIENT_READY.value:
                await self.controller.handle_client_ready(user_id)
            
            elif msg_type == MessageType.ADMIN_FORCE_NEXT.value:
                await self.controller.handle_admin_force_next(user_id)
            
            elif msg_type == MessageType.FAST_FORWARD_START.value:
                steps = data.get('steps', 10)
                await self.controller.handle_fast_forward(user_id, 'start', steps)
            
            elif msg_type == MessageType.FAST_FORWARD_STOP.value:
                await self.controller.handle_fast_forward(user_id, 'stop')
            
            elif msg_type == MessageType.HEARTBEAT.value:
                # 心跳响应
                await self.controller.send_to_user(user_id, {
                    "type": MessageType.HEARTBEAT.value,
                    "timestamp": datetime.now().isoformat()
                })
            
            elif msg_type == MessageType.FINANCIAL_REPORT_SUBMIT.value:
                await self.controller.handle_financial_report_submit(
                    user_id, 
                    data.get('report', {})
                )
            
            elif msg_type == MessageType.NEWS_CREATE.value:
                await self.controller.handle_news_create(
                    user_id,
                    data.get('news', {})
                )
            
            elif msg_type == MessageType.NEWS_CONFIRM.value:
                await self.controller.handle_news_confirm(
                    user_id,
                    data.get('news_id')
                )
            
            elif msg_type == MessageType.STOCK_UPDATE.value:
                await self.controller.handle_stock_update(
                    user_id,
                    data.get('stock', {})
                )
        
        except Exception as e:
            print(f"处理消息时出错: {e}")
            await self.controller.send_to_user(user_id, {
                "type": MessageType.ERROR.value,
                "message": str(e)
            })
    
    async def start(self):
        """
        启动服务器
        """
        print(f"WebSocket服务器启动在 {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # 永久运行


async def main():
    """
    主函数 - 示例用法
    """
    # 配置
    DB_URL = "sqlite:///trading_system.db"
    STOCK_CODES = ["AAPL", "GOOGL", "MSFT"]
    
    # 创建步进控制器
    controller = StepController(DB_URL, STOCK_CODES)
    
    # 创建WebSocket服务器
    server = WebSocketServer(controller)
    
    # 启动服务器
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
