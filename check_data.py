#!/usr/bin/env python3
"""
语C群宣监听插件 - 数据检查脚本

项目: 语C群宣监听插件
作者: 银莎Silver Shakespeare
版本: 1.0.0
完成日期: 2025/12/16

数据检查脚本，用于查看插件处理的数据。
"""

import sys
import os
import json

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from database_factory import get_database
except ImportError:
    import database_factory
    get_database = database_factory.get_database

def show_recent_groups(limit=10):
    """显示最近处理的群组"""
    print("=== 最近处理的群组 ===")
    db = get_database()

    try:
        # 获取统计信息
        stats = db.get_stats()
        print(f"数据库统计: {stats['total_groups']} 个群组, {stats['total_history_records']} 条历史记录")
        print()

        # 这里可以扩展显示最近活跃的群组
        # 由于MySQL没有直接按时间排序的查询，我们可以显示一些示例

        print("注意: 要查看具体群组数据，请使用 'python check_data.py show <群号>'")
        print("例如: python check_data.py show 987654321")

    except Exception as e:
        print(f"获取统计信息失败: {e}")

def show_group_data(group_id):
    """显示特定群组的详细信息"""
    print(f"=== 群组 {group_id} 的详细信息 ===")
    db = get_database()

    try:
        # 获取最新数据
        latest_data = db.get_group_latest(group_id)
        if latest_data:
            print("最新数据:")
            print(json.dumps(latest_data, ensure_ascii=False, indent=2))
            print()

            # 获取历史记录
            history = db.get_group_history(group_id, limit=5)
            if history:
                print(f"历史记录 (最近 {len(history)} 条):")
                for i, record in enumerate(history, 1):
                    print(f"\n--- 版本 {record['content_version']} ---")
                    print(f"创建时间: {record['created_at']}")
                    print(f"内容哈希: {record['content_hash'][:16]}...")
                    print(f"内容预览: {record['content'][:100]}...")
                    if record['tags']:
                        print(f"标签: {record['tags']}")
                    print(f"群类型: {record.get('classification_hints', {}).get('group_type', '未知')}")
            else:
                print("无历史记录")
        else:
            print(f"未找到群组 {group_id} 的数据")

    except Exception as e:
        print(f"获取群组数据失败: {e}")

def search_content(keyword, limit=5):
    """搜索包含关键词的内容"""
    print(f"=== 搜索关键词 '{keyword}' ===")
    db = get_database()

    try:
        results = db.search_groups(keyword, limit=limit)
        if results:
            print(f"找到 {len(results)} 个匹配结果:")
            for i, result in enumerate(results, 1):
                print(f"\n--- 结果 {i} ---")
                print(f"群号: {result['group_id']}")
                print(f"内容预览: {result['content'][:150]}...")
                print(f"标签: {result['tags']}")
                print(f"群类型: {result.get('classification_hints', {}).get('group_type', '未知')}")
                print(f"看到次数: {result['seen_count']}")
        else:
            print("未找到匹配的内容")

    except Exception as e:
        print(f"搜索失败: {e}")

def show_sample_data():
    """显示示例数据"""
    print("=== 数据库中的示例数据 ===")
    db = get_database()

    try:
        # 尝试获取一些群组数据进行展示
        # 这里可以根据实际需求扩展
        stats = db.get_stats()
        print(f"当前数据库中有 {stats['total_groups']} 个群组")

        # 如果想查看具体数据，可以在这里添加逻辑

    except Exception as e:
        print(f"获取示例数据失败: {e}")

def main():
    print("QQ群监听插件 - 数据检查工具")
    print("=" * 50)

    if len(sys.argv) < 2:
        print("用法:")
        print("  python check_data.py stats          # 显示统计信息")
        print("  python check_data.py show <群号>    # 显示特定群组详情")
        print("  python check_data.py search <关键词> # 搜索内容")
        print("  python check_data.py sample         # 显示示例数据")
        return

    command = sys.argv[1].lower()

    if command == "stats":
        show_recent_groups()
    elif command == "show" and len(sys.argv) >= 3:
        show_group_data(sys.argv[2])
    elif command == "search" and len(sys.argv) >= 3:
        search_content(sys.argv[2])
    elif command == "sample":
        show_sample_data()
    else:
        print("无效命令。使用 'python check_data.py' 查看帮助。")

if __name__ == "__main__":
    main()
