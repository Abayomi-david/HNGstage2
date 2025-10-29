from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .config import settings

# Create the async engine
engine = create_async_engine(settings.DATABASE_URL)

# Create a session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for our models
Base = declarative_base()

async def get_db():
    """
    Dependency to get an async database session.
    """
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """
    Initialize the database by creating all tables.
    """
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Optional: drop tables first
        await conn.run_sync(Base.metadata.create_all)