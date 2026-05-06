import os

class Settings:
    # 数据库配置
    # DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+aiomysql://root:123456@localhost:3306/educational_platform_db")
    # 'educational_platform_db' 是你将创建的数据库名称
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+aiomysql://root:123456@localhost:3306/educational_platform")

settings = Settings()