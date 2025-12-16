"""
语C群宣监听插件 - 数据库工厂模块

项目: 语C群宣监听插件
作者: 银莎Silver Shakespeare
版本: 1.0.0
完成日期: 2025/12/16

数据库工厂模块，根据配置选择使用MySQL数据库或本地JSON数据库。
"""

try:
    from .config import DATABASE_TYPE
    from .mysql_database import MySQLDatabase
    from .local_database import LocalDatabase
except ImportError:
    try:
        from config import DATABASE_TYPE
        from mysql_database import MySQLDatabase
        from local_database import LocalDatabase
    except ImportError:
        # 如果都在同一目录下
        import config
        import mysql_database
        import local_database
        DATABASE_TYPE = config.DATABASE_TYPE
        MySQLDatabase = mysql_database.MySQLDatabase
        LocalDatabase = local_database.LocalDatabase

class DatabaseFactory:
    @staticmethod
    def get_database():
        """
        根据配置返回相应的数据库实例
        如果MySQL连接失败，自动回退到本地数据库

        Returns:
            MySQLDatabase 或 LocalDatabase 的实例
        """
        if DATABASE_TYPE == "mysql":
            try:
                print("尝试使用MySQL数据库...")
                db = MySQLDatabase()
                # 确保表存在
                db.create_tables()
                print("MySQL数据库连接成功")
                return db
            except Exception as e:
                print(f"MySQL数据库连接失败: {e}")
                print("自动回退到本地JSON数据库")
                return LocalDatabase()
        elif DATABASE_TYPE == "local":
            print("使用本地JSON数据库")
            return LocalDatabase()
        else:
            print(f"未知的数据库类型: {DATABASE_TYPE}，默认使用本地数据库")
            return LocalDatabase()

# 便捷函数
def get_database():
    """获取数据库实例的便捷函数"""
    return DatabaseFactory.get_database()
