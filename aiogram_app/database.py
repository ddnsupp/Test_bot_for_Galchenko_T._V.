from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from pathlib import Path
from dotenv import load_dotenv
from os import getenv

env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)

user = getenv('POSTGRES_USER')
password = getenv('POSTGRES_PASSWORD')
database = getenv('POSTGRES_DB')
host = getenv('POSTGRES_HOST')
port = getenv('POSTGRES_PORT')


async_engine = create_async_engine(
    url=f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}",
)

session_factory = async_sessionmaker(async_engine)

