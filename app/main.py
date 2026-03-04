import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.scheduler import start_scheduler, stop_scheduler, fetch_all_keywords
from app.scraper import restore_accounts
from app.routers import feed, keywords, accounts

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await restore_accounts()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="X News Feed", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(feed.router,     prefix="/api")
app.include_router(keywords.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")


@app.get("/", include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/fetch")
async def trigger_fetch():
    """Manually trigger a fetch of all keywords."""
    import asyncio
    asyncio.create_task(fetch_all_keywords())
    return {"status": "fetch started"}
