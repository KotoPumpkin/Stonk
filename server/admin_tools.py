"""
Stonk - 管理员工具模块

实现管理员干预功能：
- 新闻发布系统
- 财报发布系统
- 价格/参数干预
- 房间管理（销毁、踢人）
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from shared.message_protocol import MessageType, create_message
from shared.utils import generate_id, get_timestamp


class AdminTools:
    """管理员工具类"""
    
    def __init__(self, db, price_engines: Dict, trade_managers: Dict, 
                 step_controllers: Dict, strategy_engines: Dict):
        """
        初始化工具
        
        Args:
            db: 数据库管理器
            price_engines: {room_id: PriceEngine}
            trade_managers: {room_id: TradeManager}
            step_controllers: {room_id: StepController}
            strategy_engines: {room_id: StrategyEngine}
        """
        self.db = db
        self.price_engines = price_engines
        self.trade_managers = trade_managers
        self.step_controllers = step_controllers
        self.strategy_engines = strategy_engines
    
    # ==================== 新闻发布系统 ====================
    
    async def publish_news(
        self,
        room_id: str,
        title: str,
        content: str,
        sentiment: str,
        affected_stocks: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        发布新闻
        
        Args:
            room_id: 房间 ID
            title: 新闻标题
            content: 新闻内容
            sentiment: 情绪 ("positive", "negative", "neutral")
            affected_stocks: 受影响的股票列表（None 表示全局）
            
        Returns:
            广播消息字典，失败返回 None
        """
        if room_id not in self.price_engines:
            return None
        
        # 映射情绪值
        sentiment_map = {
            "positive": 0.5,
            "negative": -0.5,
            "neutral": 0.0
        }
        sentiment_value = sentiment_map.get(sentiment.lower(), 0.0)
        
        # 存储到数据库
        news_id = await self._save_news_to_db(
            room_id, title, content, sentiment, affected_stocks or []
        )
        
        if not news_id:
            return None
        
        # 应用情绪到价格引擎
        price_engine = self.price_engines[room_id]
        if affected_stocks:
            for stock_code in affected_stocks:
                price_engine.apply_news_sentiment(stock_code, sentiment_value, 0.1)
        else:
            # 全局影响所有股票
            for stock_code in price_engine.stocks.keys():
                price_engine.apply_news_sentiment(stock_code, sentiment_value, 0.1)
        
        # 应用情绪到策略引擎（机器人）
        if room_id in self.strategy_engines:
            self.strategy_engines[room_id].set_room_sentiment(room_id, sentiment_value)
        
        # 生成广播消息
        broadcast_msg = create_message(
            MessageType.NEWS_BROADCAST,
            {
                "news_id": news_id,
                "title": title,
                "content": content,
                "sentiment": sentiment,
                "affected_stocks": affected_stocks or [],
                "published_at": get_timestamp()
            },
            room_id
        )
        
        return {
            "news_id": news_id,
            "broadcast_msg": broadcast_msg,
            "sentiment_value": sentiment_value
        }
    
    async def _save_news_to_db(
        self,
        room_id: str,
        title: str,
        content: str,
        sentiment: str,
        affected_stocks: List[str]
    ) -> Optional[str]:
        """保存新闻到数据库"""
        try:
            import json
            cursor = await self.db.connection.cursor()
            news_id = generate_id()
            now = get_timestamp()
            
            await cursor.execute("""
                INSERT INTO News (id, room_id, title, content, sentiment, affected_stocks, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (news_id, room_id, title, content, sentiment, 
                  json.dumps(affected_stocks), now))
            
            await self.db.connection.commit()
            return news_id
        except Exception as e:
            print(f"Error saving news: {e}")
            return None
    
    # ==================== 财报发布系统 ====================
    
    async def publish_report(
        self,
        room_id: str,
        stock_code: str,
        pe_ratio: Optional[float] = None,
        roe: Optional[float] = None,
        net_income: Optional[float] = None,
        revenue: Optional[float] = None,
        manager_weight: float = 1.0
    ) -> Optional[Dict]:
        """
        发布财报
        
        Args:
            room_id: 房间 ID
            stock_code: 股票代码
            pe_ratio: 市盈率
            roe: 净资产收益率
            net_income: 净利润
            revenue: 营收
            manager_weight: 管理员设定的策略影响权重
            
        Returns:
            广播消息字典，失败返回 None
        """
        if room_id not in self.strategy_engines:
            return None
        
        # 计算财报影响因子（简化：基于 ROE 和净利润）
        report_impact = 0.0
        if roe is not None:
            report_impact += roe * 0.5  # ROE 权重 50%
        if net_income is not None:
            # 假设净利润为正且较大则有正面影响
            report_impact += min(0.5, max(-0.5, net_income / 1000000))  # 归一化
        
        # 存储到数据库
        report_id = await self._save_report_to_db(
            room_id, stock_code, pe_ratio, roe, net_income, revenue, manager_weight
        )
        
        if not report_id:
            return None
        
        # 应用财报影响到策略引擎
        strategy_engine = self.strategy_engines[room_id]
        for robot_id in strategy_engine.get_room_robots(room_id):
            strategy_engine.apply_report_impact(robot_id, stock_code, report_impact)
        
        # 生成广播消息
        broadcast_msg = create_message(
            MessageType.REPORT_BROADCAST,
            {
                "report_id": report_id,
                "stock_code": stock_code,
                "pe_ratio": pe_ratio,
                "roe": roe,
                "net_income": net_income,
                "revenue": revenue,
                "manager_weight": manager_weight,
                "published_at": get_timestamp()
            },
            room_id
        )
        
        return {
            "report_id": report_id,
            "broadcast_msg": broadcast_msg,
            "report_impact": report_impact
        }
    
    async def _save_report_to_db(
        self,
        room_id: str,
        stock_code: str,
        pe_ratio: Optional[float],
        roe: Optional[float],
        net_income: Optional[float],
        revenue: Optional[float],
        manager_weight: float
    ) -> Optional[str]:
        """保存财报到数据库"""
        try:
            cursor = await self.db.connection.cursor()
            report_id = generate_id()
            now = get_timestamp()
            
            # 获取股票 ID
            stock = await self._get_stock_by_code(stock_code)
            stock_id = stock["id"] if stock else None
            
            if not stock_id:
                return None
            
            await cursor.execute("""
                INSERT INTO Reports (id, room_id, stock_id, pe_ratio, roe, net_income, revenue, manager_weight, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (report_id, room_id, stock_id, pe_ratio, roe, net_income, revenue, manager_weight, now))
            
            await self.db.connection.commit()
            return report_id
        except Exception as e:
            print(f"Error saving report: {e}")
            return None
    
    async def _get_stock_by_code(self, stock_code: str) -> Optional[Dict]:
        """根据股票代码获取股票信息"""
        try:
            cursor = await self.db.connection.cursor()
            await cursor.execute("""
                SELECT id, code, name, initial_price, issued_shares, description 
                FROM Stocks WHERE code = ?
            """, (stock_code,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            return {
                "id": row[0],
                "code": row[1],
                "name": row[2],
                "initial_price": row[3],
                "issued_shares": row[4],
                "description": row[5]
            }
        except Exception as e:
            print(f"Error getting stock: {e}")
            return None
    
    async def check_report_due(self, room_id: str) -> bool:
        """
        检查房间是否需要发布财报（满 365 天级步进）
        
        Args:
            room_id: 房间 ID
            
        Returns:
            是否需要发布财报
        """
        if room_id not in self.step_controllers:
            return False
        
        room_context = self.step_controllers[room_id].get_room(room_id)
        if not room_context:
            return False
        
        # 检查当前步数是否是 365 的倍数
        return room_context.current_step > 0 and room_context.current_step % 365 == 0
    
    # ==================== 价格/参数干预 ====================
    
    def intervene_stock_params(
        self,
        room_id: str,
        stock_code: str,
        volatility: Optional[float] = None,
        drift: Optional[float] = None,
        model: Optional[str] = None
    ) -> bool:
        """
        干预股票价格参数
        
        Args:
            room_id: 房间 ID
            stock_code: 股票代码
            volatility: 波动率（可选）
            drift: 漂移率（可选）
            model: 价格模型（可选）
            
        Returns:
            是否成功
        """
        if room_id not in self.price_engines:
            return False
        
        price_engine = self.price_engines[room_id]
        
        if stock_code not in price_engine.stocks:
            return False
        
        # 更新波动率
        if volatility is not None:
            price_engine.adjust_volatility(stock_code, max(0.0, volatility))
        
        # 更新漂移率
        if drift is not None:
            price_engine.adjust_drift(stock_code, drift)
        
        # 更新价格模型
        if model is not None:
            from server.price_engine import PriceModel, PriceConfig
            try:
                price_model = PriceModel(model)
                config = price_engine.stocks[stock_code].config
                new_config = PriceConfig(
                    model=price_model,
                    volatility=config.volatility,
                    drift=config.drift,
                    mean_reversion_speed=config.mean_reversion_speed,
                    trend_strength=config.trend_strength,
                    news_sentiment=config.news_sentiment,
                    news_impact=config.news_impact
                )
                price_engine.update_config(stock_code, new_config)
            except ValueError:
                return False
        
        return True
    
    def set_stock_price(
        self,
        room_id: str,
        stock_code: str,
        new_price: float
    ) -> bool:
        """
        直接设定股票价格
        
        Args:
            room_id: 房间 ID
            stock_code: 股票代码
            new_price: 新价格
            
        Returns:
            是否成功
        """
        if room_id not in self.price_engines:
            return False
        
        price_engine = self.price_engines[room_id]
        
        if stock_code not in price_engine.stocks:
            return False
        
        # 直接设置价格
        price_engine.stocks[stock_code].current_price = max(0.01, new_price)
        price_engine.stocks[stock_code].history.append(max(0.01, new_price))
        
        return True
    
    def update_robot_params(
        self,
        robot_id: str,
        params: Dict[str, Any]
    ) -> bool:
        """
        更新机器人策略参数
        
        Args:
            robot_id: 机器人 ID
            params: 参数字典
            
        Returns:
            是否成功
        """
        # 查找机器人所在的房间
        for room_id, strategy_engine in self.strategy_engines.items():
            if robot_id in strategy_engine.robots:
                return strategy_engine.update_robot_params(robot_id, params)
        
        return False
    
    # ==================== 房间管理 ====================
    
    async def destroy_room(self, room_id: str) -> bool:
        """
        销毁房间
        
        Args:
            room_id: 房间 ID
            
        Returns:
            是否成功
        """
        # 从数据库删除
        success = await self.db.delete_room(room_id)
        
        if success:
            # 清理内存中的引擎
            self.price_engines.pop(room_id, None)
            self.trade_managers.pop(room_id, None)
            self.step_controllers.pop(room_id, None)
            self.strategy_engines.pop(room_id, None)
        
        return success
    
    async def kick_user(
        self,
        room_id: str,
        user_id: str,
        user_connections: Dict
    ) -> bool:
        """
        踢出用户
        
        Args:
            room_id: 房间 ID
            user_id: 用户 ID
            user_connections: {user_id: websocket} 映射
            
        Returns:
            是否成功
        """
        # 从数据库移除
        await self.db.remove_user_from_room(room_id, user_id)
        
        # 关闭 WebSocket 连接
        if user_id in user_connections:
            try:
                await user_connections[user_id].close()
            except Exception:
                pass
        
        # 从步进控制器移除
        if room_id in self.step_controllers:
            self.step_controllers[room_id].remove_participant(room_id, user_id)
        
        return True
    
    # ==================== 房间状态控制 ====================
    
    async def admin_step_forward(self, room_id: str) -> bool:
        """
        管理员触发步进
        
        Args:
            room_id: 房间 ID
            
        Returns:
            是否成功
        """
        if room_id not in self.step_controllers:
            return False
        
        step_controller = self.step_controllers[room_id]
        await step_controller.start_step(room_id)
        
        return True
    
    async def admin_fast_forward(
        self,
        room_id: str,
        speed: float = 1.0,
        start: bool = True
    ) -> bool:
        """
        管理员控制快进
        
        Args:
            room_id: 房间 ID
            speed: 快进速度（步/秒）
            start: True 开始，False 停止
            
        Returns:
            是否成功
        """
        if room_id not in self.step_controllers:
            return False
        
        step_controller = self.step_controllers[room_id]
        
        if start:
            # 设置速度
            room_context = step_controller.get_room(room_id)
            if room_context:
                room_context.step_config.fast_forward_speed = speed
            return await step_controller.start_fast_forward(room_id)
        else:
            return await step_controller.stop_fast_forward(room_id)
    
    async def admin_pause(self, room_id: str) -> bool:
        """暂停房间"""
        if room_id not in self.step_controllers:
            return False
        
        return await self.step_controllers[room_id].pause_room(room_id)
    
    async def admin_resume(self, room_id: str) -> bool:
        """恢复房间"""
        if room_id not in self.step_controllers:
            return False
        
        return await self.step_controllers[room_id].resume_room(room_id)
    
    # ==================== 获取房间完整状态 ====================
    
    def get_room_full_status(self, room_id: str, prices: Dict[str, float]) -> Optional[Dict]:
        """
        获取房间完整状态
        
        Args:
            room_id: 房间 ID
            prices: 当前价格字典
            
        Returns:
            房间状态字典
        """
        if room_id not in self.step_controllers:
            return None
        
        step_controller = self.step_controllers[room_id]
        room_status = step_controller.get_room_status(room_id)
        
        if not room_status:
            return None
        
        # 获取机器人摘要
        robot_summaries = []
        if room_id in self.strategy_engines:
            robot_summaries = self.strategy_engines[room_id].get_all_robot_summaries(
                room_id, prices
            )
        
        # 获取股票信息
        stocks_info = []
        if room_id in self.price_engines:
            price_engine = self.price_engines[room_id]
            for code, state in price_engine.stocks.items():
                stocks_info.append({
                    "code": code,
                    "current_price": state.current_price,
                    "volatility": state.config.volatility,
                    "drift": state.config.drift,
                    "model": state.config.model.value
                })
        
        return {
            **room_status,
            "stocks": stocks_info,
            "robots": robot_summaries
        }
    
    # ==================== 股票管理 CRUD ====================
    
    async def create_stock(
        self,
        code: str,
        name: str,
        initial_price: float,
        issued_shares: int,
        description: str = ""
    ) -> Optional[Dict]:
        """
        创建股票
        
        Args:
            code: 股票代码
            name: 股票名称
            initial_price: 初始价格
            issued_shares: 发行数量
            description: 描述
            
        Returns:
            股票信息字典，失败返回 None
        """
        stock_id = await self.db.create_stock(code, name, initial_price, issued_shares, description)
        
        if not stock_id:
            return None
        
        return {
            "id": stock_id,
            "code": code,
            "name": name,
            "initial_price": initial_price,
            "issued_shares": issued_shares,
            "description": description
        }
    
    async def update_stock(
        self,
        stock_id: str,
        code: Optional[str] = None,
        name: Optional[str] = None,
        initial_price: Optional[float] = None,
        issued_shares: Optional[int] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        更新股票信息
        
        Args:
            stock_id: 股票 ID
            code: 新代码（可选）
            name: 新名称（可选）
            initial_price: 新初始价格（可选）
            issued_shares: 新发行数量（可选）
            description: 新描述（可选）
            
        Returns:
            是否成功
        """
        return await self.db.update_stock(stock_id, code, name, initial_price, issued_shares, description)
    
    async def delete_stock(self, stock_id: str) -> bool:
        """
        删除股票
        
        Args:
            stock_id: 股票 ID
            
        Returns:
            是否成功
        """
        return await self.db.delete_stock(stock_id)
    
    async def list_stocks(self) -> List[Dict[str, Any]]:
        """
        列出所有股票
        
        Returns:
            股票列表
        """
        return await self.db.list_stocks()
    
    async def add_stock_to_room(
        self,
        room_id: str,
        stock_code: str,
        current_price: float
    ) -> bool:
        """
        添加股票到房间
        
        Args:
            room_id: 房间 ID
            stock_code: 股票代码
            current_price: 当前价格
            
        Returns:
            是否成功
        """
        # 获取股票信息
        stock = await self.db.get_stock_by_code(stock_code)
        if not stock:
            return False
        
        stock_id = stock["id"]
        
        # 添加到数据库
        success = await self.db.add_stock_to_room(room_id, stock_id, current_price)
        if not success:
            return False
        
        # 同步到价格引擎
        if room_id in self.price_engines:
            price_engine = self.price_engines[room_id]
            price_engine.add_stock(stock_code, stock["name"], current_price)
        
        # 同步到交易管理器
        if room_id in self.trade_managers:
            trade_manager = self.trade_managers[room_id]
            trade_manager.set_stock_price(stock_code, current_price)
        
        return True
    
    async def remove_stock_from_room(
        self,
        room_id: str,
        stock_code: str
    ) -> bool:
        """
        从房间移除股票
        
        Args:
            room_id: 房间 ID
            stock_code: 股票代码
            
        Returns:
            是否成功
        """
        # 获取股票信息
        stock = await self.db.get_stock_by_code(stock_code)
        if not stock:
            return False
        
        stock_id = stock["id"]
        
        # 从数据库移除
        success = await self.db.remove_stock_from_room(room_id, stock_id)
        if not success:
            return False
        
        # 从价格引擎移除
        if room_id in self.price_engines:
            price_engine = self.price_engines[room_id]
            price_engine.remove_stock(stock_code)
        
        # 从交易管理器移除
        if room_id in self.trade_managers:
            trade_manager = self.trade_managers[room_id]
            trade_manager.remove_stock(stock_code)
        
        return True
    
    async def list_room_stocks(self, room_id: str) -> List[Dict[str, Any]]:
        """
        列出房间内的所有股票
        
        Args:
            room_id: 房间 ID
            
        Returns:
            股票列表
        """
        return await self.db.list_room_stocks(room_id)
