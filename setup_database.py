#!/usr/bin/env python3
"""
语C群宣监听插件 - 数据库设置脚本

项目: 语C群宣监听插件
作者: 银莎Silver Shakespeare
版本: 1.0.0
完成日期: 2025/12/16

数据库设置脚本功能:
- 初始化数据库表结构
- 清理测试数据并重置数据库
- 提供数据库管理命令

使用方法:
python setup_database.py [command]

命令:
- init: 初始化数据库表（默认）
- reset: 重置数据库（删除所有数据并重新创建表）
- stats: 显示数据库统计信息
- test: 运行数据库连接测试

作者: 数据库管理脚本
版本: 1.0.0
"""

import sys
import os
import json
from datetime import datetime

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from database_factory import get_database
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import database_factory
    get_database = database_factory.get_database

def init_database():
    """初始化数据库"""
    print("正在初始化数据库...")
    try:
        db = get_database()
        db.create_tables()
        print("[OK] 数据库表初始化成功")

        # 显示统计信息
        stats = db.get_stats()
        print("\n[STATS] 数据库统计信息:")
        print(f"  总群组数: {stats['total_groups']}")
        print(f"  历史记录数: {stats['total_history_records']}")
        print(f"  总看到次数: {stats['total_seen_count']}")

        if stats['group_type_stats']:
            print("  群组类型分布:")
            for group_type, count in stats['group_type_stats'].items():
                print(f"    {group_type}: {count}")

        return True

    except Exception as e:
        print(f"[ERROR] 数据库初始化失败: {e}")
        return False

def reset_database(force=False):
    """重置数据库"""
    if not force:
        print("[WARNING] 此操作将删除所有数据！")
        confirm = input("确认要重置数据库吗？(输入 'yes' 确认): ")

        if confirm.lower() != 'yes':
            print("操作已取消")
            return False

    print("正在重置数据库...")
    try:
        db = get_database()
        db.reset_tables()
        print("[OK] 数据库重置成功")

        # 重新初始化
        return init_database()

    except Exception as e:
        print(f"[ERROR] 数据库重置失败: {e}")
        return False

def show_stats():
    """显示数据库统计信息"""
    print("正在获取数据库统计信息...")
    try:
        db = get_database()

        stats = db.get_stats()
        print("\n[STATS] 数据库统计信息:")
        print(f"  总群组数: {stats['total_groups']}")
        print(f"  历史记录数: {stats['total_history_records']}")
        print(f"  总看到次数: {stats['total_seen_count']}")

        if stats['group_type_stats']:
            print("\n  群组类型分布:")
            for group_type, count in stats['group_type_stats'].items():
                print(f"    {group_type}: {count} 个群组")

        # 显示最近活跃的群组
        print("\n  最近活跃的群组 (前5个):")
        try:
            # 查询最近活跃的群组（按最后看到时间排序）
            recent_groups = db._query_recent_groups(5)  # 需要在数据库类中实现这个方法
            if recent_groups:
                for i, group in enumerate(recent_groups, 1):
                    group_id = group.get('group_id', 'Unknown')
                    last_seen = group.get('last_seen_group', 'Unknown')
                    seen_count = group.get('seen_count', 0)
                    group_type = group.get('classification_hints', {}).get('group_type', 'Unknown')
                    print(f"    {i}. 群号: {group_id} | 类型: {group_type} | 最后活跃: {last_seen} | 看到次数: {seen_count}")
            else:
                print("    无活跃群组数据")
        except Exception as e:
            print(f"    获取最近活跃群组失败: {e}")

        return True

    except Exception as e:
        print(f"[ERROR] 获取统计信息失败: {e}")
        return False

def test_database():
    """测试数据库连接"""
    print("正在测试数据库连接...")
    try:
        db = get_database()
        print("[OK] 数据库连接成功")

        # 测试基本操作
        stats = db.get_stats()
        print(f"[OK] 数据库查询测试成功 (群组数: {stats['total_groups']})")

        return True

    except Exception as e:
        print(f"[ERROR] 数据库测试失败: {e}")
        return False

def show_usage():
    """显示使用说明"""
    print("""
数据库管理脚本使用方法:

python setup_database.py [command]

可用命令:
  init    初始化数据库表结构 (默认)
  reset   重置数据库 (删除所有数据并重新创建表)
  stats   显示数据库统计信息
  test    运行数据库连接测试
  help    显示此帮助信息

示例:
  python setup_database.py init
  python setup_database.py reset
  python setup_database.py stats
""")

def main():
    """主函数"""
    print(f"QQ群监听插件 - 数据库管理脚本")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    # 获取命令行参数
    if len(sys.argv) < 2:
        command = "init"
    else:
        command = sys.argv[1].lower()

    # 检查是否有force参数
    force = "--force" in sys.argv or "-f" in sys.argv

    # 执行相应命令
    success = False

    if command == "init":
        success = init_database()
    elif command == "reset":
        success = reset_database(force=force)
    elif command == "stats":
        success = show_stats()
    elif command == "test":
        success = test_database()
    elif command in ["help", "-h", "--help"]:
        show_usage()
        return 0
    else:
        print(f"[ERROR] 未知命令: {command}")
        show_usage()
        return 1

    if success:
        print("\n[OK] 操作完成")
        return 0
    else:
        print("\n[ERROR] 操作失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
