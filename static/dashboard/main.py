import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from static.dashboard.config import MODE, POSTGRES_DSN
from static.dashboard.providers.csv_provider import CSVDataProvider
from static.dashboard import dependencies
from static.dashboard.api import models, sources, stats, export, ai

# Инициализация провайдера
if MODE == "test":
    data_provider = CSVDataProvider()
else:
    from static.dashboard.providers.postgres_provider import PostgresDataProvider

    data_provider = PostgresDataProvider(POSTGRES_DSN)

# Сохраняем провайдера в центральном месте
dependencies.set_data_provider(data_provider)

app = FastAPI(title="Model Dashboard API")

# Подключаем роутеры
app.include_router(models.router)
app.include_router(sources.router)
app.include_router(stats.router)
app.include_router(export.router)
app.include_router(ai.router)

# Чтение HTML-шаблона (файл лежит в app/templates/index.html)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
INDEX_HTML_PATH = os.path.join(TEMPLATES_DIR, "index.html")

def get_html() -> str:
    try:
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<html><body><h1>Template not found</h1></body></html>"

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(get_html())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
