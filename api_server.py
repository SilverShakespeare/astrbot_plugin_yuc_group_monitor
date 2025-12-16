#!/usr/bin/env python3
"""
语C群宣监听插件 - API服务器

项目: 语C群宣监听插件
作者: 银莎Silver Shakespeare
版本: 1.0.0
完成日期: 2025/12/16

提供数据查询接口，支持完整的筛选、排序和分页功能。
"""

import sys
import os
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from database_factory import get_database
except ImportError:
    import database_factory
    get_database = database_factory.get_database

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化数据库连接
db = None

def get_db():
    """获取数据库实例（单例模式）"""
    global db
    if db is None:
        db = get_database()
    return db

# API路由

@app.route('/api/stats')
def api_stats():
    """获取统计信息"""
    try:
        database = get_db()
        stats = database.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/recent-groups')
def api_recent_groups():
    """获取最近活跃的群组"""
    try:
        database = get_db()
        recent_groups = database._query_recent_groups(10)
        return jsonify(recent_groups)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/group/<group_id>')
def api_group_detail(group_id):
    """获取群组详细信息"""
    try:
        database = get_db()
        data = database.get_group_latest(group_id)
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": f"未找到群组 {group_id}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search')
def api_search():
    """搜索群组"""
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 20))

        database = get_db()
        results = database.search_groups(query, limit)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/groups')
def api_groups():
    """获取群组列表（支持筛选、排序、分页）"""
    try:
        # 分页参数
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page

        # 筛选参数
        group_id_filter = request.args.get('group_id', '').strip()
        group_type_filter = request.args.get('group_type', '').strip()
        worldview_filter = request.args.get('worldview', '').strip()
        has_sexual_content = request.args.get('has_sexual_content', '').strip()
        no_audit_setting = request.args.get('no_audit_no_setting', '').strip()


        # 排序参数
        sort_by = request.args.get('sort_by', 'last_seen_group')  # first_seen_group 或 last_seen_group
        sort_order = request.args.get('sort_order', 'desc')  # asc 或 desc

        database = get_db()

        # 构建SQL查询
        conditions = []
        params = []

        if group_id_filter:
            conditions.append("group_id LIKE %s")
            params.append(f"%{group_id_filter}%")

        if group_type_filter:
            conditions.append("JSON_UNQUOTE(JSON_EXTRACT(classification_hints, '$.group_type')) = %s")
            params.append(group_type_filter)

        if worldview_filter:
            conditions.append("JSON_UNQUOTE(JSON_EXTRACT(classification_hints, '$.worldview')) = %s")
            params.append(worldview_filter)

        if has_sexual_content in ['true', 'false']:
            conditions.append("JSON_UNQUOTE(JSON_EXTRACT(classification_hints, '$.has_sexual_content')) = %s")
            params.append('true' if has_sexual_content == 'true' else 'false')

        if no_audit_setting in ['true', 'false']:
            conditions.append("JSON_UNQUOTE(JSON_EXTRACT(classification_hints, '$.no_audit_no_setting')) = %s")
            params.append('true' if no_audit_setting == 'true' else 'false')

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 排序
        if sort_by not in ['first_seen_group', 'last_seen_group']:
            sort_by = 'last_seen_group'
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'

        order_clause = f"{sort_by} {sort_order.upper()}"

        # 查询数据
        sql = f"""
        SELECT group_id, content, tags, classification_hints,
               first_seen_group, last_seen_group, seen_count
        FROM group_raw_latest
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])

        # 调试输出
        print(f"DEBUG SQL: {sql}")
        print(f"DEBUG Params: {params}")
        print(f"DEBUG Where: {where_clause}")


        cursor = database.connection.cursor()
        cursor.execute(sql, params)
        results = cursor.fetchall()

        groups = []
        for result in results:
            groups.append({
                "group_id": result[0],
                "content": result[1],
                "tags": json.loads(result[2]) if result[2] else [],
                "classification_hints": json.loads(result[3]) if result[3] else {},
                "first_seen_group": result[4].strftime("%Y-%m-%d %H:%M:%S") if result[4] else None,
                "last_seen_group": result[5].strftime("%Y-%m-%d %H:%M:%S") if result[5] else None,
                "seen_count": result[6]
            })

        # 查询总数
        count_sql = f"SELECT COUNT(*) FROM group_raw_latest WHERE {where_clause}"
        cursor.execute(count_sql, params[:-2])  # 去掉LIMIT和OFFSET参数
        total_count = cursor.fetchone()[0]

        cursor.close()

        # 调试输出到响应
        debug_info = {
            "sql": sql,
            "params": params,
            "where_clause": where_clause,
            "conditions": conditions,
            "total_count": total_count
        }

        return jsonify({
            "groups": groups,
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page,
            "debug": debug_info
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history/<group_id>')
def api_group_history(group_id):
    """获取群组历史记录"""
    try:
        limit = int(request.args.get('limit', 10))
        database = get_db()
        history = database.get_group_history(group_id, limit)
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("启动API服务器...")
    print("API接口启动成功")
    # 在Windows上禁用调试模式以避免连接问题
    import platform
    if platform.system() == 'Windows':
        app.run(host='127.0.0.1', port=5000, debug=False)
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)
