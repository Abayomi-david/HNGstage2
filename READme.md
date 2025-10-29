# Country Currency & Exchange API

This is a FastAPI application that provides a RESTful API to fetch, cache, and serve data about countries, their currencies, and estimated GDP.

## Features

* Fetches data from `restcountries.com` and `open.er-api.com`.
* Caches data in a MySQL database.
* Calculates an `estimated_gdp` for each country.
* Generates a summary image (`cache/summary.png`) on data refresh.
* Provides CRUD endpoints to interact with the cached data.

## API Endpoints

* `POST /countries/refresh`: Fetches new data, updates the DB, and regenerates the summary image.
* `GET /countries`: Returns a list of all countries.
    * Query params: `?region=Africa`, `?currency=NGN`, `?sort=gdp_desc`
* `GET /countries/{name}`: Returns data for a single country by name.
* `DELETE /countries/{name}`: Deletes a country from the cache.
* `GET /status`: Returns the total number of cached countries and the last refresh timestamp.
* `GET /countries/image`: Serves the `cache/summary.png` image.

## Setup Instructions

### 1. Prerequisites

* Python 3.9+
* A running MySQL database.

### 2. Clone the Repository

```bash
git clone <https://github.com/Abayomi-david/HNGstage2.git>

/country-api
├── cache/
│   └── .gitkeep  (The 'summary.png' will be generated here)
├── .env
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py         (FastAPI app, endpoints, error handlers)
│   ├── database.py     (Async database setup, engine, session)
│   ├── models.py       (SQLAlchemy table models)
│   ├── schemas.py      (Pydantic data models for validation)
│   ├── crud.py         (Async database logic: Create, Read, Update, Delete)
│   ├── services.py     (Business logic: API fetching, GDP calc, image gen)
│   └── config.py       (Settings management)