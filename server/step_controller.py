"""
步进控制器 - Step Controller

功能：
- 管理房间的步进流程
- 协调真人用户的决策期
- 触发价格生成和订单撮合
- 广播状态更新
"""

from typing import Dict, List, Optional, Set, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


class StepMode(Enum):
    """步进模式"""
    SECOND = "second"     # 秒级（超短线）
    HOUR = "hour"         # 小时级（较短线）
    DAY = "day"           # 天级（短线）
    MONTH = "month"       # 月级（中线）


class RoomState(Enum):
    """房间状态"""
    IDLE = "idle"               # 空闲
    DECISION = "decision"       # 决策期（等待用户操作）
    PROCESSING = "processing"   # 处理中（计算价格、撮合订单）
    FAST_FORWARD = "fast_forward"  # 快进中
    PAUSED = "paused"          # 暂停


@dataclass
class StepConfig:
    """步进配置"""
    mode: StepMode = StepMode.DAY
    decision_timeout: float = 30.0  # 决策超时时间（秒）
    fast_forward_speed: float = 1.0  # 快进速度（步/秒）


@dataclass
class RoomContext:
    """房间上下文"""
    room_id: str
    step_config: StepConfig
    state: RoomState = RoomState.IDLE
    current_step: int = 0
    virtual_time: float = 0.0  # 虚拟时间戳
    participants: Set[str] = field(default_factory=set)  # 参与者ID集合
    ready_users: Set[str] = field(default_factory=set)   # 已准备的用户ID集合
    
    def is_all_ready(self) -> bool:
        """所有真人用户是否已准备"""
        return self.participants.issubset(self.ready_users)
        
    def reset_ready(self):
        """重置准备状态"""
        self.ready_users.clear()


class StepController:
    """步进控制器"""
    
    def __init__(self):
        """初始化步进控制器"""
        self.rooms: Dict[str, RoomContext] = {}
        self.callbacks: Dict[str, Callable] = {}
        
    def create_room(
        self,
        room_id: str,
        step_config: Optional[StepConfig] = None
    ) -> RoomContext:
        """
        创建房间
        
        Args:
            room_id: 房间ID
            step_config: 步进配置（可选）
            
        Returns:
            RoomContext 对象
        """
        if step_config is None:
            step_config = StepConfig()
            
        context = RoomContext(
            room_id=room_id,
            step_config=step_config
        )
        
        self.rooms[room_id] = context
        return context
        
    def get_room(self, room_id: str) -> Optional[RoomContext]:
        """
        获取房间上下文
        
        Args:
            room_id: 房间ID
            
        Returns:
            RoomContext 对象或 None
        """
        return self.rooms.get(room_id)
        
    def delete_room(self, room_id: str) -> bool:
        """
        删除房间
        
        Args:
            room_id: 房间ID
            
        Returns:
            是否成功
        """
        if room_id in self.rooms:
            del self.rooms[room_id]
            return True
        return False
        
    def add_participant(self, room_id: str, user_id: str) -> bool:
        """
        添加参与者
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        room = self.rooms.get(room_id)
        if room:
            room.participants.add(user_id)
            return True
        return False
        
    def remove_participant(self, room_id: str, user_id: str) -> bool:
        """
        移除参与者
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        room = self.rooms.get(room_id)
        if room:
            room.participants.discard(user_id)
            room.ready_users.discard(user_id)
            return True
        return False
        
    def register_callback(self, event_name: str, callback: Callable):
        """
        注册回调函数
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        self.callbacks[event_name] = callback
        
    async def _trigger_callback(self, event_name: str, *args, **kwargs):
        """触发回调函数"""
        callback = self.callbacks.get(event_name)
        if callback:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
                
    async def start_step(self, room_id: str) -> bool:
        """
        开始步进（管理员触发）
        
        Args:
            room_id: 房间ID
            
        Returns:
            是否成功
        """
        room = self.rooms.get(room_id)
        if not room:
            return False
            
        # 检查房间状态
        if room.state not in [RoomState.IDLE, RoomState.PAUSED]:
            return False
            
        # 进入决策期
        room.state = RoomState.DECISION
        room.reset_ready()
        
        # 广播决策开始信号
        await self._trigger_callback(
            "decision_start",
            room_id=room_id,
            timeout=room.step_config.decision_timeout
        )
        
        # 如果没有真人参与者，直接跳到处理阶段
        if len(room.participants) == 0:
            await self._process_step(room_id)
            
        return True
        
    async def user_ready(self, room_id: str, user_id: str) -> bool:
        """
        用户准备完毕（用户点击"完成"或执行交易）
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        room = self.rooms.get(room_id)
        if not room:
            return False
            
        # 检查房间状态
        if room.state != RoomState.DECISION:
            return False
            
        # 标记用户为已准备
        room.ready_users.add(user_id)
        
        # 广播准备状态更新
        await self._trigger_callback(
            "ready_update",
            room_id=room_id,
            ready_count=len(room.ready_users),
            total_count=len(room.participants)
        )
        
        # 检查是否所有人都准备好了
        if room.is_all_ready():
            await self._process_step(room_id)
            
        return True
        
    async def _process_step(self, room_id: str):
        """
        处理步进（内部方法）
        
        Args:
            room_id: 房间ID
        """
        room = self.rooms.get(room_id)
        if not room:
            return
            
        # 记录处理前的状态（用于快进恢复）
        was_fast_forward = (room.state == RoomState.FAST_FORWARD)
            
        # 进入处理状态
        room.state = RoomState.PROCESSING
        
        # 广播处理开始信号
        await self._trigger_callback("processing_start", room_id=room_id)
        
        # 1. 生成新价格
        await self._trigger_callback("generate_prices", room_id=room_id)
        
        # 2. 撮合订单
        await self._trigger_callback("match_orders", room_id=room_id)
        
        # 3. 更新虚拟时间
        room.current_step += 1
        room.virtual_time = self._calculate_virtual_time(room)
        
        # 4. 重置就绪状态
        room.reset_ready()
        
        # 5. 广播新状态
        await self._trigger_callback(
            "step_completed",
            room_id=room_id,
            step=room.current_step,
            virtual_time=room.virtual_time
        )
        
        # 恢复状态：快进模式恢复为 FAST_FORWARD，否则回到 IDLE
        if was_fast_forward:
            room.state = RoomState.FAST_FORWARD
        else:
            room.state = RoomState.IDLE
        
    def _calculate_virtual_time(self, room: RoomContext) -> float:
        """
        计算虚拟时间
        
        Args:
            room: 房间上下文
            
        Returns:
            虚拟时间戳
        """
        mode = room.step_config.mode
        base_time = datetime(2024, 1, 1).timestamp()
        
        if mode == StepMode.SECOND:
            return base_time + room.current_step
        elif mode == StepMode.HOUR:
            return base_time + room.current_step * 3600
        elif mode == StepMode.DAY:
            return base_time + room.current_step * 86400
        elif mode == StepMode.MONTH:
            return base_time + room.current_step * 86400 * 30
        else:
            return base_time + room.current_step
            
    async def start_fast_forward(self, room_id: str) -> bool:
        """
        开始快进
        
        Args:
            room_id: 房间ID
            
        Returns:
            是否成功
        """
        room = self.rooms.get(room_id)
        if not room:
            return False
            
        # 检查房间状态
        if room.state != RoomState.IDLE:
            return False
            
        # 进入快进状态
        room.state = RoomState.FAST_FORWARD
        
        # 广播快进开始信号
        await self._trigger_callback(
            "fast_forward_start",
            room_id=room_id,
            speed=room.step_config.fast_forward_speed
        )
        
        # 启动快进循环
        asyncio.create_task(self._fast_forward_loop(room_id))
        
        return True
        
    async def stop_fast_forward(self, room_id: str) -> bool:
        """
        停止快进
        
        Args:
            room_id: 房间ID
            
        Returns:
            是否成功
        """
        room = self.rooms.get(room_id)
        if not room:
            return False
            
        # 检查房间状态
        if room.state != RoomState.FAST_FORWARD:
            return False
            
        # 返回空闲状态
        room.state = RoomState.IDLE
        
        # 广播快进停止信号
        await self._trigger_callback("fast_forward_stop", room_id=room_id)
        
        return True
        
    async def _fast_forward_loop(self, room_id: str):
        """
        快进循环（内部方法）
        
        Args:
            room_id: 房间ID
        """
        room = self.rooms.get(room_id)
        if not room:
            return
            
        speed = room.step_config.fast_forward_speed
        interval = 1.0 / speed  # 步进间隔
        
        while room.state == RoomState.FAST_FORWARD:
            # 执行一步
            await self._process_step(room_id)
            
            # 等待间隔
            await asyncio.sleep(interval)
            
            # 检查状态是否被改变
            room = self.rooms.get(room_id)
            if not room or room.state != RoomState.FAST_FORWARD:
                break
                
    async def pause_room(self, room_id: str) -> bool:
        """
        暂停房间
        
        Args:
            room_id: 房间ID
            
        Returns:
            是否成功
        """
        room = self.rooms.get(room_id)
        if not room:
            return False
            
        # 如果正在快进，先停止快进
        if room.state == RoomState.FAST_FORWARD:
            await self.stop_fast_forward(room_id)
            
        room.state = RoomState.PAUSED
        
        # 广播暂停信号
        await self._trigger_callback("room_paused", room_id=room_id)
        
        return True
        
    async def resume_room(self, room_id: str) -> bool:
        """
        恢复房间
        
        Args:
            room_id: 房间ID
            
        Returns:
            是否成功
        """
        room = self.rooms.get(room_id)
        if not room:
            return False
            
        if room.state != RoomState.PAUSED:
            return False
            
        room.state = RoomState.IDLE
        
        # 广播恢复信号
        await self._trigger_callback("room_resumed", room_id=room_id)
        
        return True
        
    def get_room_status(self, room_id: str) -> Optional[Dict]:
        """
        获取房间状态
        
        Args:
            room_id: 房间ID
            
        Returns:
            房间状态字典
        """
        room = self.rooms.get(room_id)
        if not room:
            return None
            
        return {
            "room_id": room.room_id,
            "state": room.state.value,
            "step_mode": room.step_config.mode.value,
            "current_step": room.current_step,
            "virtual_time": room.virtual_time,
            "participants_count": len(room.participants),
            "ready_count": len(room.ready_users),
            "is_all_ready": room.is_all_ready()
        }
        
    def get_all_rooms_status(self) -> List[Dict]:
        """
        获取所有房间状态
        
        Returns:
            房间状态列表
        """
        return [
            self.get_room_status(room_id)
            for room_id in self.rooms.keys()
        ]
