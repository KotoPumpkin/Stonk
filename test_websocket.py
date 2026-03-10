"""
WebSocket 通信协议测试脚本
测试步进控制器和异步通信功能
"""
import asyncio
import sys
from websocket_server import StepController, WebSocketServer
from websocket_client_example import TradingClient, AdminClient


async def test_step_controller():
    """
    测试步进控制器基本功能
    """
    print("=== 测试步进控制器 ===\n")
    
    # 配置
    DB_URL = "sqlite:///trading_system.db"
    STOCK_CODES = ["AAPL", "GOOGL", "MSFT"]
    
    # 创建步进控制器
    controller = StepController(DB_URL, STOCK_CODES)
    
    # 测试获取当前状态
    print("1. 获取初始状态")
    state = await controller.get_current_state()
    print(f"   当前步进: {state['step']}")
    print(f"   价格数量: {len(state['prices'])}")
    print(f"   账户数量: {len(state['accounts'])}")
    
    # 测试执行步进
    print("\n2. 执行步进")
    await controller.execute_step()
    
    state = await controller.get_current_state()
    print(f"   新步进: {state['step']}")
    
    # 测试订单验证
    print("\n3. 测试订单验证")
    valid_order = {
        "action": "buy",
        "stock_code": "AAPL",
        "quantity": 100
    }
    invalid_order = {
        "action": "invalid",
        "stock_code": "AAPL"
    }
    
    print(f"   有效订单验证: {controller.validate_order(valid_order)}")
    print(f"   无效订单验证: {controller.validate_order(invalid_order)}")
    
    print("\n✓ 步进控制器测试完成")


async def test_single_client():
    """
    测试单个客户端连接
    """
    print("\n=== 测试单客户端连接 ===\n")
    
    # 配置
    DB_URL = "sqlite:///trading_system.db"
    STOCK_CODES = ["AAPL", "GOOGL", "MSFT"]
    
    # 创建服务器
    controller = StepController(DB_URL, STOCK_CODES)
    server = WebSocketServer(controller, host="localhost", port=8765)
    
    # 启动服务器任务
    server_task = asyncio.create_task(server.start())
    
    # 等待服务器启动
    await asyncio.sleep(1)
    
    try:
        # 创建客户端（使用真人用户 user01）
        client = TradingClient(user_id=5, server_url="ws://localhost:8765")
        
        # 连接
        print("1. 连接客户端")
        await client.connect()
        
        # 创建监听任务
        listen_task = asyncio.create_task(client.listen())
        
        await asyncio.sleep(1)
        
        # 提交订单
        print("\n2. 提交订单")
        await client.submit_order("AAPL", "buy", 100)
        
        await asyncio.sleep(1)
        
        # 标记完成
        print("\n3. 标记完成")
        await client.mark_ready()
        
        # 等待步进执行
        await asyncio.sleep(2)
        
        # 断开连接
        listen_task.cancel()
        await client.disconnect()
        
        print("\n✓ 单客户端测试完成")
    
    finally:
        server_task.cancel()


async def test_multiple_clients():
    """
    测试多客户端同步
    """
    print("\n=== 测试多客户端同步 ===\n")
    
    # 配置
    DB_URL = "sqlite:///trading_system.db"
    STOCK_CODES = ["AAPL", "GOOGL", "MSFT"]
    
    # 创建服务器
    controller = StepController(DB_URL, STOCK_CODES)
    server = WebSocketServer(controller, host="localhost", port=8765)
    
    # 启动服务器任务
    server_task = asyncio.create_task(server.start())
    
    # 等待服务器启动
    await asyncio.sleep(1)
    
    try:
        # 创建多个客户端（使用真人用户 user01 和 user02）
        client1 = TradingClient(user_id=5, server_url="ws://localhost:8765")
        client2 = TradingClient(user_id=6, server_url="ws://localhost:8765")
        
        # 连接所有客户端
        print("1. 连接多个客户端")
        await client1.connect()
        await client2.connect()
        
        # 创建监听任务
        listen1 = asyncio.create_task(client1.listen())
        listen2 = asyncio.create_task(client2.listen())
        
        await asyncio.sleep(1)
        
        # 客户端1提交订单
        print("\n2. 客户端1提交订单")
        await client1.submit_order("AAPL", "buy", 100)
        await asyncio.sleep(0.5)
        
        # 客户端2提交订单
        print("\n3. 客户端2提交订单")
        await client2.submit_order("GOOGL", "buy", 50)
        await asyncio.sleep(0.5)
        
        # 客户端1标记完成
        print("\n4. 客户端1标记完成")
        await client1.mark_ready()
        await asyncio.sleep(1)
        
        # 客户端2标记完成（应触发步进）
        print("\n5. 客户端2标记完成")
        await client2.mark_ready()
        
        # 等待步进执行
        await asyncio.sleep(3)
        
        # 断开连接
        listen1.cancel()
        listen2.cancel()
        await client1.disconnect()
        await client2.disconnect()
        
        print("\n✓ 多客户端测试完成")
    
    finally:
        server_task.cancel()


async def test_admin_control():
    """
    测试管理员控制功能
    """
    print("\n=== 测试管理员控制 ===\n")
    
    # 配置
    DB_URL = "sqlite:///trading_system.db"
    STOCK_CODES = ["AAPL", "GOOGL", "MSFT"]
    
    # 创建服务器
    controller = StepController(DB_URL, STOCK_CODES)
    server = WebSocketServer(controller, host="localhost", port=8765)
    
    # 启动服务器任务
    server_task = asyncio.create_task(server.start())
    
    # 等待服务器启动
    await asyncio.sleep(1)
    
    try:
        # 创建普通客户端和管理员客户端
        client = TradingClient(user_id=5, server_url="ws://localhost:8765")
        admin = AdminClient(user_id=1, server_url="ws://localhost:8765")
        
        # 连接
        print("1. 连接客户端和管理员")
        await client.connect()
        await admin.connect()
        
        # 创建监听任务
        listen_client = asyncio.create_task(client.listen())
        listen_admin = asyncio.create_task(admin.listen())
        
        await asyncio.sleep(1)
        
        # 测试强制下一步
        print("\n2. 管理员强制下一步")
        await admin.force_next_step()
        
        await asyncio.sleep(2)
        
        # 测试快进模式
        print("\n3. 管理员启动快进模式")
        await admin.start_fast_forward(steps=3)
        
        await asyncio.sleep(5)
        
        # 断开连接
        listen_client.cancel()
        listen_admin.cancel()
        await client.disconnect()
        await admin.disconnect()
        
        print("\n✓ 管理员控制测试完成")
    
    finally:
        server_task.cancel()


async def test_fast_forward_mode():
    """
    测试快进模式
    """
    print("\n=== 测试快进模式 ===\n")
    
    # 配置
    DB_URL = "sqlite:///trading_system.db"
    STOCK_CODES = ["AAPL", "GOOGL", "MSFT"]
    
    # 创建服务器
    controller = StepController(DB_URL, STOCK_CODES)
    server = WebSocketServer(controller, host="localhost", port=8765)
    
    # 启动服务器任务
    server_task = asyncio.create_task(server.start())
    
    # 等待服务器启动
    await asyncio.sleep(1)
    
    try:
        # 创建管理员客户端
        admin = AdminClient(user_id=1, server_url="ws://localhost:8765")
        
        # 连接
        print("1. 连接管理员")
        await admin.connect()
        
        # 创建监听任务
        listen_admin = asyncio.create_task(admin.listen())
        
        await asyncio.sleep(1)
        
        # 记录初始步进
        initial_step = controller.current_step
        print(f"   初始步进: {initial_step}")
        
        # 启动快进模式
        print("\n2. 启动快进模式 (10步)")
        await admin.start_fast_forward(steps=10)
        
        # 等待快进完成
        await asyncio.sleep(6)
        
        # 检查步进增加
        final_step = controller.current_step
        print(f"   最终步进: {final_step}")
        print(f"   步进增加: {final_step - initial_step}")
        
        # 测试中途停止
        print("\n3. 测试中途停止快进")
        initial_step = controller.current_step
        fast_forward_task = asyncio.create_task(admin.start_fast_forward(steps=20))
        
        await asyncio.sleep(2)
        await admin.stop_fast_forward()
        
        await asyncio.sleep(1)
        final_step = controller.current_step
        print(f"   快进被中断，执行了 {final_step - initial_step} 步")
        
        # 断开连接
        listen_admin.cancel()
        await admin.disconnect()
        
        print("\n✓ 快进模式测试完成")
    
    finally:
        server_task.cancel()


async def run_all_tests():
    """
    运行所有测试
    """
    print("\n" + "="*60)
    print(" WebSocket 通信协议与步进控制器测试套件")
    print("="*60 + "\n")
    
    try:
        # 基础功能测试
        await test_step_controller()
        
        # 单客户端测试
        # await test_single_client()  # 需要运行服务器
        
        # 多客户端测试
        # await test_multiple_clients()  # 需要运行服务器
        
        # 管理员控制测试
        # await test_admin_control()  # 需要运行服务器
        
        # 快进模式测试
        # await test_fast_forward_mode()  # 需要运行服务器
        
        print("\n" + "="*60)
        print(" 所有测试完成!")
        print("="*60 + "\n")
        
        print("注意: 网络测试已跳过，需要先启动服务器后再测试")
        print("运行方法:")
        print("  1. 终端1: python websocket_server.py")
        print("  2. 终端2: python test_websocket.py --network")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def run_network_tests():
    """
    运行需要网络的测试（需要服务器运行）
    """
    print("\n" + "="*60)
    print(" 运行网络测试")
    print("="*60 + "\n")
    
    print("确保服务器已在另一个终端运行:")
    print("  python websocket_server.py\n")
    
    input("按回车继续...")
    
    try:
        await test_single_client()
        await test_multiple_clients()
        await test_admin_control()
        await test_fast_forward_mode()
        
        print("\n" + "="*60)
        print(" 网络测试完成!")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--network":
        asyncio.run(run_network_tests())
    else:
        asyncio.run(run_all_tests())
