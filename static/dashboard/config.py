import os
from dotenv import load_dotenv

load_dotenv()

MODE = os.getenv("APP_MODE", "test")          # "test" или "prod"
DATA_SOURCE = os.getenv("DATA_SOURCE", "raw") # "enriched" или "raw"
POSTGRES_DSN = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
DATA_DIR = "data"                             # для тестового режима