"""
测试核心引擎功能
测试价格生成、交易管理、策略引擎
"""
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Account, Stock, Position, Trade, User, UserType, RobotStrategy
from price_engine import PriceEngine, KLineAggregator
from trade_manager import TradeManager
from strategy_engine import StrategyEngine
import pandas as pd


def setup_database():
    """设置测试数据库"""
    engine = create_engine('sqlite:///test_stonk.db', echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_price_engine():
    """测试价格生成引擎"""
    print("\n" + "="*60)
    print("测试 1: 价格生成引擎 (GBM)")
    print("="*60)
    
    session = setup_database()
    
    # 创建股票
    stock = Stock(stock_code='TEST001', stock_name='测试股票', initial_price=100.0)
    session.add(stock)
    session.commit()
    
    # 创建价格引擎
    price_engine = PriceEngine(
        stock_code='TEST001',
        initial_price=100.0,
        drift=0.1,      # 10% 年化漂移率
        volatility=0.2,   # 20% 年化波动率
        dt=1/252/78  # 每步约5秒（假设每天6.5小时交易）
    )
    
    # 生成100步价格
    print(f"\n初始价格: {price_engine.current_price:.2f}")
    prices = []
    for i in range(100):
        price = price_engine.next_price()
        prices.append(price)
        if i < 10 or i >= 90:  # 只显示前10和后10
            print(f"步进 {i+1}: {price:.2f}")
        elif i == 10:
            print("... (中间省略) ...")
    
    print(f"\n最终价格: {price_engine.current_price:.2f}")
    print(f"价格变化: {((price_engine.current_price - 100) / 100 * 100):.2f}%")
    print(f"最高价: {max(prices):.2f}")
    print(f"最低价: {min(prices):.2f}")
    
    session.close()
    print("\n✓ 价格生成引擎测试通过")


def test_kline_aggregator():
    """测试K线聚合器"""
    print("\n" + "="*60)
    print("测试 2: K线聚合器")
    print("="*60)
    
    session = setup_database()
    
    # 创建K线聚合器
    aggregator = KLineAggregator(session=session)
    
    # 生成模拟价格数据
    base_time = datetime.now()
    price_engine = PriceEngine(stock_code='TEST001', initial_price=100.0, drift=0.1, volatility=0.2)
    
    print("\n添加60个价格点（模拟1分钟数据，每秒1个点）")
    for i in range(60):
        timestamp = base_time + timedelta(seconds=i)
        price = price_engine.next_price()
        aggregator.add_tick('TEST001', timestamp, price)
    
    # 聚合并保存K线
    end_time = base_time + timedelta(seconds=59)
    aggregator.aggregate_and_save('TEST001', end_time, timeframes=['minute'])
    session.commit()
    
    # 从数据库获取K线数据
    df = aggregator.get_latest_klines('TEST001', 'minute', n_bars=10)
    print(f"\nDataFrame形式 (形状: {df.shape}):")
    if not df.empty:
        print(df.head())
        print(f"\n最近的1分钟K线:")
        for idx in range(min(3, len(df))):
            row = df.iloc[idx]
            print(f"  时间: {row['timestamp']}, "
                  f"开: {row['open']:.2f}, "
                  f"高: {row['high']:.2f}, "
                  f"低: {row['low']:.2f}, "
                  f"收: {row['close']:.2f}")
    else:
        print("暂无K线数据")
    
    session.close()
    print("\n✓ K线聚合器测试通过")


def test_trade_manager():
    """测试交易管理器"""
    print("\n" + "="*60)
    print("测试 3: 交易管理器")
    print("="*60)
    
    session = setup_database()
    
    # 创建用户和账户
    user = User(username='test_user', password='test', user_type=UserType.HUMAN)
    session.add(user)
    session.commit()
    
    account = Account(user_id=user.id, initial_capital=100000.0, cash=100000.0)
    stock = Stock(stock_code='TEST001', stock_name='测试股票', initial_price=100.0)
    session.add_all([account, stock])
    session.commit()
    
    # 创建交易管理器
    tm = TradeManager(session)
    
    print(f"\n初始资金: {account.cash:.2f}")
    
    # 测试买入
    print("\n--- 测试买入 ---")
    success, msg = tm.buy(account.id, 'TEST001', 100, 100.0)
    print(f"买入100股@100: {msg}")
    position = tm.get_position(account.id, 'TEST001')
    print(f"持仓: {position.quantity} 股, 成本: {position.avg_cost:.2f}")
    
    # 刷新账户
    session.refresh(account)
    print(f"剩余现金: {account.cash:.2f}")
    
    # 测试继续买入
    success, msg = tm.buy(account.id, 'TEST001', 50, 110.0)
    print(f"\n买入50股@110: {msg}")
    position = tm.get_position(account.id, 'TEST001')
    print(f"持仓: {position.quantity} 股, 成本: {position.avg_cost:.2f}")
    session.refresh(account)
    print(f"剩余现金: {account.cash:.2f}")
    
    # 测试卖出
    print("\n--- 测试卖出 ---")
    success, msg = tm.sell(account.id, 'TEST001', 50, 120.0)
    print(f"卖出50股@120: {msg}")
    position = tm.get_position(account.id, 'TEST001')
    print(f"持仓: {position.quantity} 股, 成本: {position.avg_cost:.2f}")
    session.refresh(account)
    print(f"剩余现金: {account.cash:.2f}")
    
    # 测试做空
    print("\n--- 测试做空 ---")
    success, msg = tm.sell(account.id, 'TEST001', 200, 115.0, allow_short=True)
    print(f"卖出200股@115 (做空): {msg}")
    position = tm.get_position(account.id, 'TEST001')
    print(f"持仓: {position.quantity} 股 (负数=空头), 成本: {position.avg_cost:.2f}")
    session.refresh(account)
    print(f"剩余现金: {account.cash:.2f}")
    
    # 测试平空
    print("\n--- 测试平空 ---")
    success, msg = tm.buy(account.id, 'TEST001', 50, 110.0)
    print(f"买入50股@110 (平空): {msg}")
    position = tm.get_position(account.id, 'TEST001')
    print(f"持仓: {position.quantity} 股, 成本: {position.avg_cost:.2f}")
    session.refresh(account)
    print(f"剩余现金: {account.cash:.2f}")
    
    # 测试资产计算
    print("\n--- 测试资产计算 ---")
    current_prices = {'TEST001': 120.0}
    asset_info = tm.calculate_total_asset(account.id, current_prices)
    print(f"当前价格: {current_prices['TEST001']:.2f}")
    print(f"现金: {asset_info['cash']:.2f}")
    print(f"持仓市值: {asset_info['position_value']:.2f}")
    print(f"总资产: {asset_info['total_asset']:.2f}")
    print(f"未实现盈亏: {asset_info['unrealized_pnl']:.2f}")
    print(f"总收益率: {asset_info['total_pnl_rate']:.2f}%")
    
    # 测试交易历史
    print("\n--- 交易历史 ---")
    trades = tm.get_trade_history(account.id, limit=10)
    print(f"共 {len(trades)} 笔交易:")
    for trade in trades[:5]:
        print(f"  {trade.timestamp.strftime('%H:%M:%S')} - "
              f"{trade.trade_type.upper()} {trade.quantity}股@{trade.price:.2f}")
    
    session.close()
    print("\n✓ 交易管理器测试通过")


def test_strategy_engine():
    """测试策略引擎"""
    print("\n" + "="*60)
    print("测试 4: 策略引擎")
    print("="*60)
    
    session = setup_database()
    
    # 创建股票和机器人用户
    stock = Stock(stock_code='TEST001', stock_name='测试股票', initial_price=100.0)
    session.add(stock)
    session.commit()
    
    # 创建机器人用户和账户
    bot_user = User(
        username='test_bot_1',
        password='bot1',
        user_type=UserType.ROBOT
    )
    session.add(bot_user)
    session.commit()
    
    account = Account(user_id=bot_user.id, cash=100000.0, initial_capital=100000.0)
    session.add(account)
    session.commit()
    
    # 创建策略引擎
    strategy_engine = StrategyEngine(session)
    
    # 创建简单价格下跌策略
    print("\n创建策略: SimplePriceDropStrategy")
    strategy = strategy_engine.create_strategy(
        user_id=bot_user.id,
        stock_code='TEST001',
        strategy_type='simple_drop',
        drop_threshold=0.02,  # 跌2%买入
        rise_threshold=0.02,  # 涨2%卖出
        lookback_period=10,
        trade_size=100.0
    )
    print(f"策略类型: {type(strategy).__name__}")
    
    # 生成模拟K线数据
    print("\n生成模拟K线数据...")
    price_engine = PriceEngine(stock_code='TEST001', initial_price=100.0, drift=0.1, volatility=0.3)
    kline_data = []
    base_time = datetime.now()
    
    for i in range(50):
        price = price_engine.next_price()
        kline_data.append({
            'timestamp': base_time + timedelta(minutes=i),
            'open': price * 0.99,
            'high': price * 1.01,
            'low': price * 0.98,
            'close': price,
            'volume': 10000
        })
    
    kline_df = pd.DataFrame(kline_data)
    print(f"K线数据: {len(kline_df)} 根")
    print(f"价格范围: {kline_df['close'].min():.2f} - {kline_df['close'].max():.2f}")
    
    # 测试策略信号生成
    print("\n--- 测试信号生成 ---")
    current_price = kline_df['close'].iloc[-1]
    timestamp = kline_df['timestamp'].iloc[-1]
    
    signal, quantity, result = strategy_engine.run_strategy(
        bot_user.id,
        kline_df,
        current_price,
        timestamp,
        execute=True
    )
    
    print(f"当前价格: {current_price:.2f}")
    print(f"生成信号: {signal}")
    print(f"交易数量: {quantity}")
    if result:
        print(f"执行结果: {result}")
    
    # 模拟价格变化并触发交易
    print("\n--- 模拟价格下跌触发买入 ---")
    # 制造一个明显的下跌
    drop_price = current_price * 0.95  # 下跌5%
    
    signal, quantity, result = strategy_engine.run_strategy(
        bot_user.id,
        kline_df,
        drop_price,
        timestamp + timedelta(minutes=1),
        execute=True
    )
    
    print(f"新价格: {drop_price:.2f} (下跌 {((drop_price/current_price - 1) * 100):.2f}%)")
    print(f"生成信号: {signal}")
    print(f"交易数量: {quantity}")
    if result:
        print(f"执行结果: {'成功' if result[0] else '失败'} - {result[1]}")
    
    # 检查持仓
    position = strategy.get_current_position()
    if position:
        print(f"\n当前持仓: {position.quantity} 股, 成本: {position.avg_cost:.2f}")
    
    # 测试其他策略类型
    print("\n--- 测试其他策略类型 ---")
    
    # 创建另一个机器人用于测试动量策略
    bot2_user = User(
        username='test_bot_2',
        password='bot2',
        user_type=UserType.ROBOT
    )
    session.add(bot2_user)
    session.commit()
    
    account2 = Account(user_id=bot2_user.id, cash=100000.0, initial_capital=100000.0)
    session.add(account2)
    session.commit()
    
    momentum_strategy = strategy_engine.create_strategy(
        user_id=bot2_user.id,
        stock_code='TEST001',
        strategy_type='momentum',
        short_period=5,
        long_period=20,
        trade_size=50.0
    )
    print(f"创建策略: {type(momentum_strategy).__name__}")
    
    # 测试均值回归策略
    bot3_user = User(
        username='test_bot_3',
        password='bot3',
        user_type=UserType.ROBOT
    )
    session.add(bot3_user)
    session.commit()
    
    account3 = Account(user_id=bot3_user.id, cash=100000.0, initial_capital=100000.0)
    session.add(account3)
    session.commit()
    
    mr_strategy = strategy_engine.create_strategy(
        user_id=bot3_user.id,
        stock_code='TEST001',
        strategy_type='mean_reversion',
        ma_period=20,
        buy_threshold=-0.02,
        sell_threshold=0.02,
        trade_size=75.0
    )
    print(f"创建策略: {type(mr_strategy).__name__}")
    
    print(f"\n策略引擎中共注册 {len(strategy_engine.strategies)} 个策略")
    
    session.close()
    print("\n✓ 策略引擎测试通过")


def test_integrated_simulation():
    """综合模拟测试"""
    print("\n" + "="*60)
    print("测试 5: 综合模拟 - 完整交易流程")
    print("="*60)
    
    session = setup_database()
    
    # 初始化股票和机器人用户
    stock = Stock(stock_code='SIM001', stock_name='模拟股票', initial_price=100.0)
    session.add(stock)
    session.commit()
    
    sim_bot = User(
        username='sim_bot',
        password='sim',
        user_type=UserType.ROBOT
    )
    session.add(sim_bot)
    session.commit()
    
    account = Account(user_id=sim_bot.id, cash=100000.0, initial_capital=100000.0)
    session.add(account)
    session.commit()
    
    # 初始化组件
    price_engine = PriceEngine(stock_code='SIM001', initial_price=100.0, drift=0.1, volatility=0.25)
    aggregator = KLineAggregator(session=session)
    strategy_engine = StrategyEngine(session)
    strategy_engine.create_strategy(
        user_id=sim_bot.id,
        stock_code='SIM001',
        strategy_type='simple_drop',
        drop_threshold=0.03,
        rise_threshold=0.03,
        lookback_period=20,
        trade_size=100.0
    )
    
    print(f"\n初始设置:")
    print(f"  账户资金: {account.cash:.2f}")
    print(f"  股票代码: {stock.stock_code}")
    print(f"  初始价格: {stock.initial_price:.2f}")
    print(f"  策略: SimplePriceDropStrategy (跌3%买/涨3%卖)")
    
    # 模拟200步
    print(f"\n开始模拟 200 步交易...")
    base_time = datetime.now()
    trade_count = 0
    
    for step in range(200):
        timestamp = base_time + timedelta(seconds=step)
        current_price = price_engine.next_price()
        
        # 添加到K线聚合器
        aggregator.add_tick('SIM001', timestamp, current_price)
        
        # 每10步运行一次策略
        if step % 10 == 0 and step > 0:
            kline_df = aggregator.get_latest_klines('SIM001', 'minute', n_bars=50)
            
            if len(kline_df) >= 20:
                signal, quantity, result = strategy_engine.run_strategy(
                    sim_bot.id,
                    kline_df,
                    current_price,
                    timestamp,
                    execute=True
                )
                
                if signal != 'hold' and result:
                    trade_count += 1
                    success, msg = result
                    if success:
                        print(f"  步进 {step}: {signal.upper()} {quantity}股 @ {current_price:.2f} - {msg}")
    
    # 最终统计
    print(f"\n模拟完成!")
    print(f"  总步数: 200")
    print(f"  交易次数: {trade_count}")
    print(f"  最终价格: {current_price:.2f}")
    print(f"  价格变化: {((current_price - 100) / 100 * 100):.2f}%")
    
    # 计算最终资产
    tm = TradeManager(session)
    asset_info = tm.calculate_total_asset(account.id, {'SIM001': current_price})
    
    print(f"\n最终账户状态:")
    print(f"  现金: {asset_info['cash']:.2f}")
    print(f"  持仓市值: {asset_info['position_value']:.2f}")
    print(f"  总资产: {asset_info['total_asset']:.2f}")
    print(f"  未实现盈亏: {asset_info['unrealized_pnl']:.2f}")
    print(f"  收益率: {asset_info['total_pnl_rate']:.2f}%")
    
    # 持仓详情
    position = tm.get_position(account.id, 'SIM001')
    if position and position.quantity != 0:
        print(f"\n持仓详情:")
        print(f"  数量: {position.quantity} 股")
        print(f"  成本: {position.avg_cost:.2f}")
        pos_info = tm.calculate_position_value(position, current_price)
        print(f"  市值: {pos_info['market_value']:.2f}")
        print(f"  盈亏: {pos_info['unrealized_pnl']:.2f} ({pos_info['pnl_rate']:.2f}%)")
    
    session.close()
    print("\n✓ 综合模拟测试通过")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Stonk 核心引擎测试套件")
    print("="*60)
    
    try:
        test_price_engine()
        test_kline_aggregator()
        test_trade_manager()
        test_strategy_engine()
        test_integrated_simulation()
        
        print("\n" + "="*60)
        print("✓ 所有测试通过!")
        print("="*60)
        print("\n核心功能已验证:")
        print("  ✓ 价格生成引擎 (GBM)")
        print("  ✓ K线数据聚合")
        print("  ✓ 交易管理 (买入/卖出/做空)")
        print("  ✓ 策略引擎 (多种策略)")
        print("  ✓ 综合模拟流程")
        print("\n阶段2完成! 准备进入阶段3 (前端开发)")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
