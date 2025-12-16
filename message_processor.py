"""
语C群宣监听插件 - 消息处理器

项目: 语C群宣监听插件
作者: 银莎Silver Shakespeare
版本: 1.0.0
完成日期: 2025/12/16

消息处理模块，包含群组消息处理、内容哈希、版本管理和数据结构生成等功能。
"""

import re
import hashlib
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
import uuid

try:
    from .config import KEYWORDS
except ImportError:
    try:
        from config import KEYWORDS
    except ImportError:
        import config
        KEYWORDS = config.KEYWORDS

class MessageProcessor:
    """
    消息处理器 - 负责群组内容处理、哈希计算和数据结构生成
    """

    def __init__(self):
        """
        初始化消息处理器
        """
        self.keywords_config = KEYWORDS

    def extract_group_id_from_message(self, message_text: str) -> Optional[str]:
        """
        从消息文本中提取群号（第一个5-11位数字字符串）

        Args:
            message_text: 消息文本

        Returns:
            Optional[str]: 提取到的群号，如果未找到则返回None
        """
        if not message_text or not isinstance(message_text, str):
            return None

        # 正则表达式：匹配5-11位数字，边界不能是其他数字
        # (?<!\d) 确保前面不是数字，(?!\d) 确保后面不是数字
        qq_pattern = r'(?<!\d)\d{5,11}(?!\d)'

        # 查找所有匹配的数字
        matches = re.findall(qq_pattern, message_text)

        # 返回第一个匹配的数字作为群号
        if matches:
            return matches[0]

        return None

    def clean_content_text(self, raw_text: str) -> str:
        """
        清洗内容文本，移除干扰格式并标准化
        保留消息内的换行符

        Args:
            raw_text: 原始文本内容

        Returns:
            str: 清洗后的标准化文本
        """
        if not raw_text:
            return ""

        # 移除所有[At:...]格式
        cleaned_text = re.sub(r'\[At:[^\]]*\]', '', raw_text)

        # 移除所有@格式: @用户名 或 @QQ号
        cleaned_text = re.sub(r'@\S+\s*', '', cleaned_text)

        # 移除引用消息格式
        cleaned_text = re.sub(r'\[引用消息\(.*?\)\]', '', cleaned_text)

        # 移除多余的空白字符和空行
        # 将多个连续换行符替换为双换行符（保留段落结构）
        cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)

        # 移除每行前后的空白字符
        lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
        cleaned_text = '\n'.join(lines)

        return cleaned_text.strip()

    def extract_manual_tags(self, content: str) -> List[str]:
        """
        从内容中提取手动标记的标签（使用规范的"#"符号）

        Args:
            content: 清洗后的内容文本

        Returns:
            List[str]: 提取到的标签列表
        """
        tags = []

        # 匹配 #标签 格式的标签
        # 支持中文、英文、数字和下划线
        tag_pattern = r'#([\u4e00-\u9fa5a-zA-Z0-9_]+)'

        matches = re.findall(tag_pattern, content)
        if matches:
            tags.extend(matches)

        return list(set(tags))  # 去重

    def classify_group_type(self, content: str) -> Optional[str]:
        """
        基于关键词分类群组类型

        Args:
            content: 清洗后的内容文本

        Returns:
            Optional[str]: 群组类型，可能的值："演绎群", "交流群", "垃圾群", 或 None
        """
        content_lower = content.lower()

        # 检查是否为垃圾群
        for keyword in self.keywords_config.get("spam_groups", []):
            if keyword in content:
                return "垃圾群"

        # 检查是否为交流群
        for keyword in self.keywords_config.get("exchange_groups", []):
            if keyword in content:
                return "交流群"

        # 检查是否为演绎群
        for keyword in self.keywords_config.get("deduction_groups", []):
            if keyword in content:
                return "演绎群"

        return None

    def classify_worldview(self, content: str) -> Optional[str]:
        """
        基于关键词分类世界观

        Args:
            content: 清洗后的内容文本

        Returns:
            Optional[str]: 世界观类型，可能的值："现玄", "西幻", "古玄", "古原", "现原", "同人", "科幻", 或 None
        """
        content_lower = content.lower()

        # 世界观映射
        worldview_mapping = {
            "现玄": self.keywords_config.get("worldview_modern_fantasy", []),
            "古玄": self.keywords_config.get("worldview_ancient_fantasy", []),
            "西幻": self.keywords_config.get("worldview_western_fantasy", []),
            "古原": self.keywords_config.get("worldview_ancient_original", []),
            "现原": self.keywords_config.get("worldview_modern_original", []),
            "同人": self.keywords_config.get("worldview_tongren", []),
            "科幻": self.keywords_config.get("worldview_sci_fi", [])
        }

        # 按优先级检查世界观关键词
        for worldview, keywords in worldview_mapping.items():
            for keyword in keywords:
                if keyword in content:
                    return worldview

        return None

    def check_sexual_content(self, content: str) -> bool:
        """
        检查是否提及性相关内容

        Args:
            content: 清洗后的内容文本

        Returns:
            bool: 是否包含性相关内容
        """
        sexual_keywords = self.keywords_config.get("sexual_content", [])
        for keyword in sexual_keywords:
            if keyword in content:
                return True
        return False

    def check_no_audit_setting(self, content: str) -> bool:
        """
        检查是否提及无审无设表达

        Args:
            content: 清洗后的内容文本

        Returns:
            bool: 是否包含无审无设表达
        """
        no_audit_keywords = self.keywords_config.get("no_audit_expressions", [])
        for keyword in no_audit_keywords:
            if keyword in content:
                return True
        return False

    def generate_content_hash(self, content: str) -> str:
        """
        生成内容的SHA256哈希

        Args:
            content: 内容文本

        Returns:
            str: SHA256哈希字符串
        """
        if not content:
            return ""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def generate_batch_id(self) -> str:
        """
        生成批次ID

        Returns:
            str: UUID字符串
        """
        return str(uuid.uuid4())

    def process_message(self, message_text: str, source_group_id: str = None,
                       source: str = "qq_monitor_plugin") -> Optional[Dict[str, Any]]:
        """
        处理消息并生成完整的数据结构

        Args:
            message_text: 原始消息文本
            source_group_id: 消息来源群组ID
            source: 数据来源标识

        Returns:
            Optional[Dict]: 处理后的数据结构，如果无法提取群号则返回None
        """
        try:
            # 1. 提取群号
            group_id = self.extract_group_id_from_message(message_text)
            if not group_id:
                return None

            # 2. 清洗内容
            content = self.clean_content_text(message_text)

            # 3. 生成内容哈希
            content_hash = self.generate_content_hash(content)

            # 4. 提取手动标签
            tags = self.extract_manual_tags(content)

            # 5. 进行分类
            group_type = self.classify_group_type(content)
            worldview = self.classify_worldview(content)
            has_sexual_content = self.check_sexual_content(content)
            no_audit_no_setting = self.check_no_audit_setting(content)

            # 6. 生成时间戳
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 7. 生成批次ID
            batch_id = self.generate_batch_id()

            # 8. 构建完整数据结构
            processed_data = {
                "group_id": group_id,
                "content": content,
                "content_hash": content_hash,
                "content_version": 1,  # 初始版本，数据库中会管理版本号
                "tags": tags,
                "classification_hints": {
                    "group_type": group_type,
                    "worldview": worldview,
                    "has_sexual_content": has_sexual_content,
                    "no_audit_no_setting": no_audit_no_setting
                },
                "timestamps": {
                    "first_seen_group": current_time,  # 初始时间，数据库中会管理
                    "last_seen_group": current_time,
                    "last_updated_content": current_time
                },
                "source_meta": {
                    "source": source,
                    "batch_id": batch_id
                },
                "seen_count": 1  # 初始计数，数据库中会管理
            }

            return processed_data

        except Exception as e:
            print(f"处理消息时发生错误: {e}")
            return None

    def update_processed_data(self, existing_data: Dict[str, Any],
                            new_message_text: str, source: str = "qq_monitor_plugin") -> Dict[str, Any]:
        """
        更新已存在的群组数据（处理重复消息）

        Args:
            existing_data: 已存在的群组数据
            new_message_text: 新的消息文本
            source: 数据来源标识

        Returns:
            Dict: 更新后的数据结构
        """
        try:
            # 清洗新内容
            new_content = self.clean_content_text(new_message_text)
            new_content_hash = self.generate_content_hash(new_content)

            # 复制现有数据
            updated_data = existing_data.copy()

            # 更新时间戳
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_data["timestamps"]["last_seen_group"] = current_time

            # 检查内容是否变更
            if new_content_hash != existing_data.get("content_hash"):
                # 内容已变更
                updated_data["content"] = new_content
                updated_data["content_hash"] = new_content_hash
                updated_data["content_version"] = existing_data.get("content_version", 1) + 1
                updated_data["timestamps"]["last_updated_content"] = current_time

                # 重新提取标签
                updated_data["tags"] = self.extract_manual_tags(new_content)

                # 重新分类
                updated_data["classification_hints"]["group_type"] = self.classify_group_type(new_content)
                updated_data["classification_hints"]["worldview"] = self.classify_worldview(new_content)
                updated_data["classification_hints"]["has_sexual_content"] = self.check_sexual_content(new_content)
                updated_data["classification_hints"]["no_audit_no_setting"] = self.check_no_audit_setting(new_content)

            # 更新计数
            updated_data["seen_count"] = existing_data.get("seen_count", 0) + 1

            # 更新来源信息
            updated_data["source_meta"]["source"] = source
            updated_data["source_meta"]["batch_id"] = self.generate_batch_id()

            return updated_data

        except Exception as e:
            print(f"更新数据时发生错误: {e}")
            return existing_data


# 便捷函数
def process_message(message_text: str, source_group_id: str = None,
                   source: str = "qq_monitor_plugin") -> Optional[Dict[str, Any]]:
    """
    处理消息的便捷函数

    Args:
        message_text: 原始消息文本
        source_group_id: 消息来源群组ID
        source: 数据来源标识

    Returns:
        Optional[Dict]: 处理后的数据结构
    """
    processor = MessageProcessor()
    return processor.process_message(message_text, source_group_id, source)


def update_processed_data(existing_data: Dict[str, Any], new_message_text: str,
                         source: str = "qq_monitor_plugin") -> Dict[str, Any]:
    """
    更新已存在数据的便捷函数

    Args:
        existing_data: 已存在的群组数据
        new_message_text: 新的消息文本
        source: 数据来源标识

    Returns:
        Dict: 更新后的数据结构
    """
    processor = MessageProcessor()
    return processor.update_processed_data(existing_data, new_message_text, source)


# 测试函数
if __name__ == "__main__":
    # 测试消息处理
    test_message = """
    查。半封回信
    tag:#现原豪门  #世家恋爱  #全员固设、半固  #1v1向  #皮相制  #全性向  #月KPI
    情长纸短，不尽依依。
    京市应当是没有夜晚的，白昼由炽烈的太阳主宰，而当余晖落入西山，接替它的不是清冷月色，霓虹代替了星辰。
    考核方式:
    考核①：两篇同性别戏录滤白（卡头）
    考核②：找对应皮妈聊皮
    考核③：半固：补全小传 全固：皮析/贴皮200+
    考核④:考核期为48h，支持续2小时。
    按序进行 支持竞皮（三人锁皮） 支持续杯/换皮考核两次。
    暂书至此，不复一一
    邀请函:1075496791
    """

    processor = MessageProcessor()
    result = processor.process_message(test_message)

    if result:
        print("处理结果:")
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("无法处理消息")
