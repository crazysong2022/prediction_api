# db.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def get_db_engine():
    """
    从 .env 加载 DATABASE_URL，并创建数据库引擎。
    成功连接后返回 engine。
    """
    # 加载 .env 文件中的环境变量
    load_dotenv()

    # 获取 DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL 未在 .env 文件中找到，请检查配置。")

    try:
        # 创建数据库引擎
        engine = create_engine(db_url)

        # 测试连接是否可用
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))  # 使用 text 包裹原生 SQL

        print("✅ 数据库连接成功！")
        return engine

    except SQLAlchemyError as e:
        error_msg = f"❌ 数据库连接失败：{str(e)}"
        raise ConnectionError(error_msg)