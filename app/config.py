from pydantic_settings import BaseSettings

from pathlib import Path

# Define the root directory (the parent of the 'app' directory)
ROOT_DIR = Path(__file__).resolve().parent.parent
# Define the absolute path for the summary image
IMAGE_PATH = ROOT_DIR / "cache" / "summary.png"

class Settings(BaseSettings):
    # The `DATABASE_URL` will be loaded from the .env file
    DATABASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()