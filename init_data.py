import os
import sys
from datetime import datetime
from sqlalchemy import inspect
from models import (
    Base, get_engine, get_session, 
    User, Account, Stock, SystemState, 
    UserType, RobotStrategy
)

def init_system_data(db_path='trading_system.db'):
    """
    初始化系统数据
    包括：同步表结构、创建管理员、机器人账户、股票清单、系统状态
    """
    # 1. 创建引擎并同步表结构
    engine = get_engine(db_path)
    print(f"正在为数据库 {db_path} 同步表结构...")
    
    # 核心修复：确保 Base 关联的所有模型都被同步到物理文件中
    Base.metadata.create_all(bind=engine)
    
    # 调试信息：列出数据库中所有的表名
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"当前数据库中的表: {', '.join(tables)}")
    
    if not tables:
        print("错误：表创建失败，请检查 models.py 中的类定义是否正确继承了 Base。")
        return False

    session = get_session(engine)
    
    try:
        # 检查是否已经初始化过（以管理员是否存在为准）
        if session.query(User).filter(User.user_type == UserType.ADMIN).count() > 0:
            print("数据库已存在基础数据，跳过数据注入。如需重置数据，请使用 --reset 参数。")
            return True

        print("开始注入初始系统数据...")
        
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
                "initial_capital": 100000.0,
                "description": "散户游资策略"
            },
            {
                "username": "robot_institution",
                "password": "robot123",
                "strategy": RobotStrategy.INSTITUTION,
                "initial_capital": 500000.0,
                "description": "正规机构策略"
            },
            {
                "username": "robot_short_seller",
                "password": "robot123",
                "strategy": RobotStrategy.SHORT_SELLER,
                "initial_capital": 300000.0,
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
            print(f"✓ 创建机器人账户: {robot.username} ({config['description']})")
        
        # 3. 创建示例真人账户
        print("\n创建示例真人账户...")
        demo_users = [
            {"username": "user01", "password": "user123", "initial_capital": 50000.0},
            {"username": "user02", "password": "user123", "initial_capital": 50000.0}
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
            print(f"✓ 创建真人账户: {user.username}")
        
        # 4. 创建股票清单
        print("\n创建股票清单...")
        stocks_config = [
            {
                "code": "SH600000", 
                "name": "浦发银行", 
                "description": "上海浦东发展银行，主营商业银行业务，包括存款、贷款、投资银行等金融服务",
                "initial_price": 10.50, 
                "drift": 0.0001, 
                "volatility": 0.15
            },
            {
                "code": "SH600519", 
                "name": "贵州茅台", 
                "description": "中国最大的白酒生产企业，主营高端白酒的生产与销售，品牌价值极高",
                "initial_price": 1680.00, 
                "drift": 0.0002, 
                "volatility": 0.18
            },
            {
                "code": "SZ000001", 
                "name": "平安银行", 
                "description": "全国性股份制商业银行，提供个人银行、公司银行、资产管理等综合金融服务",
                "initial_price": 15.30, 
                "drift": 0.00005, 
                "volatility": 0.20
            },
            {
                "code": "SZ000858", 
                "name": "五粮液", 
                "description": "中国知名白酒企业，以浓香型白酒为主，市场份额位居行业前列",
                "initial_price": 180.50, 
                "drift": 0.00015, 
                "volatility": 0.22
            },
            {
                "code": "SH601318", 
                "name": "中国平安", 
                "description": "综合性金融集团，业务涵盖保险、银行、投资等多个领域",
                "initial_price": 55.80, 
                "drift": 0.0001, 
                "volatility": 0.17
            },
            {
                "code": "SZ002594", 
                "name": "比亚迪", 
                "description": "全球领先的新能源汽车制造商，业务包括电动汽车、电池及光伏产品",
                "initial_price": 268.00, 
                "drift": 0.0003, 
                "volatility": 0.30
            },
            {
                "code": "SH688981", 
                "name": "中芯国际", 
                "description": "中国最大的集成电路制造企业，提供芯片代工服务",
                "initial_price": 55.00, 
                "drift": 0.00025, 
                "volatility": 0.28
            },
            {
                "code": "SZ300750", 
                "name": "宁德时代", 
                "description": "全球领先的动力电池制造商，为新能源汽车提供核心零部件",
                "initial_price": 420.00, 
                "drift": 0.0002, 
                "volatility": 0.25
            },
            {
                "code": "SH601988", 
                "name": "中国银行", 
                "description": "中国四大国有商业银行之一，业务网络遍布全球",
                "initial_price": 4.20, 
                "drift": 0.00003, 
                "volatility": 0.12
            },
            {
                "code": "SZ002475", 
                "name": "立讯精密", 
                "description": "全球知名的精密制造企业，主营消费电子产品的连接器及组件",
                "initial_price": 32.50, 
                "drift": 0.00018, 
                "volatility": 0.24
            }
        ]
        
        for config in stocks_config:
            stock = Stock(
                stock_code=config["code"],
                stock_name=config["name"],
                description=config["description"],
                initial_price=config["initial_price"],
                drift=config["drift"],
                volatility=config["volatility"],
                is_active=True
            )
            session.add(stock)
            print(f"✓ 添加股票: {config['code']} - {config['name']}")
        
        # 5. 初始化系统状态
        print("\n初始化系统状态...")
        system_state = SystemState(
            id=1,
            current_time=datetime(2024, 1, 1, 9, 30, 0),
            step_mode="day",
            step_count=0,
            is_fast_forward=False,
            last_report_year=2023,  # 初始化为2023年，2024年需要发布财报
            requires_financial_report=False,
            has_pending_news=False
        )
        session.add(system_state)
        print("✓ 系统状态已初始化 (起始时间: 2024-01-01)")
        
        session.commit()
        print("\n" + "="*60)
        print("✓ 数据初始化成功！所有表已建立。")
        print("="*60)
        return True
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ 数据注入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

def reset_database(db_path='trading_system.db'):
    """重置数据库"""
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"已物理删除旧数据库文件: {db_path}")
        except PermissionError:
            print(f"错误：无法删除文件 {db_path}，请先关闭正在连接该数据库的其他程序（如测试脚本）。")
            return False
    return init_system_data(db_path)

if __name__ == "__main__":
    db_file = 'trading_system.db'
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_database(db_file)
    else:
        init_system_data(db_file)
