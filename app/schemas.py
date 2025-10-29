from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

# Base Pydantic model for a Country
class CountryBase(BaseModel):
    name: str
    capital: Optional[str] = None
    region: Optional[str] = None
    population: int
    currency_code: Optional[str] = None
    exchange_rate: Optional[float] = None
    estimated_gdp: Optional[float] = None
    flag_url: Optional[HttpUrl] = None

# Model for creating a country (used internally)
class CountryCreate(CountryBase):
    pass

# Model for updating a country (used internally)
class CountryUpdate(CountryBase):
    pass

# Model for responses (includes DB-generated fields)
class Country(CountryBase):
    id: int
    last_refreshed_at: datetime

    class Config:
        from_attributes = True  # Replaced orm_mode in Pydantic v2

# Model for the /status endpoint
class StatusResponse(BaseModel):
    total_countries: int
    last_refreshed_at: Optional[datetime] = None

# Standard error response models
class ErrorDetail(BaseModel):
    error: str
    details: Optional[Dict[str, Any] | str] = None