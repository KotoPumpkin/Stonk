"""
WebSocket 客户端示例
演示如何连接到服务器并进行交互
"""
import asyncio
import json
import websockets
from datetime import datetime


class TradingClient:
    """
    交易客户端
    """
    
    def __init__(self, user_id: int, server_url: str = "ws://localhost:8765"):
        """
        初始化客户端
        :param user_id: 用户ID
        :param server_url: 服务器URL
        """
        self.user_id = user_id
        self.server_url = server_url
        self.websocket = None
        self.is_connected = False
    
    async def connect(self):
        """连接到服务器"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            
            # 发送认证消息
            auth_message = {
                "type": "AUTH",
                "user_id": self.user_id
            }
            await self.websocket.send(json.dumps(auth_message))
            
            self.is_connected = True
            print(f"用户 {self.user_id} 已连接到服务器")
            
            # 接收初始状态
            response = await self.websocket.recv()
            data = json.loads(response)
            print(f"\n初始状态:")
            self.print_state(data)
            
        except Exception as e:
            print(f"连接失败: {e}")
            self.is_connected = False
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            print(f"用户 {self.user_id} 已断开连接")
    
    async def submit_order(self, stock_code: str, action: str, quantity: float):
        """
        提交订单
        :param stock_code: 股票代码
        :param action: 'buy' 或 'sell'
        :param quantity: 数量
        """
        if not self.is_connected:
            print("未连接到服务器")
            return
        
        order = {
            "type": "CLIENT_SUBMIT",
            "order": {
                "stock_code": stock_code,
                "action": action,
                "quantity": quantity
            }
        }
        
        await self.websocket.send(json.dumps(order))
        print(f"\n已提交订单: {action} {quantity} {stock_code}")
    
    async def mark_ready(self):
        """标记操作完成"""
        if not self.is_connected:
            print("未连接到服务器")
            return
        
        message = {
            "type": "CLIENT_READY"
        }
        
        await self.websocket.send(json.dumps(message))
        print(f"\n用户 {self.user_id} 已标记完成操作")
    
    async def send_heartbeat(self):
        """发送心跳"""
        if not self.is_connected:
            return
        
        message = {
            "type": "HEARTBEAT"
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def listen(self):
        """监听服务器消息"""
        if not self.is_connected:
            print("未连接到服务器")
            return
        
        try:
            async for message in self.websocket:
                data = json.loads(message)
                self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("连接已关闭")
            self.is_connected = False
        except Exception as e:
            print(f"监听消息时出错: {e}")
    
    def handle_message(self, data: dict):
        """
        处理服务器消息
        :param data: 消息数据
        """
        msg_type = data.get('type')
        
        if msg_type == "STEP_INIT":
            print("\n=== 接收到初始状态 ===")
            self.print_state(data)
        
        elif msg_type == "STEP_WAIT":
            print(f"\n=== 服务器等待中 ===")
            print(data.get('message'))
        
        elif msg_type == "STEP_UPDATE":
            print("\n=== 步进更新 ===")
            self.print_state(data)
            if 'bot_results' in data:
                print("\n机器人交易结果:")
                for bot_id, result in data['bot_results'].items():
                    print(f"  Bot {bot_id}: {result['signal']}, 数量: {result['quantity']}, 结果: {result['result']}")
        
        elif msg_type == "USER_READY":
            print(f"\n用户 {data.get('user_id')} 已完成操作")
            print(f"进度: {data.get('ready_count')}/{data.get('total_count')}")
        
        elif msg_type == "ORDER_RECEIVED":
            print(f"\n订单已接收: {data.get('message')}")
        
        elif msg_type == "ORDER_EXECUTED":
            success = data.get('success')
            message = data.get('message')
            order = data.get('order')
            print(f"\n订单执行结果:")
            print(f"  成功: {success}")
            print(f"  消息: {message}")
            print(f"  订单: {order}")
        
        elif msg_type == "FAST_FORWARD_START":
            print(f"\n=== 快进模式启动 ===")
            print(f"步数: {data.get('steps')}")
        
        elif msg_type == "FAST_FORWARD_STOP":
            print(f"\n=== 快进模式停止 ===")
        
        elif msg_type == "ERROR":
            print(f"\n错误: {data.get('message')}")
        
        elif msg_type == "HEARTBEAT":
            pass  # 静默处理心跳
    
    def print_state(self, data: dict):
        """
        打印状态信息
        :param data: 状态数据
        """
        state = data.get('data', {})
        
        print(f"步进: {state.get('step')}")
        print(f"时间: {state.get('timestamp')}")
        print(f"等待中: {state.get('is_waiting')}")
        print(f"快进模式: {state.get('is_fast_forward')}")
        
        print("\n当前价格:")
        for stock, price in state.get('prices', {}).items():
            print(f"  {stock}: ${price:.2f}")
        
        print("\n账户信息:")
        for account in state.get('accounts', []):
            print(f"\n  用户: {account['username']} (ID: {account['user_id']}, 类型: {account['user_type']})")
            print(f"    现金: ${account['cash']:.2f}")
            print(f"    持仓市值: ${account['position_value']:.2f}")
            print(f"    总资产: ${account['total_asset']:.2f}")
            print(f"    未实现盈亏: ${account['unrealized_pnl']:.2f} ({account['total_pnl_rate']:.2%})")
            
            if account['positions']:
                print("    持仓:")
                for pos in account['positions']:
                    print(f"      {pos['stock_code']}: {pos['quantity']} 股")
                    print(f"        成本: ${pos['avg_cost']:.2f}, 市价: ${pos['current_price']:.2f}")
                    print(f"        市值: ${pos['market_value']:.2f}, 盈亏: ${pos['unrealized_pnl']:.2f} ({pos['pnl_rate']:.2%})")


class AdminClient(TradingClient):
    """
    管理员客户端
    增加管理员功能
    """
    
    async def force_next_step(self):
        """强制下一步"""
        if not self.is_connected:
            print("未连接到服务器")
            return
        
        message = {
            "type": "ADMIN_FORCE_NEXT"
        }
        
        await self.websocket.send(json.dumps(message))
        print("\n管理员已强制下一步")
    
    async def start_fast_forward(self, steps: int = 10):
        """
        开始快进模式
        :param steps: 快进步数
        """
        if not self.is_connected:
            print("未连接到服务器")
            return
        
        message = {
            "type": "FAST_FORWARD_START",
            "steps": steps
        }
        
        await self.websocket.send(json.dumps(message))
        print(f"\n管理员启动快进模式 ({steps} 步)")
    
    async def stop_fast_forward(self):
        """停止快进模式"""
        if not self.is_connected:
            print("未连接到服务器")
            return
        
        message = {
            "type": "FAST_FORWARD_STOP"
        }
        
        await self.websocket.send(json.dumps(message))
        print("\n管理员停止快进模式")


async def human_trader_example():
    """
    真人交易员示例
    """
    client = TradingClient(user_id=1)  # 假设用户ID为1
    
    await client.connect()
    
    # 创建监听任务
    listen_task = asyncio.create_task(client.listen())
    
    # 模拟交易操作
    await asyncio.sleep(2)
    
    # 提交买单
    await client.submit_order("AAPL", "buy", 100)
    await asyncio.sleep(1)
    
    # 标记完成
    await client.mark_ready()
    
    # 继续监听一段时间
    await asyncio.sleep(10)
    
    # 断开连接
    listen_task.cancel()
    await client.disconnect()


async def admin_example():
    """
    管理员示例
    """
    admin = AdminClient(user_id=999)  # 假设管理员ID为999
    
    await admin.connect()
    
    # 创建监听任务
    listen_task = asyncio.create_task(admin.listen())
    
    await asyncio.sleep(2)
    
    # 强制下一步
    await admin.force_next_step()
    
    await asyncio.sleep(5)
    
    # 启动快进模式
    await admin.start_fast_forward(steps=5)
    
    await asyncio.sleep(10)
    
    # 断开连接
    listen_task.cancel()
    await admin.disconnect()


async def interactive_client():
    """
    交互式客户端
    """
    print("=== 交互式交易客户端 ===\n")
    
    user_id = input("请输入用户ID: ")
    is_admin = input("是否为管理员? (y/n): ").lower() == 'y'
    
    if is_admin:
        client = AdminClient(user_id=int(user_id))
    else:
        client = TradingClient(user_id=int(user_id))
    
    await client.connect()
    
    # 创建监听任务
    listen_task = asyncio.create_task(client.listen())
    
    print("\n可用命令:")
    print("  buy <股票代码> <数量>  - 买入")
    print("  sell <股票代码> <数量> - 卖出")
    print("  ready                  - 标记完成操作")
    if is_admin:
        print("  force                  - 强制下一步")
        print("  fast <步数>            - 快进模式")
        print("  stop                   - 停止快进")
    print("  quit                   - 退出\n")
    
    try:
        while True:
            command = await asyncio.get_event_loop().run_in_executor(
                None, input, "> "
            )
            
            parts = command.strip().split()
            if not parts:
                continue
            
            cmd = parts[0].lower()
            
            if cmd == "buy" and len(parts) == 3:
                await client.submit_order(parts[1], "buy", float(parts[2]))
            
            elif cmd == "sell" and len(parts) == 3:
                await client.submit_order(parts[1], "sell", float(parts[2]))
            
            elif cmd == "ready":
                await client.mark_ready()
            
            elif cmd == "force" and is_admin:
                await client.force_next_step()
            
            elif cmd == "fast" and is_admin and len(parts) == 2:
                await client.start_fast_forward(int(parts[1]))
            
            elif cmd == "stop" and is_admin:
                await client.stop_fast_forward()
            
            elif cmd == "quit":
                break
            
            else:
                print("未知命令或参数错误")
    
    except KeyboardInterrupt:
        print("\n中断...")
    finally:
        listen_task.cancel()
        await client.disconnect()


if __name__ == "__main__":
    # 运行交互式客户端
    asyncio.run(interactive_client())
    
    # 或者运行示例
    # asyncio.run(human_trader_example())
    # asyncio.run(admin_example())
