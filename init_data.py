"""
数据初始化脚本
预设管理员账户、机器人账户、股票清单
"""
from models import (
    init_database, get_session, User, Account, Stock, SystemState,
    UserType, RobotStrategy
)
from datetime import datetime


def init_system_data(db_path='trading_system.db'):
    """
    初始化系统数据
    包括：管理员、机器人账户、股票清单、系统状态
    """
    # 初始化数据库
    engine = init_database(db_path)
    session = get_session(engine)
    
    try:
        print("开始初始化系统数据...")
        
        # 1. 创建管理员账户
        print("\n创建管理员账户...")
        admin = User(
            username="admin",
            password="admin123",  # 实际应用应加密
            user_type=UserType.ADMIN
        )
        session.add(admin)
        session.flush()  # 获取 admin.id
        
        # 管理员账户（不参与交易，无需资金）
        admin_account = Account(
            user_id=admin.id,
            cash=0.0,
            initial_capital=0.0
        )
        session.add(admin_account)
        print(f"✓ 创建管理员账户: {admin.username}")
        
        # 2. 创建三类机器人账户
        print("\n创建机器人账户...")
        robot_configs = [
            {
                "username": "robot_retail",
                "password": "robot123",
                "strategy": RobotStrategy.RETAIL,
                "initial_capital": 100000.0,  # 10万初始资金
                "description": "散户游资策略"
            },
            {
                "username": "robot_institution",
                "password": "robot123",
                "strategy": RobotStrategy.INSTITUTION,
                "initial_capital": 500000.0,  # 50万初始资金
                "description": "正规机构策略"
            },
            {
                "username": "robot_short_seller",
                "password": "robot123",
                "strategy": RobotStrategy.SHORT_SELLER,
                "initial_capital": 300000.0,  # 30万初始资金
                "description": "做空组织策略"
            }
        ]
        
        for config in robot_configs:
            robot = User(
                username=config["username"],
                password=config["password"],
                user_type=UserType.ROBOT,
                strategy_type=config["strategy"]
            )
            session.add(robot)
            session.flush()
            
            robot_account = Account(
                user_id=robot.id,
                cash=config["initial_capital"],
                initial_capital=config["initial_capital"]
            )
            session.add(robot_account)
            print(f"✓ 创建机器人账户: {robot.username} ({config['description']}) - 初始资金: ¥{config['initial_capital']:,.2f}")
        
        # 3. 创建示例真人账户
        print("\n创建示例真人账户...")
        demo_users = [
            {
                "username": "user01",
                "password": "user123",
                "initial_capital": 50000.0
            },
            {
                "username": "user02",
                "password": "user123",
                "initial_capital": 50000.0
            }
        ]
        
        for config in demo_users:
            user = User(
                username=config["username"],
                password=config["password"],
                user_type=UserType.HUMAN
            )
            session.add(user)
            session.flush()
            
            user_account = Account(
                user_id=user.id,
                cash=config["initial_capital"],
                initial_capital=config["initial_capital"]
            )
            session.add(user_account)
            print(f"✓ 创建真人账户: {user.username} - 初始资金: ¥{config['initial_capital']:,.2f}")
        
        # 4. 创建股票清单
        print("\n创建股票清单...")
        stocks_config = [
            {
                "code": "SH600000",
                "name": "浦发银行",
                "initial_price": 10.50,
                "drift": 0.0001,  # 略微正向漂移
                "volatility": 0.15  # 较低波动率（稳健型）
            },
            {
                "code": "SH600519",
                "name": "贵州茅台",
                "initial_price": 1680.00,
                "drift": 0.0002,
                "volatility": 0.18
            },
            {
                "code": "SZ000001",
                "name": "平安银行",
                "initial_price": 15.30,
                "drift": 0.00005,
                "volatility": 0.20
            },
            {
                "code": "SZ000858",
                "name": "五粮液",
                "initial_price": 180.50,
                "drift": 0.00015,
                "volatility": 0.22
            },
            {
                "code": "SH601318",
                "name": "中国平安",
                "initial_price": 55.80,
                "drift": 0.0001,
                "volatility": 0.17
            },
            {
                "code": "SZ002594",
                "name": "比亚迪",
                "initial_price": 268.00,
                "drift": 0.0003,  # 较高漂移（成长型）
                "volatility": 0.30  # 较高波动率
            },
            {
                "code": "SH688981",
                "name": "中芯国际",
                "initial_price": 55.00,
                "drift": 0.00025,
                "volatility": 0.28
            },
            {
                "code": "SZ300750",
                "name": "宁德时代",
                "initial_price": 420.00,
                "drift": 0.0002,
                "volatility": 0.25
            },
            {
                "code": "SH601988",
                "name": "中国银行",
                "initial_price": 4.20,
                "drift": 0.00003,
                "volatility": 0.12  # 超低波动率
            },
            {
                "code": "SZ002475",
                "name": "立讯精密",
                "initial_price": 32.50,
                "drift": 0.00018,
                "volatility": 0.24
            }
        ]
        
        for config in stocks_config:
            stock = Stock(
                stock_code=config["code"],
                stock_name=config["name"],
                initial_price=config["initial_price"],
                drift=config["drift"],
                volatility=config["volatility"],
                is_active=True
            )
            session.add(stock)
            print(f"✓ 添加股票: {config['code']} - {config['name']} "
                  f"(初始价: ¥{config['initial_price']:.2f}, 波动率: {config['volatility']:.2%})")
        
        # 5. 初始化系统状态
        print("\n初始化系统状态...")
        system_state = SystemState(
            id=1,  # 确保只有一条系统状态记录
            current_time=datetime(2024, 1, 1, 9, 30, 0),  # 初始时间：2024年1月1日 9:30
            step_mode="day",  # 默认模式：天级步进
            step_count=0,
            is_fast_forward=False
        )
        session.add(system_state)
        print(f"✓ 系统状态初始化完成 (初始时间: {system_state.current_time}, 模式: {system_state.step_mode})")
        
        # 提交所有更改
        session.commit()
        print("\n" + "="*60)
        print("✓ 数据初始化完成！")
        print("="*60)
        print(f"\n数据库文件: {db_path}")
        print("\n账户汇总:")
        print("  - 1 个管理员账户 (admin/admin123)")
        print("  - 3 个机器人账户 (robot_retail, robot_institution, robot_short_seller)")
        print("  - 2 个示例真人账户 (user01, user02)")
        print(f"  - {len(stocks_config)} 只股票")
        print("\n系统已就绪，可以开始运行！")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        session.close()


def reset_database(db_path='trading_system.db'):
    """
    重置数据库（删除并重新创建）
    """
    import os
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"已删除旧数据库: {db_path}")
    
    return init_system_data(db_path)


if __name__ == "__main__":
    # 运行初始化
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        print("重置模式：将删除现有数据库并重新初始化")
        reset_database()
    else:
        print("初始化模式：如果数据库已存在将跳过初始化")
        print("使用 --reset 参数可强制重置数据库\n")
        init_system_data()
