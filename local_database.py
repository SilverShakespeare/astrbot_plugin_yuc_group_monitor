"""
语C群宣监听插件 - 本地JSON数据库操作模块

项目: 语C群宣监听插件
作者: 银莎Silver Shakespeare
版本: 1.0.0
完成日期: 2025/12/16

本地JSON数据库操作模块，当MySQL不可用时使用。
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
import pytz

try:
    from .config import LOCAL_DB_PATHS
except ImportError:
    try:
        from config import LOCAL_DB_PATHS
    except ImportError:
        import config
        LOCAL_DB_PATHS = config.LOCAL_DB_PATHS

class LocalDatabase:
    """
    本地JSON数据库实现
    用于在无法连接MySQL时的降级方案
    """

    def __init__(self):
        """
        初始化本地数据库
        """
        self._ensure_data_directory_exists()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.latest_path = os.path.join(base_dir, LOCAL_DB_PATHS["group_raw_latest"])
        self.history_path = os.path.join(base_dir, LOCAL_DB_PATHS["group_raw_history"])

        # 初始化数据存储
        self.latest_data = {}
        self.history_data = []
        self._ensure_data_loaded()

    def _ensure_data_directory_exists(self):
        """确保数据目录存在"""
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def _ensure_data_loaded(self):
        """加载数据文件"""
        # 加载最新数据
        if os.path.exists(self.latest_path):
            with open(self.latest_path, 'r', encoding='utf-8') as f:
                try:
                    self.latest_data = json.load(f)
                except json.JSONDecodeError:
                    self.latest_data = {}
        else:
            self.latest_data = {}

        # 加载历史数据
        if os.path.exists(self.history_path):
            with open(self.history_path, 'r', encoding='utf-8') as f:
                try:
                    self.history_data = json.load(f)
                except json.JSONDecodeError:
                    self.history_data = []
        else:
            self.history_data = []

    def _save_data(self):
        """保存数据到文件"""
        with open(self.latest_path, 'w', encoding='utf-8') as f:
            json.dump(self.latest_data, f, ensure_ascii=False, indent=2)

        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(self.history_data, f, ensure_ascii=False, indent=2)

    def create_tables(self):
        """本地数据库不需要创建表，这里是空实现"""
        pass

    def reset_tables(self):
        """重置本地数据库"""
        self.latest_data = {}
        self.history_data = []
        self._save_data()
        print("本地数据库已重置")

    def get_group_latest(self, group_id: str) -> Optional[Dict[str, Any]]:
        """获取群组最新数据"""
        return self.latest_data.get(group_id)

    def process_group_content(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理群组内容"""
        group_id = group_data["group_id"]
        content_hash = group_data["content_hash"]

        try:
            existing_data = self.get_group_latest(group_id)

            if existing_data:
                # 群组已存在，检查内容是否变更
                if existing_data["content_hash"] == content_hash:
                    # 内容未变，只更新计数和时间
                    existing_data["timestamps"]["last_seen_group"] = group_data["timestamps"]["last_seen_group"]
                    existing_data["seen_count"] += 1
                    self._save_data()
                    return {
                        "success": True,
                        "action": "updated_existing",
                        "group_id": group_id,
                        "content_changed": False
                    }
                else:
                    # 内容已变，版本递增，插入历史，更新最新
                    new_version = existing_data["content_version"] + 1

                    # 插入历史记录
                    history_record = {
                        "id": len(self.history_data) + 1,
                        "group_id": group_id,
                        "content_version": existing_data["content_version"],
                        "content": existing_data["content"],
                        "content_hash": existing_data["content_hash"],
                        "tags": existing_data["tags"],
                        "classification_hints": existing_data["classification_hints"],
                        "source": existing_data["source_meta"]["source"],
                        "batch_id": existing_data["source_meta"]["batch_id"],
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    self.history_data.append(history_record)

                    # 更新最新数据
                    group_data["content_version"] = new_version
                    self.latest_data[group_id] = group_data
                    self._save_data()

                    return {
                        "success": True,
                        "action": "updated_with_new_version",
                        "group_id": group_id,
                        "content_changed": True,
                        "new_version": new_version
                    }
            else:
                # 新群组，直接插入
                self.latest_data[group_id] = group_data
                self._save_data()

                return {
                    "success": True,
                    "action": "inserted_new",
                    "group_id": group_id,
                    "content_changed": True,
                    "version": 1
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "group_id": group_id
            }

    def get_group_history(self, group_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取群组历史记录"""
        history = [record for record in self.history_data if record["group_id"] == group_id]
        history.sort(key=lambda x: x["content_version"], reverse=True)
        return history[:limit]

    def search_groups(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """搜索群组（本地实现简单的关键词匹配）"""
        results = []
        keyword_lower = keyword.lower()

        for group_id, data in self.latest_data.items():
            if keyword_lower in data["content"].lower():
                results.append({
                    "group_id": group_id,
                    "content": data["content"],
                    "tags": data["tags"],
                    "classification_hints": data["classification_hints"],
                    "first_seen_group": data["timestamps"]["first_seen_group"],
                    "last_seen_group": data["timestamps"]["last_seen_group"],
                    "seen_count": data["seen_count"]
                })

                if len(results) >= limit:
                    break

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_groups = len(self.latest_data)
        total_history = len(self.history_data)
        total_seen = sum(data.get("seen_count", 0) for data in self.latest_data.values())

        # 统计群组类型
        type_stats = {}
        for data in self.latest_data.values():
            group_type = data.get("classification_hints", {}).get("group_type")
            if group_type:
                type_stats[group_type] = type_stats.get(group_type, 0) + 1

        return {
            "total_groups": total_groups,
            "total_history_records": total_history,
            "total_seen_count": total_seen,
            "group_type_stats": type_stats
        }

    def _query_recent_groups(self, limit: int = 5) -> List[Dict[str, Any]]:
        """查询最近活跃的群组（本地实现）"""
        # 按最后看到时间排序
        sorted_groups = sorted(
            self.latest_data.values(),
            key=lambda x: x.get("timestamps", {}).get("last_seen_group", ""),
            reverse=True
        )

        recent_groups = []
        for group in sorted_groups[:limit]:
            recent_groups.append({
                "group_id": group.get("group_id"),
                "last_seen_group": group.get("timestamps", {}).get("last_seen_group"),
                "seen_count": group.get("seen_count", 0),
                "classification_hints": group.get("classification_hints", {})
            })

        return recent_groups


# 测试函数
if __name__ == "__main__":
    db = LocalDatabase()
    print("本地数据库初始化完成")

    # 测试统计
    stats = db.get_stats()
    print(f"数据库统计: {stats}")