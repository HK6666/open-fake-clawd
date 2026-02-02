#!/usr/bin/env python3
"""
生成模拟的历史请求数据用于测试热力图
"""

import aiosqlite
import random
from datetime import datetime, timedelta
from pathlib import Path

# 数据库路径 - 根据你的实际路径调整
DB_PATH = Path("ccbot.db")

async def generate_mock_data():
    """生成最近365天的模拟请求数据"""
    
    # 连接数据库
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    
    try:
        # 清理旧数据（可选）
        await conn.execute("DELETE FROM daily_request_counts")
        await conn.commit()
        print("[清理] 旧数据已清除")
        
        # 生成365天的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # 模拟用户ID列表
        user_ids = [123456789, 987654321, 555666777]
        
        # 生成数据点
        data_points = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 随机决定是否生成这一天的数据（70%概率有数据）
            if random.random() < 0.7:
                # 为每个用户生成数据
                for user_id in user_ids:
                    # 随机请求数，但制造一些高峰
                    base_count = random.randint(0, 20)
                    
                    # 制造一些活跃的高峰日（10%概率是高活跃日）
                    if random.random() < 0.1:
                        base_count = random.randint(30, 80)
                    
                    # 制造几个超级活跃日（5%概率）
                    if random.random() < 0.05:
                        base_count = random.randint(100, 200)
                    
                    if base_count > 0:
                        created_at = datetime.now() - timedelta(days=random.randint(0, 365))
                        data_points.append((
                            date_str,
                            user_id,
                            base_count,
                            created_at,
                            created_at
                        ))
            
            current_date += timedelta(days=1)
        
        # 批量插入数据
        await conn.executemany(
            """
            INSERT INTO daily_request_counts (date, user_id, request_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            data_points
        )
        await conn.commit()
        
        print(f"[OK] 成功生成 {len(data_points)} 条请求记录")
        
        # 显示统计信息
        cursor = await conn.execute(
            "SELECT COUNT(DISTINCT date) as days, SUM(request_count) as total FROM daily_request_counts"
        )
        row = await cursor.fetchone()
        print(f"[统计] {row['days']} 个活跃日期，总计 {row['total']} 次请求")
        
        # 显示最近30天的数据示例
        print("\n[最近30天数据预览]：")
        cursor = await conn.execute(
            """
            SELECT date, SUM(request_count) as total_count
            FROM daily_request_counts
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
            """
        )
        rows = await cursor.fetchall()
        for row in reversed(rows):
            count = row['total_count']
            bar = "█" * min(count // 5, 20)  # 每5个请求一个方块，最多20个
            print(f"  {row['date']}: {count:4d} {bar}")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()
        print("\n[关闭] 数据库连接已关闭")

if __name__ == "__main__":
    import asyncio
    
    print("[开始] 生成模拟数据...")
    print(f"[数据库] 路径: {DB_PATH.absolute()}")
    
    if not DB_PATH.exists():
        print(f"[ERROR] 数据库文件不存在: {DB_PATH}")
        print("请先启动一次后端服务以创建数据库")
    else:
        asyncio.run(generate_mock_data())
        print("\n[完成] 刷新 Dashboard 即可看到热力图效果")
