"""
管理工具脚本
提供股票描述编辑、财报发布、新闻发布等管理功能
"""

import sys
from datetime import datetime
from models import (
    get_engine, get_session,
    Stock, FinancialReport, News, SystemState,
    NewsImpact
)

def list_stocks(session):
    """列出所有股票"""
    stocks = session.query(Stock).all()
    print("\n=== 股票清单 ===")
    for stock in stocks:
        print(f"\n{stock.stock_code} - {stock.stock_name}")
        print(f"  描述: {stock.description or '无'}")
        print(f"  初始价格: ¥{stock.initial_price:.2f}")
        print(f"  状态: {'活跃' if stock.is_active else '停牌'}")
    return stocks

def edit_stock_description(session):
    """编辑股票描述"""
    stocks = list_stocks(session)
    
    stock_code = input("\n请输入要编辑的股票代码: ").strip().upper()
    stock = session.query(Stock).filter(Stock.stock_code == stock_code).first()
    
    if not stock:
        print("错误：未找到该股票")
        return
    
    print(f"\n当前描述: {stock.description or '无'}")
    new_description = input("请输入新的描述（直接回车取消）: ").strip()
    
    if new_description:
        stock.description = new_description
        session.commit()
        print(f"✓ 股票 {stock_code} 的描述已更新")
    else:
        print("已取消")

def publish_financial_report(session):
    """发布财报"""
    # 获取系统状态
    system_state = session.query(SystemState).first()
    if not system_state:
        print("错误：系统状态未初始化")
        return
    
    current_year = system_state.current_time.year
    
    print(f"\n=== 发布 {current_year} 年度财报 ===")
    
    # 检查是否需要发布财报
    if not system_state.requires_financial_report:
        print(f"当前无需发布财报（上次发布年份: {system_state.last_report_year}）")
        return
    
    # 获取所有活跃股票
    stocks = session.query(Stock).filter(Stock.is_active == True).all()
    
    print(f"\n需要为以下 {len(stocks)} 支股票发布财报:")
    for stock in stocks:
        print(f"  - {stock.stock_code} {stock.stock_name}")
    
    # 为每支股票输入财报
    for stock in stocks:
        print(f"\n{'='*50}")
        print(f"股票: {stock.stock_code} - {stock.stock_name}")
        print(f"{'='*50}")
        
        # 检查是否已发布该年度财报
        existing = session.query(FinancialReport).filter(
            FinancialReport.stock_id == stock.id,
            FinancialReport.report_year == current_year
        ).first()
        
        if existing:
            print(f"该股票已发布 {current_year} 年度财报")
            continue
        
        print("\n请输入财报数据:")
        
        try:
            revenue = float(input("  营业收入（亿元）: "))
            net_profit = float(input("  净利润（亿元）: "))
            eps = float(input("  每股收益（元）: "))
            roe = float(input("  净资产收益率（%）: "))
            
            summary = input("  财报摘要: ").strip()
            
            # 创建财报
            report = FinancialReport(
                stock_id=stock.id,
                report_year=current_year,
                revenue=revenue,
                net_profit=net_profit,
                eps=eps,
                roe=roe,
                summary=summary,
                published_at=datetime.now()
            )
            session.add(report)
            print(f"✓ {stock.stock_code} 的财报已记录")
            
        except ValueError:
            print("✗ 输入错误，跳过该股票")
            continue
    
    # 检查是否所有股票都已发布财报
    reports_count = session.query(FinancialReport).filter(
        FinancialReport.report_year == current_year
    ).count()
    
    if reports_count >= len(stocks):
        system_state.requires_financial_report = False
        system_state.last_report_year = current_year
        print(f"\n✓ 所有股票的 {current_year} 年度财报已发布完成")
        print("系统可以继续推进")
    else:
        print(f"\n⚠ 还有 {len(stocks) - reports_count} 支股票未发布财报")
        print("系统暂时无法继续推进")
    
    session.commit()

def create_news(session):
    """创建新闻"""
    print("\n=== 创建新闻 ===")
    
    # 列出所有股票
    stocks = session.query(Stock).filter(Stock.is_active == True).all()
    print("\n可用股票:")
    for i, stock in enumerate(stocks, 1):
        print(f"  {i}. {stock.stock_code} - {stock.stock_name}")
    print(f"  0. 全市场新闻（不针对特定股票）")
    
    try:
        choice = int(input("\n请选择股票编号: "))
        
        stock_id = None
        if choice > 0 and choice <= len(stocks):
            stock_id = stocks[choice - 1].id
            print(f"选择股票: {stocks[choice - 1].stock_code}")
        elif choice == 0:
            print("创建全市场新闻")
        else:
            print("无效选择")
            return
        
        title = input("\n新闻标题: ").strip()
        content = input("新闻内容: ").strip()
        
        if not title or not content:
            print("标题和内容不能为空")
            return
        
        print("\n新闻影响类型:")
        print("  1. 积极影响 (POSITIVE)")
        print("  2. 消极影响 (NEGATIVE)")
        print("  3. 中性影响 (NEUTRAL)")
        
        impact_choice = int(input("请选择影响类型: "))
        impact_map = {
            1: NewsImpact.POSITIVE,
            2: NewsImpact.NEGATIVE,
            3: NewsImpact.NEUTRAL
        }
        
        if impact_choice not in impact_map:
            print("无效选择")
            return
        
        impact = impact_map[impact_choice]
        impact_score = float(input("影响强度（-1.0 到 1.0，负数表示消极影响）: "))
        
        # 创建新闻
        news = News(
            stock_id=stock_id,
            title=title,
            content=content,
            impact_type=impact,
            impact_score=impact_score,
            is_published=False,  # 新闻会在下一步开始时发布
            created_at=datetime.now()
        )
        session.add(news)
        
        # 更新系统状态
        system_state = session.query(SystemState).first()
        if system_state:
            system_state.has_pending_news = True
        
        session.commit()
        print("\n✓ 新闻已创建，将在下一步开始时发布")
        
    except (ValueError, IndexError):
        print("输入错误")

def view_pending_news(session):
    """查看待发布的新闻"""
    news_list = session.query(News).filter(News.is_published == False).all()
    
    if not news_list:
        print("\n当前没有待发布的新闻")
        return
    
    print(f"\n=== 待发布新闻（{len(news_list)}条）===")
    for news in news_list:
        print(f"\n新闻ID: {news.id}")
        if news.stock_id:
            stock = session.query(Stock).get(news.stock_id)
            print(f"关联股票: {stock.stock_code} - {stock.stock_name}")
        else:
            print("关联股票: 全市场新闻")
        print(f"标题: {news.title}")
        print(f"内容: {news.content}")
        print(f"影响类型: {news.impact_type.value}")
        print(f"影响强度: {news.impact_score}")

def view_financial_reports(session):
    """查看已发布的财报"""
    year = int(input("\n请输入要查看的年份: "))
    
    reports = session.query(FinancialReport).filter(
        FinancialReport.report_year == year
    ).all()
    
    if not reports:
        print(f"\n{year} 年没有已发布的财报")
        return
    
    print(f"\n=== {year} 年度财报 ===")
    for report in reports:
        stock = session.query(Stock).get(report.stock_id)
        print(f"\n{stock.stock_code} - {stock.stock_name}")
        print(f"  营业收入: ¥{report.revenue:.2f}亿")
        print(f"  净利润: ¥{report.net_profit:.2f}亿")
        print(f"  每股收益: ¥{report.eps:.2f}")
        print(f"  ROE: {report.roe:.2f}%")
        print(f"  摘要: {report.summary}")
        print(f"  发布时间: {report.published_at}")

def main_menu():
    """主菜单"""
    engine = get_engine('trading_system.db')
    session = get_session(engine)
    
    try:
        while True:
            print("\n" + "="*50)
            print("股票交易系统 - 管理工具")
            print("="*50)
            print("1. 查看股票清单")
            print("2. 编辑股票描述")
            print("3. 发布年度财报")
            print("4. 创建新闻")
            print("5. 查看待发布新闻")
            print("6. 查看历史财报")
            print("0. 退出")
            print("="*50)
            
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                list_stocks(session)
            elif choice == "2":
                edit_stock_description(session)
            elif choice == "3":
                publish_financial_report(session)
            elif choice == "4":
                create_news(session)
            elif choice == "5":
                view_pending_news(session)
            elif choice == "6":
                view_financial_reports(session)
            elif choice == "0":
                print("\n再见！")
                break
            else:
                print("无效选择，请重试")
    
    except KeyboardInterrupt:
        print("\n\n程序被中断")
    finally:
        session.close()

if __name__ == "__main__":
    main_menu()
