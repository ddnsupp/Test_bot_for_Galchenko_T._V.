from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from os import getenv

user = getenv('POSTGRES_USER')
password = getenv('POSTGRES_PASSWORD')
database = getenv('POSTGRES_DB')
host = getenv('POSTGRES_HOST', 'localhost')
port = getenv('POSTGRES_PORT', '5432')


async_engine = create_async_engine(
    url=f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}",
)

session_factory = async_sessionmaker(async_engine)



# async def connect_to_postgres():
#     user = getenv('POSTGRES_USER')
#     password = getenv('POSTGRES_PASSWORD')
#     database = getenv('POSTGRES_DB')
#     host = getenv('POSTGRES_HOST', 'localhost')
#     port = getenv('POSTGRES_PORT', '5432')
#
#     connection_string = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
#     engine = create_async_engine(connection_string, echo=False)
#
#     # Note the use of AsyncSession here
#     session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
#
#     return engine, session_maker

