"""
数据库迁移脚本 - 添加新功能字段
"""
import sqlite3
from datetime import datetime

def migrate_database():
    """迁移数据库到新版本"""
    conn = sqlite3.connect('trading_system.db')
    cursor = conn.cursor()
    
    print("开始数据库迁移...")
    
    try:
        # 1. 为stocks表添加description字段
        print("1. 添加股票描述字段...")
        cursor.execute("PRAGMA table_info(stocks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'description' not in columns:
            cursor.execute("ALTER TABLE stocks ADD COLUMN description TEXT DEFAULT ''")
            print("   ✓ 股票描述字段添加成功")
        else:
            print("   - 股票描述字段已存在")
        
        # 2. 创建financial_reports表
        print("2. 创建财报表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                revenue REAL NOT NULL,
                profit REAL NOT NULL,
                eps REAL NOT NULL,
                roe REAL NOT NULL,
                report_content TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stock_id) REFERENCES stocks(id),
                UNIQUE(stock_id, year)
            )
        """)
        print("   ✓ 财报表创建成功")
        
        # 3. 创建news表
        print("3. 创建新闻表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                impact_type TEXT NOT NULL,
                impact_degree REAL NOT NULL,
                target_stocks TEXT,
                created_step INTEGER NOT NULL,
                published_step INTEGER,
                is_published INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP
            )
        """)
        print("   ✓ 新闻表创建成功")
        
        # 4. 为system_state表添加last_report_year字段
        print("4. 添加上次财报年份字段...")
        cursor.execute("PRAGMA table_info(system_state)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'last_report_year' not in columns:
            cursor.execute("ALTER TABLE system_state ADD COLUMN last_report_year INTEGER DEFAULT 0")
            print("   ✓ 上次财报年份字段添加成功")
        else:
            print("   - 上次财报年份字段已存在")
        
        # 5. 为system_state表添加需要财报标记字段
        print("5. 添加财报需求标记字段...")
        cursor.execute("PRAGMA table_info(system_state)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'requires_financial_report' not in columns:
            cursor.execute("ALTER TABLE system_state ADD COLUMN requires_financial_report INTEGER DEFAULT 0")
            print("   ✓ 财报需求标记字段添加成功")
        else:
            print("   - 财报需求标记字段已存在")
        
        # 6. 为system_state表添加待发布新闻数量字段
        print("6. 添加待发布新闻数量字段...")
        cursor.execute("PRAGMA table_info(system_state)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'has_pending_news' not in columns:
            cursor.execute("ALTER TABLE system_state ADD COLUMN has_pending_news INTEGER DEFAULT 0")
            print("   ✓ 待发布新闻标记字段添加成功")
        else:
            print("   - 待发布新闻标记字段已存在")
        
        # 7. 创建news_confirmations表（记录玩家确认新闻）
        print("7. 创建新闻确认表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_confirmations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER NOT NULL,
                robot_id INTEGER NOT NULL,
                confirmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (news_id) REFERENCES news(id),
                FOREIGN KEY (robot_id) REFERENCES robots(id),
                UNIQUE(news_id, robot_id)
            )
        """)
        print("   ✓ 新闻确认表创建成功")
        
        conn.commit()
        print("\n✅ 数据库迁移完成！")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
