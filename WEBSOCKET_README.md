# WebSocket 异步通信协议与步进控制器

## 概述

本模块实现了实时互动的"服务端-客户端"通信机制，用于管理交易模拟的步进控制。

## 架构设计

### 核心组件

1. **StepController (步进控制器)**
   - 管理交易模拟的步进状态
   - 执行价格更新和机器人策略
   - 处理订单队列
   - 管理真人账户的完成状态

2. **WebSocketServer (WebSocket 服务器)**
   - 处理客户端连接和消息路由
   - 广播状态更新
   - 管理管理员权限
   - 实现快进模式

3. **TradingClient (交易客户端)**
   - 连接到服务器
   - 提交订单
   - 接收状态更新

4. **AdminClient (管理员客户端)**
   - 继承交易客户端功能
   - 强制推进步进
   - 启动/停止快进模式

## WebSocket 协议

### 消息类型

#### 客户端 → 服务器

- **AUTH**: 认证消息
  ```json
  {
    "type": "AUTH",
    "user_id": 1
  }
  ```

- **CLIENT_SUBMIT**: 提交订单
  ```json
  {
    "type": "CLIENT_SUBMIT",
    "order": {
      "stock_code": "AAPL",
      "action": "buy",
      "quantity": 100
    }
  }
  ```

- **CLIENT_READY**: 标记操作完成
  ```json
  {
    "type": "CLIENT_READY"
  }
  ```

- **ADMIN_FORCE_NEXT**: 管理员强制下一步
  ```json
  {
    "type": "ADMIN_FORCE_NEXT"
  }
  ```

- **FAST_FORWARD_START**: 启动快进模式
  ```json
  {
    "type": "FAST_FORWARD_START",
    "steps": 10
  }
  ```

- **FAST_FORWARD_STOP**: 停止快进模式
  ```json
  {
    "type": "FAST_FORWARD_STOP"
  }
  ```

- **HEARTBEAT**: 心跳
  ```json
  {
    "type": "HEARTBEAT"
  }
  ```

#### 服务器 → 客户端

- **STEP_INIT**: 广播初始状态
  ```json
  {
    "type": "STEP_INIT",
    "data": {
      "step": 0,
      "timestamp": "2026-03-11 01:00:00",
      "prices": {"AAPL": 150.0, ...},
      "accounts": [...],
      "is_waiting": false,
      "is_fast_forward": false
    }
  }
  ```

- **STEP_WAIT**: 服务器等待状态
  ```json
  {
    "type": "STEP_WAIT",
    "message": "等待所有真人账户完成操作..."
  }
  ```

- **STEP_UPDATE**: 步进更新
  ```json
  {
    "type": "STEP_UPDATE",
    "data": {...},
    "bot_results": {
      "2": {
        "signal": "buy",
        "quantity": 50,
        "result": "success"
      }
    }
  }
  ```

- **USER_READY**: 用户完成通知
  ```json
  {
    "type": "USER_READY",
    "user_id": 1,
    "ready_count": 1,
    "total_count": 2
  }
  ```

- **ORDER_RECEIVED**: 订单接收确认
  ```json
  {
    "type": "ORDER_RECEIVED",
    "message": "订单已接收"
  }
  ```

- **ORDER_EXECUTED**: 订单执行结果
  ```json
  {
    "type": "ORDER_EXECUTED",
    "success": true,
    "message": "订单执行成功",
    "order": {...}
  }
  ```

- **ERROR**: 错误消息
  ```json
  {
    "type": "ERROR",
    "message": "错误描述"
  }
  ```

## 使用指南

### 1. 启动服务器

```bash
# 基本启动
python websocket_server.py

# 自定义配置
python websocket_server.py --host 0.0.0.0 --port 8765 --db sqlite:///stonk.db
```

服务器启动后会：
- 监听 WebSocket 连接
- 发送心跳包保持连接
- 广播初始状态给所有客户端

### 2. 连接客户端

#### 交互式客户端

```bash
python websocket_client_example.py
```

可用命令：
- `buy <股票代码> <数量>` - 买入
- `sell <股票代码> <数量>` - 卖出
- `ready` - 标记完成操作
- `force` - (管理员) 强制下一步
- `fast <步数>` - (管理员) 快进模式
- `stop` - (管理员) 停止快进
- `quit` - 退出

#### 编程方式

```python
import asyncio
from websocket_client_example import TradingClient

async def main():
    # 创建客户端
    client = TradingClient(user_id=1)
    
    # 连接服务器
    await client.connect()
    
    # 创建监听任务
    listen_task = asyncio.create_task(client.listen())
    
    # 提交订单
    await client.submit_order("AAPL", "buy", 100)
    
    # 标记完成
    await client.mark_ready()
    
    # 等待一段时间
    await asyncio.sleep(10)
    
    # 断开连接
    listen_task.cancel()
    await client.disconnect()

asyncio.run(main())
```

### 3. 管理员操作

```python
from websocket_client_example import AdminClient

async def admin_demo():
    admin = AdminClient(user_id=999)
    await admin.connect()
    
    listen_task = asyncio.create_task(admin.listen())
    
    # 强制下一步
    await admin.force_next_step()
    
    # 快进10步
    await admin.start_fast_forward(steps=10)
    
    # 停止快进
    await admin.stop_fast_forward()
    
    listen_task.cancel()
    await admin.disconnect()
```

## 工作流程

### 正常步进流程

1. **初始化**: 服务器广播 STEP_INIT，所有客户端收到当前状态
2. **等待**: 服务器进入 STEP_WAIT 状态
3. **交易**: 真人账户提交订单 (CLIENT_SUBMIT)
4. **完成**: 真人账户标记完成 (CLIENT_READY)
5. **推进**: 当所有真人账户完成后，自动执行步进
6. **更新**: 服务器广播 STEP_UPDATE，包含新价格和账户信息
7. **循环**: 回到步骤 2

### 管理员强制推进

管理员可以随时使用 ADMIN_FORCE_NEXT 强制推进到下一步，即使部分真人账户未完成操作。

### 快进模式

1. 管理员启动快进模式 (FAST_FORWARD_START)
2. 真人账户自动设为"托管状态"
3. 服务器循环执行指定步数
4. 每步仅执行机器人策略，跳过等待
5. 完成后自动停止，或管理员手动停止 (FAST_FORWARD_STOP)

## 测试

### 基础测试

```bash
# 测试步进控制器
python test_websocket.py
```

### 网络测试

```bash
# 终端1: 启动服务器
python websocket_server.py

# 终端2: 运行网络测试
python test_websocket.py --network
```

测试内容：
- ✓ 步进控制器基本功能
- ✓ 单客户端连接
- ✓ 多客户端同步
- ✓ 管理员控制
- ✓ 快进模式

## 配置说明

### 服务器配置

```python
# websocket_server.py

# 数据库配置
DB_URL = "sqlite:///stonk.db"

# 股票代码
STOCK_CODES = ["AAPL", "GOOGL", "MSFT"]

# 服务器地址
HOST = "localhost"
PORT = 8765

# 心跳间隔（秒）
HEARTBEAT_INTERVAL = 30

# 快进模式步进间隔（秒）
FAST_FORWARD_INTERVAL = 0.5
```

### 客户端配置

```python
# 服务器URL
SERVER_URL = "ws://localhost:8765"

# 用户ID
USER_ID = 1

# 管理员ID (通常为999)
ADMIN_ID = 999
```

## 安全考虑

1. **认证**: 当前实现使用简单的用户ID认证，生产环境应使用更强的认证机制
2. **权限**: 管理员权限通过用户ID判断（ID >= 900），应改为基于角色的访问控制
3. **加密**: WebSocket 连接未加密，生产环境应使用 WSS (WebSocket Secure)
4. **验证**: 订单参数需要服务器端验证，防止恶意数据

## 故障排查

### 连接失败

- 确认服务器已启动
- 检查防火墙设置
- 验证主机和端口配置

### 步进不推进

- 检查是否所有真人账户已标记完成
- 查看服务器日志确认等待状态
- 管理员可使用强制推进

### 快进模式异常

- 确保只有管理员可以启动快进
- 检查步进间隔配置
- 使用停止命令终止快进

## 扩展功能

### 可以添加的功能

1. **持久化订单队列**: 将未执行订单保存到数据库
2. **历史回放**: 重放历史步进数据
3. **实时图表**: 集成 WebSocket 到前端图表
4. **通知系统**: 价格警报和订单完成通知
5. **性能监控**: 步进执行时间、订单处理速度等指标

## 技术栈

- **asyncio**: 异步 I/O 框架
- **websockets**: WebSocket 协议实现
- **SQLAlchemy**: ORM 数据库访问
- **JSON**: 消息序列化格式

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue。
