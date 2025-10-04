from pathlib import Path
from pydantic_settings import BaseSettings

# Build a path to the .env file in the project root
env_path = Path(__file__).parent.parent.parent.parent / '.env'

class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str 

    class Config:
        env_file = env_path

settings = Settings()