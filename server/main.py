import os
import glob
import shutil
import logging
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from dotenv import load_dotenv

load_dotenv()

if not (API_KEY := os.getenv("API_KEY")):
    raise RuntimeError("API_KEY environment variable must be set")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate API KEY")


from src.modules import shared, sleep, alarms, dashboards, termux

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z"
)

def _sweep_garbage():
    """Remove compiled Python caches."""
    with suppress(Exception):
        for pycache in glob.glob("**/__pycache__", recursive=True):
            shutil.rmtree(pycache, ignore_errors=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup App Architecture For Production
    _sweep_garbage()
    shared.init_pool()
    shared.init_db()
    yield
    
    # Teardown Gracefully
    shared.close_pool()
    _sweep_garbage()


app = FastAPI(title="SmartWake Sleep Intelligence Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes — no API key required so phones can curl-install without credentials
app.include_router(termux.router)

# Protected routes — require X-API-Key header
app.include_router(sleep.router, dependencies=[Depends(get_api_key)])
app.include_router(alarms.router, dependencies=[Depends(get_api_key)])
app.include_router(dashboards.router, dependencies=[Depends(get_api_key)])

@app.get("/")
@app.get("/health")
def health_check():
    from src.modules.shared import BASE_URL
    return {
        "status": "ok",
        "service": "SmartWake Sleep Intelligence Server",
        "base_url": BASE_URL,
    }

@app.get("/favicon.ico", include_in_schema=False)
@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
def suppress_browser_assets():
    """Silently absorb browser-generated asset requests — keeps logs clean."""
    return Response(status_code=204)
