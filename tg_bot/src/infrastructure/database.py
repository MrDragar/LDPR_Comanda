from sqlalchemy.ext.asyncio import (
    async_sessionmaker, create_async_engine, AsyncSession,
    async_scoped_session, AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from src.infrastructure.interfaces import IDatabase


class Base(DeclarativeBase):
    ...


class Database(IDatabase):
    __engine: AsyncEngine
    __session_maker: async_sessionmaker
    __database_session: async_scoped_session

    def __init__(self, db_url: str):
        self.__engine = create_async_engine(
            self.get_sqlite_url(db_url), echo=True
        )
        self.__session_maker = async_sessionmaker(
            bind=self.__engine,
            autoflush=False,
            class_=AsyncSession
        )

    def create_session(self) -> AsyncSession:
        return self.__session_maker()

    async def create_database(self):
        async with self.__engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await self.__run_light_migrations(conn)

    @staticmethod
    async def __run_light_migrations(conn):
        result = await conn.execute(text("PRAGMA table_info(headliners)"))
        columns = {row[1] for row in result.fetchall()}
        if columns and "welcome_message" not in columns:
            await conn.execute(text("ALTER TABLE headliners ADD COLUMN welcome_message TEXT"))
        await Database.__drop_global_phone_unique(conn)

    @staticmethod
    async def __drop_global_phone_unique(conn):
        indexes = await conn.execute(text("PRAGMA index_list(users)"))
        for index in indexes.fetchall():
            if not index[2]:
                continue
            index_name = index[1]
            index_info = await conn.execute(text(f"PRAGMA index_info({index_name})"))
            index_columns = [row[2] for row in index_info.fetchall()]
            if index_columns != ["phone_number"]:
                continue

            await conn.execute(text("PRAGMA foreign_keys=OFF"))
            await conn.execute(text("""
                CREATE TABLE users_new (
                    id INTEGER NOT NULL,
                    source VARCHAR(3) NOT NULL,
                    is_member BOOLEAN,
                    username VARCHAR,
                    surname VARCHAR NOT NULL,
                    name VARCHAR,
                    patronymic VARCHAR,
                    birth_date DATE,
                    phone_number VARCHAR NOT NULL,
                    region VARCHAR,
                    email VARCHAR,
                    gender VARCHAR,
                    city VARCHAR,
                    wish_to_join BOOLEAN,
                    home_address VARCHAR,
                    news_subscription BOOLEAN NOT NULL,
                    balance INTEGER NOT NULL,
                    role VARCHAR(14) NOT NULL,
                    grade VARCHAR(15) NOT NULL,
                    created_at DATETIME NOT NULL,
                    PRIMARY KEY (id, source)
                )
            """))
            await conn.execute(text("""
                INSERT INTO users_new (
                    id, source, is_member, username, surname, name, patronymic,
                    birth_date, phone_number, region, email, gender, city,
                    wish_to_join, home_address, news_subscription, balance,
                    role, grade, created_at
                )
                SELECT
                    id, source, is_member, username, surname, name, patronymic,
                    birth_date, phone_number, region, email, gender, city,
                    wish_to_join, home_address, news_subscription, balance,
                    role, grade, created_at
                FROM users
            """))
            await conn.execute(text("DROP TABLE users"))
            await conn.execute(text("ALTER TABLE users_new RENAME TO users"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            break

    @staticmethod
    def get_sqlite_url(db_path) -> str:
        return f"sqlite+aiosqlite:///{db_path}"
