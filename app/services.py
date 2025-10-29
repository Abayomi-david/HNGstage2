import httpx
import random
import os
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas
from PIL import Image, ImageDraw, ImageFont
from .config import IMAGE_PATH
from typing import Optional




# Define a custom exception for service unavailability
class ServiceUnavailableException(Exception):
    def __init__(self, api_name: str, details: str):
        self.api_name = api_name
        self.details = details
        super().__init__(f"Could not fetch data from {api_name}: {details}")

# --- External API Fetching ---

async def fetch_exchange_rates() -> dict:
    """
    Fetch latest exchange rates from open.er-api.com.
    """
    url = "https://open.er-api.com/v6/latest/USD"
    api_name = "Exchange Rates API"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json().get("rates", {})
        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise ServiceUnavailableException(api_name=api_name, details=str(e))

async def fetch_countries_data() -> list:
    """
    Fetch country data from restcountries.com.
    """
    url = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
    api_name = "RestCountries API"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise ServiceUnavailableException(api_name=api_name, details=str(e))

# --- Core Refresh Logic ---

async def process_and_cache_countries(db: AsyncSession):
    """
    Main logic to fetch from APIs, process data, and cache in the DB.
    """
    # Fetch data from both APIs concurrently
    try:
        rates, countries = await asyncio.gather(
            fetch_exchange_rates(),
            fetch_countries_data()
        )
    except ServiceUnavailableException:
        # Re-raise to be caught by the endpoint's error handler
        raise

    refresh_time = datetime.now(timezone.utc)
    
    for country_data in countries:
        name = country_data.get("name")
        population = country_data.get("population")

        # Skip records with missing essential data
        if not name or population is None:
            continue

        currency_code: Optional[str] = None
        exchange_rate: Optional[float] = None
        estimated_gdp: Optional[float] = 0.0  # Default to 0

        # Handle currency data
        currencies = country_data.get("currencies", [])
        if currencies and isinstance(currencies, list):
            first_currency = currencies[0]
            if isinstance(first_currency, dict):
                currency_code = first_currency.get("code")

        # Calculate GDP if possible
        if currency_code and currency_code in rates:
            exchange_rate = rates[currency_code]
            if exchange_rate > 0: # Avoid division by zero
                random_multiplier = random.randint(1000, 2000)
                estimated_gdp = (population * random_multiplier) / exchange_rate
            else:
                estimated_gdp = 0.0 # Set to 0 if rate is 0
        elif currency_code:
            # Currency code exists but not in rates API
            exchange_rate = None
            estimated_gdp = None # Set to null as per spec
        else:
            # No currency array
            currency_code = None
            exchange_rate = None
            estimated_gdp = 0.0 # Set to 0 as per spec

        # Prepare data payload
        country_payload = schemas.CountryCreate(
            name=name,
            capital=country_data.get("capital"),
            region=country_data.get("region"),
            population=population,
            currency_code=currency_code,
            exchange_rate=exchange_rate,
            estimated_gdp=estimated_gdp,
            flag_url=country_data.get("flag")
        )

        # Update or insert the country
        await crud.upsert_country(db, country_payload)
    
    # Update the global refresh timestamp
    await crud.update_app_status(db, refresh_time)
    
    # Commit the entire transaction
    await db.commit()

    # Generate summary image after successful refresh
    await generate_summary_image(db)
    
    return {"status": "success", "refreshed_at": refresh_time}

# --- Image Generation ---

async def generate_summary_image(db: AsyncSession):
    """
    Generates a summary image and saves it to 'cache/summary.png'.
    """
    # Fetch data needed for the image
    total = await crud.get_countries_count(db)
    top_5 = await crud.get_top_gdp_countries(db)
    status = await crud.get_app_status(db)
    timestamp = status.last_refreshed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if status and status.last_refreshed_at else "N/A"

    # Create image
    img = Image.new('RGB', (600, 400), color='white')
    d = ImageDraw.Draw(img)

    # Try to load a font; fall back to default
    try:
        # You can bundle a .ttf font file (e.g., "DejaVuSans.ttf")
        # and use ImageFont.truetype("path/to/font.ttf", 15)
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
    except IOError:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # Draw text
    d.text((20, 20), "Country Data Summary", fill='black', font=font_title)
    d.text((20, 50), f"Last Refresh: {timestamp}", fill='darkgray', font=font_text)
    d.text((20, 80), f"Total Cached Countries: {total}", fill='black', font=font_text)
    
    d.text((20, 120), "Top 5 Countries by Estimated GDP:", fill='blue', font=font_text)
    y_pos = 150
    for i, country in enumerate(top_5):
        gdp_str = f"${country.estimated_gdp:,.2f}" if country.estimated_gdp is not None else "N/A"
        text = f"{i+1}. {country.name} ({gdp_str})"
        d.text((30, y_pos), text, fill='black', font=font_text)
        y_pos += 30

    # Ensure cache directory exists
    if not os.path.exists('cache'):
        os.makedirs('cache')

    # Save the image
    img.save(str(IMAGE_PATH))