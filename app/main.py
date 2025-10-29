import os
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from . import crud, models, schemas, services
from .database import get_db, init_db, engine
from .services import ServiceUnavailableException
from .config import IMAGE_PATH

# Create the FastAPI app
app = FastAPI(
    title="Country Currency & Exchange API",
    description="An API to fetch, cache, and serve country and currency data.",
    version="1.0.0"
)

# --- Event Handlers ---

@app.on_event("startup")
async def on_startup():
    """
    Initialize the database tables on startup.
    """
    await init_db()

@app.on_event("shutdown")
async def on_shutdown():
    """
    Close the database engine connection on shutdown.
    """
    await engine.dispose()

# --- Custom Error Handlers ---

@app.exception_handler(ServiceUnavailableException)
async def service_unavailable_handler(request: Request, exc: ServiceUnavailableException):
    """
    Handle 503 errors from external API failures.
    """
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "External data source unavailable",
            "details": f"Could not fetch data from {exc.api_name}"
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle 400 validation errors to match the required format.
    """
    details = {}
    for error in exc.errors():
        field = error["loc"][-1] if len(error["loc"]) > 1 else "body"
        details[str(field)] = error["msg"]
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Validation failed", "details": details}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle generic 404/other HTTP errors.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected 500 internal server errors.
    """
    # Log the exception here (e.g., logging.error(exc, exc_info=True))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )

# --- API Endpoints ---

@app.post(
    "/countries/refresh",
    summary="Refresh Country Data",
    description="Fetches data from external APIs, updates the database, and generates a summary image.",
    status_code=status.HTTP_200_OK
)
async def refresh_countries_data(db: AsyncSession = Depends(get_db)):
    """
    Endpoint to trigger the data refresh process.
    """
    # The ServiceUnavailableException will be caught by the custom handler
    result = await services.process_and_cache_countries(db)
    return result

@app.get(
    "/countries",
    response_model=List[schemas.Country],
    summary="Get All Countries",
    description="Get a list of all countries from the database, with optional filtering and sorting."
)
async def get_all_countries(
    region: Optional[str] = Query(None, description="Filter by region (e.g., 'Africa')"),
    currency: Optional[str] = Query(None, description="Filter by currency code (e.g., 'NGN')"),
    sort: Optional[str] = Query(None, description="Sort by GDP (use 'gdp_desc')"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all countries, with filters for region, currency, and sorting by GDP.
    """
    countries = await crud.get_countries(db, region=region, currency=currency, sort=sort)
    return countries

@app.get(
    "/countries/{name}",
    response_model=schemas.Country,
    summary="Get Country by Name",
    description="Get a single country by its name (case-insensitive)."
)
async def get_country_by_name(name: str, db: AsyncSession = Depends(get_db)):
    """
    Get a single country by its name.
    """
    db_country = await crud.get_country_by_name(db, name=name)
    if db_country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return db_country

@app.delete(
    "/countries/{name}",
    summary="Delete Country by Name",
    description="Delete a single country from the cache by its name.",
    status_code=status.HTTP_200_OK
)
async def delete_country(name: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a country record from the database.
    """
    deleted_country = await crud.delete_country_by_name(db, name=name)
    if deleted_country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return {"status": "success", "message": f"Successfully deleted {deleted_country.name}"}

@app.get(
    "/status",
    response_model=schemas.StatusResponse,
    summary="Get API Status",
    description="Get the total number of cached countries and the last refresh timestamp."
)
async def get_status(db: AsyncSession = Depends(get_db)):
    """
    Get the application's status.
    """
    total = await crud.get_countries_count(db)
    status_record = await crud.get_app_status(db)
    timestamp = status_record.last_refreshed_at if status_record else None
    
    return {"total_countries": total, "last_refreshed_at": timestamp}

# @app.get(
#     "/countries/image",
#     summary="Get Summary Image",
#     description="Serves the 'cache/summary.png' image generated during the last refresh."
# )
# async def get_summary_image():
#     """
#     Serve the generated summary image file.
#     """
#     image_path = "cache/summary.png"
#     if not os.path.exists(image_path):
#         return JSONResponse(
#             status_code=status.HTTP_404_NOT_FOUND,
#             content={"error": "Summary image not found. Run /countries/refresh to generate it."}
#         )
#     return FileResponse(image_path, media_type="image/png")
@app.get(
    "/countries/image",
    summary="Get Summary Image",
    description="Serves the 'cache/summary.png' image generated during the last refresh."
)
async def get_summary_image():
    """
    Serve the generated summary image file.
    """
    # Use the absolute path from the config
    image_path = str(IMAGE_PATH)
    
    if not os.path.exists(image_path):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Summary image not found. Run /countries/refresh to generate it."}
        )
    return FileResponse(image_path, media_type="image/png")