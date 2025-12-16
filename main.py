"""
语C群宣监听插件 - QQ群组消息监听与数据处理系统

项目: 语C群宣监听插件
作者: 银莎Silver Shakespeare
版本: 1.0.0
完成日期: 2025/12/16

功能说明:
- 监听指定QQ群组中的消息
- 从消息文本中提取群号并生成完整的数据结构
- 实现内容清洗、分类和版本管理
- 支持MySQL数据库存储，支持本地JSON降级

配置说明:
- 可在config.py中配置DATABASE_TYPE选择数据库类型
- 可在config.py中配置DB_CONFIG进行MySQL连接设置
- 可在config.py中配置SYSTEM_PARAMS["listen_qq_groups"]指定监听群组
"""

import re
import asyncio
from datetime import datetime
import json
from typing import List, Optional

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

from .database_factory import get_database
from .message_processor import process_message, update_processed_data
from .config import SYSTEM_PARAMS

# 配置加载状态标志
config_loaded = False
# 目标群组ID列表
target_group_ids = []

try:
    target_group_ids = SYSTEM_PARAMS.get("listen_qq_groups", [])
    config_loaded = True
except ImportError:
    target_group_ids = []
    config_loaded = False

@register("语C群宣监听插件", "银莎Silver Shakespeare", "监听并存储QQ群消息", "1.0.0")
class GroupListener(Star):
    """
    QQ群组监听插件主类

    功能概述:
    - 监听并处理指定QQ群组中的消息
    - 生成完整的数据结构
    - 实现群号提取、内容清洗、分类和版本管理
    - 支持MySQL数据库存储和本地JSON降级

    属性:
        target_group_ids: 需要监听的群组ID列表，为空则监听所有群组
        db: 数据库实例
    """

    def __init__(self, context: Context):
        """
        初始化插件

        Args:
            context: AstrBot上下文对象
        """
        super().__init__(context)

        logger.info("=== QQ群组监听插件 (PDF文档实现) 加载开始 ===")

        # 初始化数据库
        try:
            self.db = get_database()
            logger.info("数据库初始化成功")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

        # 设置目标群组
        self.target_group_ids: List[str] = target_group_ids

        if self.target_group_ids:
            logger.info(f"配置了监听群组: {self.target_group_ids}")
        else:
            logger.info("未配置特定监听群组，将监听所有群组消息")

        logger.info("插件初始化完成，等待消息处理")

    def should_process_message(self, event: AstrMessageEvent) -> bool:
        """
        判断是否应该处理该消息

        过滤逻辑:
        - 非群组消息直接忽略
        - 如果配置了目标群组列表，只处理列表中的群组消息
        - 如果未配置目标群组列表，处理所有群组消息

        Args:
            event: AstrMessageEvent消息事件对象

        Returns:
            bool: True表示应该处理该消息，False表示忽略
        """
        group_id = event.get_group_id()

        # 非群组消息直接返回False
        if not group_id:
            return False

        # 如果配置了目标群组列表，检查当前群组是否在列表中
        if self.target_group_ids and str(group_id) not in self.target_group_ids:
            return False

        return True

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent, *args, **kwargs):
        """
        处理所有类型的消息事件

        处理流程:
        1. 检查是否应该处理该消息（群组过滤）
        2. 从消息中提取并处理群组数据
        3. 将处理后的数据存储到数据库
        4. 记录处理结果

        Args:
            event: AstrMessageEvent消息事件对象
            *args: 额外参数
            **kwargs: 额外关键字参数
        """
        should_process = self.should_process_message(event)

        if not should_process:
            return

        message_content = event.get_message_outline()
        source_group_id = event.get_group_id()

        if not message_content:
            return

        try:
            logger.info(f"接收到来自群组 {source_group_id} 的消息，开始处理")

            # 处理消息，生成数据结构
            processed_data = process_message(
                message_text=message_content,
                source_group_id=str(source_group_id),
                source=f"qq_group_{source_group_id}"
            )

            if not processed_data:
                logger.debug("消息中未找到有效的群号，跳过处理")
                return

            group_id = processed_data["group_id"]
            logger.info(f"从消息中提取到群号: {group_id}")

            # 存储到数据库
            result = self.db.process_group_content(processed_data)

            if result["success"]:
                action = result["action"]
                content_changed = result.get("content_changed", False)

                logger.info(f"群号 {group_id} 处理成功")
                logger.info(f"  操作类型: {action}")
                logger.info(f"  内容是否变更: {content_changed}")

                if content_changed:
                    version = result.get("new_version") or result.get("version", 1)
                    logger.info(f"  当前版本: {version}")

                logger.info(f"  群组类型: {processed_data['classification_hints'].get('group_type', '未知')}")
                logger.info(f"  世界观: {processed_data['classification_hints'].get('worldview', '未知')}")
                logger.info(f"  标签: {processed_data['tags']}")

                # 如果是开发环境，可以打印完整数据结构
                if SYSTEM_PARAMS.get("enable_debug_logging", False):
                    logger.debug(f"完整数据结构: {json.dumps(processed_data, ensure_ascii=False, indent=2)}")

            else:
                logger.error(f"群号 {group_id} 处理失败: {result.get('error')}")

        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}")
            import traceback
            logger.error(f"详细错误信息:\n{traceback.format_exc()}")

    def get_plugin_stats(self) -> dict:
        """
        获取插件统计信息

        Returns:
            dict: 统计信息
        """
        try:
            db_stats = self.db.get_stats()
            return {
                "plugin_status": "running",
                "target_groups": self.target_group_ids,
                "database_stats": db_stats
            }
        except Exception as e:
            return {
                "plugin_status": "error",
                "error": str(e)
            }

    def reset_database(self) -> bool:
        """
        重置数据库（清理所有数据并重新创建表）

        Returns:
            bool: 重置是否成功
        """
        try:
            self.db.reset_tables()
            logger.info("数据库重置完成")
            return True
        except Exception as e:
            logger.error(f"数据库重置失败: {e}")
            return False