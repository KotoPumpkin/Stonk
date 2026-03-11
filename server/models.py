"""
Stonk - 数据模型与数据库操作模块

使用 aiosqlite 实现异步数据库操作，支持用户、房间、股票、机器人等数据管理。
"""

import aiosqlite
import json
from typing import Optional, List, Dict, Any
import time
from shared.utils import hash_password, generate_salt, generate_id, generate_user_id, generate_room_id, generate_robot_id, generate_order_id
from shared.constants import INITIAL_CAPITAL, DB_PATH


class DatabaseManager:
    """数据库管理器 - 封装所有数据库操作"""
    
    def __init__(self, db_path: str = DB_PATH):
        """
        初始化数据库管理器。
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def initialize(self) -> None:
        """初始化数据库连接并创建表"""
        self.connection = await aiosqlite.connect(self.db_path)
        # 启用外键约束
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self.connection:
            await self.connection.close()
    
    async def _create_tables(self) -> None:
        """创建所有数据库表"""
        cursor = await self.connection.cursor()
        
        # Users 表 - 用户账户信息
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        
        # Rooms 表 - 房间配置
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Rooms (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                step_mode TEXT NOT NULL,
                status TEXT NOT NULL,
                initial_capital REAL NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                step_count INTEGER DEFAULT 0,
                current_timestamp REAL NOT NULL
            )
        """)
        
        # Stocks 表 - 股票基础数据
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Stocks (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                initial_price REAL NOT NULL,
                issued_shares INTEGER NOT NULL,
                description TEXT,
                created_at REAL NOT NULL
            )
        """)
        
        # RoomStocks 表 - 房间与股票的关联（每个房间可有独立的股票池）
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS RoomStocks (
                room_id TEXT NOT NULL,
                stock_id TEXT NOT NULL,
                current_price REAL NOT NULL,
                PRIMARY KEY (room_id, stock_id),
                FOREIGN KEY (room_id) REFERENCES Rooms(id) ON DELETE CASCADE,
                FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE CASCADE
            )
        """)
        
        # Robots 表 - 机器人账户
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Robots (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                name TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                initial_capital REAL NOT NULL,
                current_cash REAL NOT NULL,
                holdings TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY (room_id) REFERENCES Rooms(id) ON DELETE CASCADE
            )
        """)
        
        # TradeRecords 表 - 交易记录
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS TradeRecords (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                user_id TEXT,
                robot_id TEXT,
                stock_id TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp REAL NOT NULL,
                FOREIGN KEY (room_id) REFERENCES Rooms(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
                FOREIGN KEY (robot_id) REFERENCES Robots(id) ON DELETE CASCADE,
                FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE CASCADE
            )
        """)
        
        # Assets 表 - 资产快照
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Assets (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                user_id TEXT,
                robot_id TEXT,
                timestamp REAL NOT NULL,
                cash REAL NOT NULL,
                holdings TEXT NOT NULL DEFAULT '{}',
                total_value REAL NOT NULL,
                profit_loss REAL NOT NULL,
                FOREIGN KEY (room_id) REFERENCES Rooms(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
                FOREIGN KEY (robot_id) REFERENCES Robots(id) ON DELETE CASCADE
            )
        """)
        
        # News 表 - 新闻记录
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS News (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                affected_stocks TEXT DEFAULT '[]',
                published_at REAL NOT NULL,
                FOREIGN KEY (room_id) REFERENCES Rooms(id) ON DELETE CASCADE
            )
        """)
        
        # Reports 表 - 财报记录
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Reports (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                stock_id TEXT NOT NULL,
                pe_ratio REAL,
                roe REAL,
                net_income REAL,
                revenue REAL,
                manager_weight REAL DEFAULT 1.0,
                published_at REAL NOT NULL,
                FOREIGN KEY (room_id) REFERENCES Rooms(id) ON DELETE CASCADE,
                FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE CASCADE
            )
        """)
        
        # RoomUsers 表 - 房间与用户的关联（用户在房间中的状态）
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS RoomUsers (
                room_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                initial_capital REAL NOT NULL,
                current_cash REAL NOT NULL,
                holdings TEXT NOT NULL DEFAULT '{}',
                joined_at REAL NOT NULL,
                PRIMARY KEY (room_id, user_id),
                FOREIGN KEY (room_id) REFERENCES Rooms(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
            )
        """)
        
        # Sessions 表 - 会话管理
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
            )
        """)
        
        await self.connection.commit()
    
    # ==================== User Operations ====================
    
    async def register_user(self, username: str, password: str) -> Optional[str]:
        """
        注册新用户。
        
        Args:
            username: 用户名
            password: 明文密码
        
        Returns:
            用户 ID，如果注册失败则返回 None
        """
        try:
            cursor = await self.connection.cursor()
            user_id = generate_user_id()
            salt = generate_salt()
            password_hash = hash_password(password, salt)
            now = time.time()
            
            await cursor.execute("""
                INSERT INTO Users (id, username, password_hash, salt, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, password_hash, salt, now, now))
            
            await self.connection.commit()
            return user_id
        except Exception as e:
            print(f"Error registering user: {e}")
            return None
    
    async def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        验证用户账户。
        
        Args:
            username: 用户名
            password: 明文密码
        
        Returns:
            用户信息字典（包含 id、username），如果验证失败则返回 None
        """
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT id, username, password_hash, salt FROM Users WHERE username = ?
            """, (username,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            user_id, username, password_hash, salt = row
            from shared.utils import verify_password
            if verify_password(password, salt, password_hash):
                return {"id": user_id, "username": username}
            else:
                return None
        except Exception as e:
            print(f"Error verifying user: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT id, username, created_at FROM Users WHERE id = ?
            """, (user_id,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            user_id, username, created_at = row
            return {"id": user_id, "username": username, "created_at": created_at}
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    # ==================== Room Operations ====================
    
    async def create_room(self, name: str, step_mode: str, initial_capital: float) -> Optional[str]:
        """
        创建房间。
        
        Args:
            name: 房间名称
            step_mode: 步进模式 (second/hour/day/month)
            initial_capital: 初始资金
        
        Returns:
            房间 ID，如果创建失败则返回 None
        """
        try:
            cursor = await self.connection.cursor()
            room_id = generate_room_id()
            now = time.time()
            
            await cursor.execute("""
                INSERT INTO Rooms (id, name, step_mode, status, initial_capital, created_at, updated_at, current_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (room_id, name, step_mode, "running", initial_capital, now, now, now))
            
            await self.connection.commit()
            return room_id
        except Exception as e:
            print(f"Error creating room: {e}")
            return None
    
    async def get_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取房间信息"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT id, name, step_mode, status, initial_capital, created_at, step_count, current_timestamp
                FROM Rooms WHERE id = ?
            """, (room_id,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            room_id, name, step_mode, status, initial_capital, created_at, step_count, current_timestamp = row
            return {
                "id": room_id,
                "name": name,
                "step_mode": step_mode,
                "status": status,
                "initial_capital": initial_capital,
                "created_at": created_at,
                "step_count": step_count,
                "current_timestamp": current_timestamp
            }
        except Exception as e:
            print(f"Error getting room: {e}")
            return None
    
    async def list_rooms(self) -> List[Dict[str, Any]]:
        """列出所有房间"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT id, name, step_mode, status, initial_capital, created_at, step_count
                FROM Rooms ORDER BY created_at DESC
            """)
            
            rows = await cursor.fetchall()
            rooms = []
            for row in rows:
                room_id, name, step_mode, status, initial_capital, created_at, step_count = row
                rooms.append({
                    "id": room_id,
                    "name": name,
                    "step_mode": step_mode,
                    "status": status,
                    "initial_capital": initial_capital,
                    "created_at": created_at,
                    "step_count": step_count
                })
            return rooms
        except Exception as e:
            print(f"Error listing rooms: {e}")
            return []
    
    async def delete_room(self, room_id: str) -> bool:
        """删除房间"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("DELETE FROM Rooms WHERE id = ?", (room_id,))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error deleting room: {e}")
            return False
    
    # ==================== Stock Operations ====================
    
    async def create_stock(self, code: str, name: str, initial_price: float, issued_shares: int, 
                          description: str = "") -> Optional[str]:
        """创建股票"""
        try:
            cursor = await self.connection.cursor()
            stock_id = generate_order_id()
            now = time.time()
            
            await cursor.execute("""
                INSERT INTO Stocks (id, code, name, initial_price, issued_shares, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (stock_id, code, name, initial_price, issued_shares, description, now))
            
            await self.connection.commit()
            return stock_id
        except Exception as e:
            print(f"Error creating stock: {e}")
            return None
    
    async def get_stock(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """获取股票信息"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT id, code, name, initial_price, issued_shares, description FROM Stocks WHERE id = ?
            """, (stock_id,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            stock_id, code, name, initial_price, issued_shares, description = row
            return {
                "id": stock_id,
                "code": code,
                "name": name,
                "initial_price": initial_price,
                "issued_shares": issued_shares,
                "description": description
            }
        except Exception as e:
            print(f"Error getting stock: {e}")
            return None
    
    async def list_stocks(self) -> List[Dict[str, Any]]:
        """列出所有股票"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT id, code, name, initial_price, issued_shares FROM Stocks
            """)
            
            rows = await cursor.fetchall()
            stocks = []
            for row in rows:
                stock_id, code, name, initial_price, issued_shares = row
                stocks.append({
                    "id": stock_id,
                    "code": code,
                    "name": name,
                    "initial_price": initial_price,
                    "issued_shares": issued_shares
                })
            return stocks
        except Exception as e:
            print(f"Error listing stocks: {e}")
            return []
    
    # ==================== Robot Operations ====================
    
    async def create_robot(self, room_id: str, name: str, strategy_type: str, 
                          initial_capital: float) -> Optional[str]:
        """创建机器人"""
        try:
            cursor = await self.connection.cursor()
            robot_id = generate_robot_id()
            now = time.time()
            
            await cursor.execute("""
                INSERT INTO Robots (id, room_id, name, strategy_type, initial_capital, current_cash, holdings, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (robot_id, room_id, name, strategy_type, initial_capital, initial_capital, "{}", now, now))
            
            await self.connection.commit()
            return robot_id
        except Exception as e:
            print(f"Error creating robot: {e}")
            return None
    
    async def get_robot(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """获取机器人信息"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT id, room_id, name, strategy_type, initial_capital, current_cash, holdings
                FROM Robots WHERE id = ?
            """, (robot_id,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            robot_id, room_id, name, strategy_type, initial_capital, current_cash, holdings = row
            return {
                "id": robot_id,
                "room_id": room_id,
                "name": name,
                "strategy_type": strategy_type,
                "initial_capital": initial_capital,
                "current_cash": current_cash,
                "holdings": json.loads(holdings)
            }
        except Exception as e:
            print(f"Error getting robot: {e}")
            return None
    
    async def list_room_robots(self, room_id: str) -> List[Dict[str, Any]]:
        """列出房间内的所有机器人"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT id, name, strategy_type, initial_capital, current_cash, holdings
                FROM Robots WHERE room_id = ?
            """, (room_id,))
            
            rows = await cursor.fetchall()
            robots = []
            for row in rows:
                robot_id, name, strategy_type, initial_capital, current_cash, holdings = row
                robots.append({
                    "id": robot_id,
                    "name": name,
                    "strategy_type": strategy_type,
                    "initial_capital": initial_capital,
                    "current_cash": current_cash,
                    "holdings": json.loads(holdings)
                })
            return robots
        except Exception as e:
            print(f"Error listing room robots: {e}")
            return []
    
    # ==================== Trade Record Operations ====================
    
    async def record_trade(self, room_id: str, stock_id: str, action: str, quantity: int, price: float,
                          user_id: Optional[str] = None, robot_id: Optional[str] = None) -> Optional[str]:
        """记录交易"""
        try:
            cursor = await self.connection.cursor()
            trade_id = generate_order_id()
            timestamp = time.time()
            
            await cursor.execute("""
                INSERT INTO TradeRecords (id, room_id, user_id, robot_id, stock_id, action, quantity, price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (trade_id, room_id, user_id, robot_id, stock_id, action, quantity, price, timestamp))
            
            await self.connection.commit()
            return trade_id
        except Exception as e:
            print(f"Error recording trade: {e}")
            return None
    
    async def get_room_trades(self, room_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取房间的交易记录"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT id, user_id, robot_id, stock_id, action, quantity, price, timestamp
                FROM TradeRecords WHERE room_id = ? ORDER BY timestamp DESC LIMIT ?
            """, (room_id, limit))
            
            rows = await cursor.fetchall()
            trades = []
            for row in rows:
                trade_id, user_id, robot_id, stock_id, action, quantity, price, timestamp = row
                trades.append({
                    "id": trade_id,
                    "user_id": user_id,
                    "robot_id": robot_id,
                    "stock_id": stock_id,
                    "action": action,
                    "quantity": quantity,
                    "price": price,
                    "timestamp": timestamp
                })
            return trades
        except Exception as e:
            print(f"Error getting room trades: {e}")
            return []
    
    # ==================== Session Operations ====================
    
    async def create_session(self, user_id: str, token: str, expires_in: int = 86400) -> bool:
        """创建会话"""
        try:
            cursor = await self.connection.cursor()
            now = time.time()
            expires_at = now + expires_in
            
            await cursor.execute("""
                INSERT INTO Sessions (token, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
            """, (token, user_id, now, expires_at))
            
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
    
    async def verify_session(self, token: str) -> Optional[str]:
        """验证会话，返回用户 ID"""
        try:
            cursor = await self.connection.cursor()
            now = time.time()
            
            await cursor.execute("""
                SELECT user_id FROM Sessions WHERE token = ? AND expires_at > ?
            """, (token, now))
            
            row = await cursor.fetchone()
            if row:
                return row[0]
            else:
                return None
        except Exception as e:
            print(f"Error verifying session: {e}")
            return None
    
    async def delete_session(self, token: str) -> bool:
        """删除会话"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("DELETE FROM Sessions WHERE token = ?", (token,))
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    # ==================== Room User Operations ====================
    
    async def add_user_to_room(self, room_id: str, user_id: str, initial_capital: float) -> bool:
        """将用户添加到房间"""
        try:
            cursor = await self.connection.cursor()
            now = time.time()
            
            await cursor.execute("""
                INSERT INTO RoomUsers (room_id, user_id, initial_capital, current_cash, joined_at)
                VALUES (?, ?, ?, ?, ?)
            """, (room_id, user_id, initial_capital, initial_capital, now))
            
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error adding user to room: {e}")
            return False
    
    async def remove_user_from_room(self, room_id: str, user_id: str) -> bool:
        """从房间移除用户"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                DELETE FROM RoomUsers WHERE room_id = ? AND user_id = ?
            """, (room_id, user_id))
            
            await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error removing user from room: {e}")
            return False
    
    async def get_room_users(self, room_id: str) -> List[Dict[str, Any]]:
        """获取房间内的用户"""
        try:
            cursor = await self.connection.cursor()
            await cursor.execute("""
                SELECT user_id, initial_capital, current_cash, holdings, joined_at
                FROM RoomUsers WHERE room_id = ?
            """, (room_id,))
            
            rows = await cursor.fetchall()
            users = []
            for row in rows:
                user_id, initial_capital, current_cash, holdings, joined_at = row
                users.append({
                    "user_id": user_id,
                    "initial_capital": initial_capital,
                    "current_cash": current_cash,
                    "holdings": json.loads(holdings),
                    "joined_at": joined_at
                })
            return users
        except Exception as e:
            print(f"Error getting room users: {e}")
            return []
