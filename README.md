# 语C群宣监听插件

项目: 语C群宣监听插件
作者: 银莎Silver Shakespeare
版本: 1.0.0
完成日期: 2025/12/16

基于数据处理系统，用于监听QQ群消息并按照指定数据结构进行处理和存储。

## 功能特性

- **消息监听**: 监听指定QQ群组中的消息
- **智能提取**: 从消息文本中自动提取群号
- **内容清洗**: 移除@、引用等干扰元素，保留换行符
- **智能分类**: 基于关键词自动分类群组类型和世界观
- **标签提取**: 提取#标签和基于内容的标签
- **版本管理**: 自动检测内容变更并管理版本
- **数据存储**: 支持MySQL数据库存储，支持本地JSON降级
- **API接口**: 提供完整的REST API接口进行数据查询

## 数据结构

每个处理的群组数据包含以下完整结构：

```json
{
  "group_id": "1016105893",
  "content": "清洗后的完整文案...",
  "content_hash": "sha256-of-content",
  "content_version": 3,
  "tags": ["可三视", "PVE"],
  "classification_hints": {
    "group_type": "演绎群",
    "worldview": "现玄",
    "has_sexual_content": false,
    "no_audit_no_setting": false
  },
  "timestamps": {
    "first_seen_group": "2025-12-16 10:35:25",
    "last_seen_group": "2025-12-16 10:50:10",
    "last_updated_content": "2025-12-16 10:48:02"
  },
  "source_meta": {
    "source": "qq_monitor_plugin",
    "batch_id": "uuid"
  },
  "seen_count": 4
}
```

## 安装和配置

### 1. 环境要求

- Python 3.7+
- MySQL 8.0+ (推荐)
- AstrBot框架

### 2. 数据库配置

编辑 `config.py` 文件中的数据库连接信息：

```python
# 使用远程MySQL数据库
DATABASE_TYPE = "mysql"
DB_CONFIG = {
    "host": "your_mysql_host",
    "port": 3306,
    "user": "your_username",
    "password": "your_password",
    "database": "your_database",
    "charset": "utf8mb4",
    "autocommit": True
}
```

### 3. 初始化数据库

运行数据库初始化脚本：

```bash
# 初始化数据库表
python setup_database.py init

# 重置数据库（清除所有数据）
python setup_database.py reset --force

# 查看数据库统计
python setup_database.py stats

# 测试数据库连接
python setup_database.py test
```

### 4. 配置监听群组

在 `config.py` 中设置要监听的群组：

```python
SYSTEM_PARAMS = {
    "listen_qq_groups": ["群号1", "群号2"],  # 为空则监听所有群组
    "enable_debug_logging": True  # 启用详细日志
}
```

## 使用方法

### 启动插件

将插件目录放置到 AstrBot 的 plugins 目录下：

```
astrbot/data/plugins/astrbot_plugin_yuc_group_monitor/
```

重启 AstrBot 即可自动加载插件。

### 关键词配置

插件内置了丰富的关键词配置，支持以下分类：

- **垃圾群关键词**: 占卜、白嫖、塔罗等
- **交流群关键词**: 宣市、扩列、群宣等
- **演绎群关键词**: 演绎、语C、角色扮演等
- **世界观关键词**: 现原、古原、西幻、科幻等
- **审核关键词**: 审核、人设、无审无设等
- **性相关关键词**: 全性向、BLC、ABO、R18等

可在 `config.py` 的 `KEYWORDS` 配置中自定义关键词。

## 代码文件结构

### 核心文件

| 文件 | 说明 |
|------|------|
| `main.py` | 主插件文件，负责消息监听和处理调度 |
| `message_processor.py` | 消息处理器，负责内容清洗、分类和数据结构生成 |
| `config.py` | 配置文件，包含数据库配置和关键词设置 |
| `database_factory.py` | 数据库工厂，根据配置选择MySQL或本地JSON存储 |
| `mysql_database.py` | MySQL数据库操作实现 |
| `local_database.py` | 本地JSON数据库操作实现 |

### 工具文件

| 文件 | 说明 |
|------|------|
| `setup_database.py` | 数据库初始化和管理工具 |
| `check_data.py` | 数据查询和检查工具 |
| `api_server.py` | REST API服务器（可选） |

### 项目文件

| 文件 | 说明 |
|------|------|
| `README.md` | 项目说明文档 |
| `__init__.py` | Python包初始化文件 |

## Docker部署配置

### 1. 创建Docker网络

```bash
docker network create qq-monitor-net
```

### 2. 启动NapCat容器

```bash
docker run -d --name napcat \
  --network qq-monitor-net \
  -p 6099:6099 \
  --restart=always \
  mlikiowa/napcat-docker:latest
```

### 3. 启动AstrBot容器

```bash
docker run -itd --name astrbot \
  --network qq-monitor-net \
  --restart=always \
  -p 6185:6185 \
  -p 5000:5000 \
  -v $PWD/astrbot/data:/AstrBot/data \
  soulter/astrbot:latest
```

### 4. NapCat WebSocket配置

在NapCat Web管理界面中配置WebSocket连接：

1. 访问 NapCat Web管理界面：`http://localhost:6099`
2. 在"正向WebSocket"配置中设置：
   - **启用**: 开启
   - **WebSocket地址**: `ws://astrbot:6180` (使用容器名)
   - **端口**: 留空
   - **令牌**: 留空（或设置一致的令牌）

### 5. AstrBot配置

在AstrBot配置中添加NapCat平台：

```yaml
# AstrBot配置文件 (data/config/bot_config.yaml)
platform:
  - name: "napcat"
    type: "napcat"
    host: "napcat"  # 使用容器名
    port: 6099      # NapCat端口
    token: ""       # 如果设置了令牌
    reconnect: true
```

## NapCat配置详解

### 容器环境配置

在Docker容器环境中，NapCat和AstrBot通过Docker网络通信：

#### AstrBot平台配置

在AstrBot启动的WebUI中的 机器人 栏创建机器人，填写反向 Websocket 端口 (默认6199) 供NapCat连接

#### NapCat WebSocket设置

在NapCat启动的WebUI中的 网络配置 栏新建 WebSocket客户端 配置，URL设置为 ws://astrbot:6199/ws

### 本地开发环境配置

如果在本地开发环境运行：

#### NapCat本地配置

1. **下载并安装NapCat**:
```bash
# 从GitHub下载NapCat
git clone https://github.com/NapNeko/NapCatQQ.git
cd NapCatQQ
# 按照官方文档安装
```

2. **配置文件位置**:
   - Windows: `%USERPROFILE%\.config\napcat\config.yml`
   - Linux: `~/.config/napcat/config.yml`

3. **配置文件内容**:
```yaml
# NapCat配置文件示例
ws:
  host: "127.0.0.1"
  port: 6099
  enable: true
  enableHttp: false

# 消息上报到AstrBot
report:
  enable: true
  url: "http://127.0.0.1:6185"  # AstrBot地址
  token: ""

heartbeat:
  enable: true
  interval: 30000
```

#### AstrBot本地配置

```yaml
# AstrBot配置文件
platform:
  - name: "napcat"
    type: "napcat"
    host: "127.0.0.1"  # 本地NapCat
    port: 6099
    token: ""
    reconnect: true
```

### 测试连接

1. **启动NapCat**:
```bash
# Docker环境
docker start napcat
```

2. **启动AstrBot**:
```bash
# Docker环境
docker start astrbot
```

3. **检查日志**:
   - NapCat日志: `docker logs napcat`
   - AstrBot日志: `docker logs astrbot`

## 命令行工具

```bash
# 查看统计信息
python check_data.py stats

# 查看特定群组详情
python check_data.py show 群号

# 搜索内容
python check_data.py search 关键词
```

## API接口（可选）

如果需要通过编程方式访问数据，可以启动API服务器：

### 启动API服务器

```bash
# 启动API服务器
python api_server.py

# 服务器将在 http://localhost:5000 提供API接口
# 按 Ctrl+C 停止服务器
```

### API接口文档

API服务器提供REST API接口，支持完整的筛选、排序和分页功能：

#### 基础接口

**获取统计信息**
```
GET /api/stats
```
返回数据库统计信息，包括总群组数、历史记录数等。

**获取最近活跃群组**
```
GET /api/recent-groups
```
返回最近10个活跃的群组列表。

#### 群组查询接口

**获取群组列表（核心接口）**
```
GET /api/groups
```
支持完整的筛选、排序和分页功能。

**筛选参数:**
- `group_id={关键词}` - 群号模糊搜索（如：`870153` 匹配包含此数字的群号）
- `group_type={类型}` - 群类型筛选
  - 可选值：`演绎群`、`交流群`、`垃圾群`
- `worldview={世界观}` - 世界观筛选
  - 可选值：`现原`、`古原`、`现玄`、`古玄`、`西幻`、`科幻`、`同人`
- `has_sexual_content=true/false` - 是否包含性内容
  - `true` - 只显示包含性内容的群组
  - `false` - 只显示不包含性内容的群组
  - 不传此参数 - 显示所有群组
- `no_audit_no_setting=true/false` - 是否无审无设
  - `true` - 只显示无审无设的群组
  - `false` - 只显示有审有设的群组
  - 不传此参数 - 显示所有群组

**排序参数:**
- `sort_by={字段}` - 排序字段
  - `last_seen_group` - 按最后活跃时间排序（默认）
  - `first_seen_group` - 按首次发现时间排序
- `sort_order={方向}` - 排序方向
  - `desc` - 降序（默认，从新到旧）
  - `asc` - 升序（从旧到新）

**分页参数:**
- `page={页码}` - 页码（从1开始，默认：1）
- `per_page={每页条数}` - 每页显示条数（默认：10，可选：10/20/50）

#### 其他接口

**获取特定群组详情**
```
GET /api/group/{group_id}
```
返回指定群组的完整详细信息。

**搜索群组（关键词搜索）**
```
GET /api/search?q={关键词}&limit={条数}
```
在群组内容中进行全文搜索。

**获取群组历史记录**
```
GET /api/history/{group_id}?limit={条数}
```
返回指定群组的历史版本记录。

#### API使用示例

**1. 获取所有演绎群，按最后活跃时间降序排列：**
```
/api/groups?group_type=演绎群&sort_by=last_seen_group&sort_order=desc&page=1&per_page=20
```

**2. 搜索群号包含"870"的群组：**
```
/api/groups?group_id=870&page=1&per_page=10
```

**3. 获取西幻世界观且不包含性内容的群组：**
```
/api/groups?worldview=西幻&has_sexual_content=false&page=1&per_page=15
```

**4. 获取按首次发现时间升序排列的群组（最老的在前）：**
```
/api/groups?sort_by=first_seen_group&sort_order=asc&page=1&per_page=25
```

**5. 组合筛选：演绎群+现原世界观+无审无设+每页50条：**
```
/api/groups?group_type=演绎群&worldview=现原&no_audit_no_setting=true&page=1&per_page=50
```

#### 响应格式

所有API返回JSON格式数据：

```json
{
  "groups": [
    {
      "group_id": "870153565",
      "content": "群宣传内容...",
      "tags": ["标签1", "标签2"],
      "classification_hints": {
        "group_type": "演绎群",
        "worldview": "现原",
        "has_sexual_content": false,
        "no_audit_no_setting": false
      },
      "first_seen_group": "2025-12-16 06:32:54",
      "last_seen_group": "2025-12-16 06:46:20",
      "seen_count": 2
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 10,
  "total_pages": 15
}
```

#### 错误处理

API返回标准HTTP状态码：
- `200` - 成功
- `404` - 群组不存在
- `500` - 服务器错误

错误响应格式：
```json
{
  "error": "错误描述信息"
}
```

## 数据库表结构

### group_raw_latest (最新数据表)

存储每个群组的最新信息，支持全文搜索。

```sql
CREATE TABLE group_raw_latest (
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
```

### group_raw_history (历史数据表)

记录每次内容变更的历史版本。

```sql
CREATE TABLE group_raw_history (
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
```

## 注意事项

1. **数据库连接**: 确保MySQL数据库可访问，连接失败将自动降级到本地JSON存储
2. **性能考虑**: 大量消息处理时注意数据库性能，可调整批量处理大小
3. **数据清理**: 使用 `setup_database.py reset` 可清理测试数据
4. **字符编码**: 数据库使用utf8mb4编码，支持中文和特殊字符

## 故障排除

### 数据库连接失败
- 检查MySQL服务是否运行
- 验证连接参数是否正确
- 确认用户权限是否足够

### 消息处理失败
- 检查消息格式是否符合预期
- 查看日志中的错误信息
- 确认关键词配置是否正确

### 性能问题
- 启用数据库索引
- 调整批量处理参数
- 监控数据库查询性能

## 许可证

本项目遵循相关开源许可证。
