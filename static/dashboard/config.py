import os
from dotenv import load_dotenv

load_dotenv()

MODE = os.getenv("APP_MODE", "prod")          # "test" или "prod"
DATA_SOURCE = os.getenv("DATA_SOURCE", "raw") # "enriched" или "raw"
POSTGRES_DSN = os.getenv(
    "DASHBOARD_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_radar"),
).replace("postgresql+asyncpg://", "postgresql://")
DATA_DIR = "data"                             # для тестового режима
