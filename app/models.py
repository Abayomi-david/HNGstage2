from sqlalchemy import Column, Integer, String, Float, DateTime, func, BigInteger
from .database import Base

class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    capital = Column(String(255), nullable=True)
    region = Column(String(255), nullable=True, index=True)
    population = Column(BigInteger, nullable=False)
    currency_code = Column(String(10), nullable=True, index=True)
    exchange_rate = Column(Float, nullable=True)
    estimated_gdp = Column(Float, nullable=True, index=True)
    flag_url = Column(String(512), nullable=True)
    last_refreshed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AppStatus(Base):
    """
    A simple singleton table to store global app status,
    like the last successful refresh time.
    """
    __tablename__ = "app_status"

    id = Column(Integer, primary_key=True, default=1)
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True)