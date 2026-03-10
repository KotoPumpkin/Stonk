"""
测试管理功能脚本
"""
from models import (
    get_engine, get_session,
    Stock, FinancialReport, News, SystemState, NewsImpact
)
from datetime import datetime

def test_stock_description():
    """测试股票描述功能"""
    print("\n=== 测试股票描述功能 ===")
    
    engine = get_engine('trading_system.db')
    session = get_session(engine)
    
    try:
        # 获取第一支股票
        stock = session.query(Stock).first()
        if not stock:
            print("❌ 没有找到股票")
            return
        
        print(f"股票: {stock.stock_code} - {stock.stock_name}")
        print(f"当前描述: {stock.description or '无'}")
        
        # 更新描述
        new_description = "这是一家科技公司，主要从事人工智能和云计算业务。近年来营收稳定增长，市场前景广阔。"
        stock.description = new_description
        session.commit()
        
        print(f"✓ 描述已更新为: {new_description}")
        
    finally:
        session.close()

def test_financial_report():
    """测试财报功能"""
    print("\n=== 测试财报功能 ===")
    
    engine = get_engine('trading_system.db')
    session = get_session(engine)
    
    try:
        # 获取系统状态
        system_state = session.query(SystemState).first()
        if not system_state:
            print("❌ 系统状态未初始化")
            return
        
        current_year = system_state.current_time.year
        print(f"当前年份: {current_year}")
        print(f"需要财报: {system_state.requires_financial_report}")
        
        # 获取第一支股票
        stock = session.query(Stock).filter(Stock.is_active == True).first()
        if not stock:
            print("❌ 没有找到活跃股票")
            return
        
        # 检查是否已有财报
        existing = session.query(FinancialReport).filter(
            FinancialReport.stock_code == stock.stock_code,
            FinancialReport.year == current_year
        ).first()
        
        if existing:
            print(f"✓ {stock.stock_code} 已有 {current_year} 年财报")
            print(f"  内容: {existing.content[:50]}...")
        else:
            # 创建测试财报
            report = FinancialReport(
                stock_code=stock.stock_code,
                year=current_year,
                content="测试财报：公司本年度营业收入100.5亿元，同比增长15%；净利润20.3亿元，同比增长12%；每股收益2.5元；净资产收益率15.5%。整体业绩表现优异，各项指标符合预期。",
                published_at=datetime.now()
            )
            session.add(report)
            session.commit()
            print(f"✓ 已为 {stock.stock_code} 创建 {current_year} 年财报")
        
    finally:
        session.close()

def test_news():
    """测试新闻功能"""
    print("\n=== 测试新闻功能 ===")
    
    engine = get_engine('trading_system.db')
    session = get_session(engine)
    
    try:
        # 获取第一支股票
        stock = session.query(Stock).filter(Stock.is_active == True).first()
        if not stock:
            print("❌ 没有找到活跃股票")
            return
        
        # 创建测试新闻
        # 积极新闻
        news1 = News(
            stock_code=stock.stock_code,
            title="科技板块迎来利好政策",
            content="政府宣布将加大对人工智能产业的扶持力度，预计将为相关企业带来更多发展机遇。",
            impact_type=NewsImpact.POSITIVE,
            impact_strength=0.7,
            is_published=False,
            created_at=datetime.now()
        )
        session.add(news1)
        
        # 消极新闻
        news2 = News(
            stock_code=stock.stock_code,
            title="市场监管趋严",
            content="监管部门出台新规，短期内可能影响业务扩张速度。",
            impact_type=NewsImpact.NEGATIVE,
            impact_strength=0.5,
            is_published=False,
            created_at=datetime.now()
        )
        session.add(news2)
        
        # 更新系统状态
        system_state = session.query(SystemState).first()
        if system_state:
            system_state.has_pending_news = True
        
        session.commit()
        
        # 查看待发布新闻
        pending = session.query(News).filter(News.is_published == False).all()
        print(f"✓ 已创建 2 条测试新闻")
        print(f"待发布新闻总数: {len(pending)}")
        for news in pending:
            print(f"  - {news.title} ({news.impact_type.value}, 强度: {news.impact_strength})")
        
    finally:
        session.close()

def test_system_status():
    """测试系统状态"""
    print("\n=== 测试系统状态 ===")
    
    engine = get_engine('trading_system.db')
    session = get_session(engine)
    
    try:
        system_state = session.query(SystemState).first()
        if not system_state:
            print("❌ 系统状态未初始化")
            return
        
        print(f"当前时间: {system_state.current_time}")
        print(f"步进模式: {system_state.step_mode}")
        print(f"步数: {system_state.step_count}")
        print(f"需要财报: {system_state.requires_financial_report}")
        print(f"上次财报年份: {system_state.last_report_year}")
        print(f"有待发布新闻: {system_state.has_pending_news}")
        
        # 统计各类数据
        stocks_count = session.query(Stock).filter(Stock.is_active == True).count()
        reports_count = session.query(FinancialReport).count()
        pending_news = session.query(News).filter(News.is_published == False).count()
        published_news = session.query(News).filter(News.is_published == True).count()
        
        print(f"\n数据统计:")
        print(f"  活跃股票: {stocks_count}")
        print(f"  已发布财报: {reports_count}")
        print(f"  待发布新闻: {pending_news}")
        print(f"  已发布新闻: {published_news}")
        
    finally:
        session.close()

def main():
    """运行所有测试"""
    print("=" * 50)
    print("管理功能测试")
    print("=" * 50)
    
    try:
        test_stock_description()
        test_financial_report()
        test_news()
        test_system_status()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
