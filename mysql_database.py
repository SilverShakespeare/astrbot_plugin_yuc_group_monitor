"""
语C群宣监听插件 - MySQL数据库操作模块

项目: 语C群宣监听插件
作者: 银莎Silver Shakespeare
版本: 1.0.0
完成日期: 2025/12/16

MySQL数据库操作模块，实现PDF文档中定义的数据库schema。
"""

import pymysql
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager

try:
    from .config import DB_CONFIG
except ImportError:
    import config
    DB_CONFIG = config.DB_CONFIG

class MySQLDatabase:
    """
    MySQL数据库操作类
    实现PDF文档中定义的数据库表结构和操作
    """

    def __init__(self):
        """
        初始化MySQL数据库连接
        """
        self.connection_params = DB_CONFIG
        self.connection = None
        self.connect()

    def connect(self):
        """
        建立数据库连接
        """
        try:
            self.connection = pymysql.connect(**self.connection_params)
            print("MySQL数据库连接成功")
        except Exception as e:
            print(f"MySQL数据库连接失败: {e}")
            raise

    def disconnect(self):
        """
        断开数据库连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    @contextmanager
    def get_cursor(self):
        """
        获取数据库游标的上下文管理器
        自动处理连接和事务
        """
        cursor = None
        try:
            if not self.connection or not self.connection.open:
                self.connect()
            cursor = self.connection.cursor()
            yield cursor
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()

    def create_tables(self):
        """
        创建数据库表
        根据PDF文档创建group_raw_latest和group_raw_history表
        """
        with self.get_cursor() as cursor:
            # 创建最新表 group_raw_latest
            create_latest_table_sql = """
            CREATE TABLE IF NOT EXISTS group_raw_latest (
                group_id VARCHAR(32) NOT NULL PRIMARY KEY COMMENT '群号，唯一键',
                content MEDIUMTEXT NOT NULL COMMENT '清洗后的文案',
                content_hash CHAR(64) NOT NULL COMMENT '文案哈希，用于判定变更',
                content_version INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '文案版本，变更递增',
                tags JSON DEFAULT (JSON_ARRAY()) COMMENT '初判标签列表',
                classification_hints JSON DEFAULT (JSON_OBJECT()) COMMENT '分类提示信息',
                source VARCHAR(64) DEFAULT NULL COMMENT '数据来源标记',
                batch_id VARCHAR(64) DEFAULT NULL COMMENT '抓取批次ID',
                first_seen_group DATETIME NOT NULL COMMENT '首次发现时间',
                last_seen_group DATETIME NOT NULL COMMENT '最近看到时间',
                last_updated_content DATETIME NOT NULL COMMENT '最近文案更新时间',
                seen_count INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '看到次数',
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FULLTEXT KEY ft_content (content) COMMENT '全文索引'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """

            # 创建历史表 group_raw_history
            create_history_table_sql = """
            CREATE TABLE IF NOT EXISTS group_raw_history (
                id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
                group_id VARCHAR(32) NOT NULL COMMENT '群号',
                content_version INT UNSIGNED NOT NULL COMMENT '对应版本号',
                content MEDIUMTEXT NOT NULL COMMENT '当次文案',
                content_hash CHAR(64) NOT NULL COMMENT '当次文案哈希',
                tags JSON DEFAULT (JSON_ARRAY()) COMMENT '当次标签',
                classification_hints JSON DEFAULT (JSON_OBJECT()) COMMENT '当次分类提示',
                source VARCHAR(64) DEFAULT NULL COMMENT '数据来源',
                batch_id VARCHAR(64) DEFAULT NULL COMMENT '批次ID',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                KEY idx_group_ver (group_id, content_version) COMMENT '群号+版本索引',
                KEY idx_group_time (group_id, created_at) COMMENT '群号+时间索引'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """

            # 执行建表语句
            cursor.execute(create_latest_table_sql)
            cursor.execute(create_history_table_sql)

            print("数据库表创建/检查完成")

    def reset_tables(self):
        """
        重置数据库表（删除并重新创建）
        用于清理测试数据
        """
        with self.get_cursor() as cursor:
            # 删除表（如果存在）
            cursor.execute("DROP TABLE IF EXISTS group_raw_history")
            cursor.execute("DROP TABLE IF EXISTS group_raw_latest")

            print("数据库表已重置，正在重新创建...")
            self.create_tables()
            print("数据库表重置完成")

    def get_group_latest(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        获取群组的最新数据

        Args:
            group_id: 群组ID

        Returns:
            Optional[Dict]: 最新数据，如果不存在则返回None
        """
        with self.get_cursor() as cursor:
            sql = """
            SELECT group_id, content, content_hash, content_version,
                   tags, classification_hints, source, batch_id,
                   first_seen_group, last_seen_group, last_updated_content, seen_count
            FROM group_raw_latest
            WHERE group_id = %s
            """
            cursor.execute(sql, (group_id,))
            result = cursor.fetchone()

            if result:
                return {
                    "group_id": result[0],
                    "content": result[1],
                    "content_hash": result[2],
                    "content_version": result[3],
                    "tags": json.loads(result[4]) if result[4] else [],
                    "classification_hints": json.loads(result[5]) if result[5] else {},
                    "source_meta": {
                        "source": result[6],
                        "batch_id": result[7]
                    },
                    "timestamps": {
                        "first_seen_group": result[8].strftime("%Y-%m-%d %H:%M:%S") if result[8] else None,
                        "last_seen_group": result[9].strftime("%Y-%m-%d %H:%M:%S") if result[9] else None,
                        "last_updated_content": result[10].strftime("%Y-%m-%d %H:%M:%S") if result[10] else None
                    },
                    "seen_count": result[11]
                }

            return None

    def process_group_content(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理群组内容，实现PDF文档中的UPSERT逻辑

        Args:
            group_data: 群组数据

        Returns:
            Dict: 处理结果
        """
        group_id = group_data["group_id"]
        content_hash = group_data["content_hash"]

        with self.get_cursor() as cursor:
            try:
                # 检查群组是否已存在
                existing_data = self.get_group_latest(group_id)

                if existing_data:
                    # 群组已存在，检查内容是否变更
                    if existing_data["content_hash"] == content_hash:
                        # 内容未变，只更新计数和时间
                        sql = """
                        UPDATE group_raw_latest
                        SET last_seen_group = %s, seen_count = seen_count + 1
                        WHERE group_id = %s
                        """
                        cursor.execute(sql, (
                            group_data["timestamps"]["last_seen_group"],
                            group_id
                        ))
                        return {
                            "success": True,
                            "action": "updated_existing",
                            "group_id": group_id,
                            "content_changed": False
                        }
                    else:
                        # 内容已变，版本递增，更新最新表，插入历史表
                        new_version = existing_data["content_version"] + 1

                        # 插入历史记录
                        history_sql = """
                        INSERT INTO group_raw_history
                        (group_id, content_version, content, content_hash, tags,
                         classification_hints, source, batch_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(history_sql, (
                            group_id,
                            existing_data["content_version"],  # 插入当前版本到历史
                            existing_data["content"],
                            existing_data["content_hash"],
                            json.dumps(existing_data["tags"]),
                            json.dumps(existing_data["classification_hints"]),
                            existing_data["source_meta"]["source"],
                            existing_data["source_meta"]["batch_id"]
                        ))

                        # 更新最新表
                        update_sql = """
                        UPDATE group_raw_latest
                        SET content = %s, content_hash = %s, content_version = %s,
                            tags = %s, classification_hints = %s,
                            source = %s, batch_id = %s,
                            last_seen_group = %s, last_updated_content = %s,
                            seen_count = seen_count + 1
                        WHERE group_id = %s
                        """
                        cursor.execute(update_sql, (
                            group_data["content"],
                            group_data["content_hash"],
                            new_version,
                            json.dumps(group_data["tags"]),
                            json.dumps(group_data["classification_hints"]),
                            group_data["source_meta"]["source"],
                            group_data["source_meta"]["batch_id"],
                            group_data["timestamps"]["last_seen_group"],
                            group_data["timestamps"]["last_updated_content"],
                            group_id
                        ))

                        return {
                            "success": True,
                            "action": "updated_with_new_version",
                            "group_id": group_id,
                            "content_changed": True,
                            "new_version": new_version
                        }
                else:
                    # 新群组，插入最新表
                    insert_sql = """
                    INSERT INTO group_raw_latest
                    (group_id, content, content_hash, content_version, tags,
                     classification_hints, source, batch_id,
                     first_seen_group, last_seen_group, last_updated_content, seen_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_sql, (
                        group_data["group_id"],
                        group_data["content"],
                        group_data["content_hash"],
                        group_data["content_version"],
                        json.dumps(group_data["tags"]),
                        json.dumps(group_data["classification_hints"]),
                        group_data["source_meta"]["source"],
                        group_data["source_meta"]["batch_id"],
                        group_data["timestamps"]["first_seen_group"],
                        group_data["timestamps"]["last_seen_group"],
                        group_data["timestamps"]["last_updated_content"],
                        group_data["seen_count"]
                    ))

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
        """
        获取群组的历史记录

        Args:
            group_id: 群组ID
            limit: 最大返回记录数

        Returns:
            List[Dict]: 历史记录列表
        """
        with self.get_cursor() as cursor:
            sql = """
            SELECT id, group_id, content_version, content, content_hash,
                   tags, classification_hints, source, batch_id, created_at
            FROM group_raw_history
            WHERE group_id = %s
            ORDER BY content_version DESC
            LIMIT %s
            """
            cursor.execute(sql, (group_id, limit))
            results = cursor.fetchall()

            history = []
            for result in results:
                history.append({
                    "id": result[0],
                    "group_id": result[1],
                    "content_version": result[2],
                    "content": result[3],
                    "content_hash": result[4],
                    "tags": json.loads(result[5]) if result[5] else [],
                    "classification_hints": json.loads(result[6]) if result[6] else {},
                    "source": result[7],
                    "batch_id": result[8],
                    "created_at": result[9].strftime("%Y-%m-%d %H:%M:%S") if result[9] else None
                })

            return history

    def search_groups(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        全文搜索群组

        Args:
            keyword: 搜索关键词
            limit: 最大返回结果数

        Returns:
            List[Dict]: 搜索结果列表
        """
        with self.get_cursor() as cursor:
            sql = """
            SELECT group_id, content, tags, classification_hints,
                   first_seen_group, last_seen_group, seen_count
            FROM group_raw_latest
            WHERE MATCH(content) AGAINST(%s IN NATURAL LANGUAGE MODE)
            ORDER BY seen_count DESC
            LIMIT %s
            """
            cursor.execute(sql, (keyword, limit))
            results = cursor.fetchall()

            search_results = []
            for result in results:
                search_results.append({
                    "group_id": result[0],
                    "content": result[1],
                    "tags": json.loads(result[2]) if result[2] else [],
                    "classification_hints": json.loads(result[3]) if result[3] else {},
                    "first_seen_group": result[4].strftime("%Y-%m-%d %H:%M:%S") if result[4] else None,
                    "last_seen_group": result[5].strftime("%Y-%m-%d %H:%M:%S") if result[5] else None,
                    "seen_count": result[6]
                })

            return search_results

    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            Dict: 统计信息
        """
        with self.get_cursor() as cursor:
            # 最新表统计
            cursor.execute("SELECT COUNT(*) FROM group_raw_latest")
            latest_count = cursor.fetchone()[0]

            # 历史表统计
            cursor.execute("SELECT COUNT(*) FROM group_raw_history")
            history_count = cursor.fetchone()[0]

            # 总看到次数
            cursor.execute("SELECT SUM(seen_count) FROM group_raw_latest")
            total_seen = cursor.fetchone()[0] or 0

            # 群组类型统计
            cursor.execute("""
            SELECT
                JSON_UNQUOTE(JSON_EXTRACT(classification_hints, '$.group_type')) as group_type,
                COUNT(*) as count
            FROM group_raw_latest
            WHERE JSON_EXTRACT(classification_hints, '$.group_type') IS NOT NULL
            GROUP BY JSON_EXTRACT(classification_hints, '$.group_type')
            """)
            type_stats = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "total_groups": latest_count,
                "total_history_records": history_count,
                "total_seen_count": total_seen,
                "group_type_stats": type_stats
            }

    def _query_recent_groups(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        查询最近活跃的群组

        Args:
            limit: 返回的群组数量限制

        Returns:
            List[Dict]: 最近活跃的群组列表
        """
        with self.get_cursor() as cursor:
            sql = """
            SELECT group_id, last_seen_group, seen_count, classification_hints
            FROM group_raw_latest
            ORDER BY last_seen_group DESC
            LIMIT %s
            """
            cursor.execute(sql, (limit,))
            results = cursor.fetchall()

            recent_groups = []
            for result in results:
                recent_groups.append({
                    "group_id": result[0],
                    "last_seen_group": result[1].strftime("%Y-%m-%d %H:%M:%S") if result[1] else None,
                    "seen_count": result[2],
                    "classification_hints": json.loads(result[3]) if result[3] else {}
                })

            return recent_groups


# 测试函数
if __name__ == "__main__":
    # 测试数据库连接和基本操作
    try:
        db = MySQLDatabase()
        db.create_tables()
        print("数据库初始化成功")

        # 获取统计信息
        stats = db.get_stats()
        print(f"数据库统计: {stats}")

        db.disconnect()
        print("数据库连接已关闭")

    except Exception as e:
        print(f"数据库测试失败: {e}")
