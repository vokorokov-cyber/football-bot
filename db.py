import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")

pool = None


async def init_db():
    global pool

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not set")

    pool = await asyncpg.create_pool(DATABASE_URL)

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id BIGINT,
                category TEXT,
                PRIMARY KEY (user_id, category)
            );
        """)

    print("✅ DB CONNECTED")


async def add_user(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
            user_id
        )


async def get_subscriptions(user_id: int):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT category FROM subscriptions WHERE user_id = $1",
            user_id
        )
        return {r["category"] for r in rows}


async def toggle_subscription(user_id: int, category: str):
    async with pool.acquire() as conn:
        exists = await conn.fetchrow(
            "SELECT 1 FROM subscriptions WHERE user_id=$1 AND category=$2",
            user_id, category
        )

        if exists:
            await conn.execute(
                "DELETE FROM subscriptions WHERE user_id=$1 AND category=$2",
                user_id, category
            )
        else:
            await conn.execute(
                "INSERT INTO subscriptions (user_id, category) VALUES ($1, $2)",
                user_id, category
            )


async def clear_subscriptions(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM subscriptions WHERE user_id=$1",
            user_id
        )


async def get_users_by_categories(categories: list[str]):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT user_id
            FROM subscriptions
            WHERE category = ANY($1)
            """,
            categories
        )
        return [r["user_id"] for r in rows]