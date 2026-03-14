"""
数据库初始化脚本
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings


def init_database():
    """
    初始化数据库
    读取并执行schema.sql
    """
    print(f"正在连接数据库: {settings.DATABASE_URL}")

    engine = create_engine(settings.DATABASE_URL)

    # 读取schema.sql文件路径
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs",
        "schema.sql"
    )

    if not os.path.exists(schema_path):
        print(f"错误: schema.sql文件不存在: {schema_path}")
        return False

    print(f"正在读取schema.sql: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    print("正在执行数据库初始化...")

    # 分割SQL语句并执行
    # PostgreSQL的扩展和类型定义需要单独处理
    statements = []
    current_statement = []

    for line in schema_sql.split("\n"):
        stripped = line.strip()

        # 跳过注释和空行
        if not stripped or stripped.startswith("--"):
            continue

        current_statement.append(line)

        # 检查是否是语句结束
        if stripped.endswith(";"):
            statement = "\n".join(current_statement)
            statements.append(statement)
            current_statement = []

    # 执行所有语句
    with engine.begin() as conn:
        for i, statement in enumerate(statements, 1):
            try:
                # 跳过纯注释
                if statement.strip().startswith("--"):
                    continue
                conn.execute(text(statement))
            except Exception as e:
                # 某些语句可能已存在，跳过错误
                if "already exists" not in str(e):
                    print(f"警告: 执行语句 {i} 时出错: {e}")

    print("数据库初始化完成!")
    print("\n系统预设资产:")
    print("- 3个系统形象")
    print("- 3个系统音色")
    print("- 3个系统脚本")
    print("- 订阅计划配置")
    print("- 系统配置")

    return True


if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"初始化失败: {e}")
        sys.exit(1)
