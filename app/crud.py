from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
from . import models, schemas
from datetime import datetime

# --- Country CRUD ---

async def get_country_by_name(db: AsyncSession, name: str) -> Optional[models.Country]:
    """
    Fetch a single country by its name (case-insensitive).
    """
    result = await db.execute(
        select(models.Country).where(func.lower(models.Country.name) == name.lower())
    )
    return result.scalars().first()

async def get_countries(
    db: AsyncSession, 
    region: Optional[str], 
    currency: Optional[str], 
    sort: Optional[str], 
    skip: int = 0, 
    limit: int = 100
) -> List[models.Country]:
    """
    Fetch a list of countries with optional filtering and sorting.
    """
    query = select(models.Country)

    if region:
        query = query.where(models.Country.region == region)
    
    if currency:
        query = query.where(models.Country.currency_code == currency)

    if sort == "gdp_desc":
        # Sort by GDP, putting NULLs last
        query = query.order_by(models.Country.estimated_gdp.desc())
    else:
        # Default sort by name
        query = query.order_by(models.Country.name.asc())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def get_countries_count(db: AsyncSession) -> int:
    """
    Get the total count of countries in the database.
    """
    result = await db.execute(select(func.count(models.Country.id)))
    return result.scalar() or 0

async def upsert_country(db: AsyncSession, country_data: schemas.CountryCreate) -> models.Country:
    """
    Update a country if it exists by name, or create it if it doesn't.
    """
    # Check if country exists (case-insensitive)
    db_country = await get_country_by_name(db, name=country_data.name)
    
    country_dict = country_data.model_dump()
    
    if db_country:
        # Update existing country
        await db.execute(
            update(models.Country)
            .where(models.Country.id == db_country.id)
            .values(**country_dict)
        )
        # Refresh the object to get updated values
        await db.refresh(db_country, attribute_names=country_dict.keys())
    else:
        # Insert new country
        db_country = models.Country(**country_dict)
        db.add(db_country)
        await db.flush() # Flush to get the new object in the session
    
    return db_country

async def delete_country_by_name(db: AsyncSession, name: str) -> Optional[models.Country]:
    """
    Delete a country by its name (case-insensitive).
    """
    db_country = await get_country_by_name(db, name)
    if db_country:
        await db.delete(db_country)
        await db.commit()
        return db_country
    return None

async def get_top_gdp_countries(db: AsyncSession, limit: int = 5) -> List[models.Country]:
    """
    Get the top N countries by estimated GDP.
    """
    query = (
        select(models.Country)
        .order_by(models.Country.estimated_gdp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

# --- AppStatus CRUD ---

async def get_app_status(db: AsyncSession) -> Optional[models.AppStatus]:
    """
    Get the global app status (singleton row).
    """
    result = await db.execute(select(models.AppStatus).where(models.AppStatus.id == 1))
    return result.scalars().first()

async def update_app_status(db: AsyncSession, refresh_time: datetime):
    """
    Update the global last_refreshed_at timestamp.
    """
    status = await get_app_status(db)
    if status:
        status.last_refreshed_at = refresh_time
        db.add(status)
    else:
        new_status = models.AppStatus(id=1, last_refreshed_at=refresh_time)
        db.add(new_status)
    await db.flush()