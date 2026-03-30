import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "sk_live_smartwake_93f8e21a")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate API KEY")


from src.modules import shared, sleep, alarms, dashboards, termux

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.getenv("DB_PATH", "db/smartwake.db")
    if not db_path.startswith("/"):
        logging.warning(f"⚠️ RAILWAY EPHEMERAL STORAGE WARNING: DB_PATH='{db_path}' is a relative path — the database will be PERMANENTLY DELETED on next deployment. Mount a Railway Volume and set DB_PATH to an absolute path like /data/smartwake.db")
        
    # ---------------- Startup Sweep Phase ----------------
    logging.warning("🧹 [CLEANUP] Sweeping legacy caches before server binds...")
    import shutil
    import glob
    try:
        for pycache in glob.glob("**/__pycache__", recursive=True):
            shutil.rmtree(pycache, ignore_errors=True)
        for garbage in glob.glob("**/*-journal", recursive=True) + glob.glob("**/*.tmp", recursive=True):
            try: os.remove(garbage)
            except OSError: pass
    except Exception:
        pass
        
    shared.init_db()
    yield
    
    # ---------------- Shutdown Phase ----------------
    logging.warning("🧹 [CLEANUP] Initiating graceful shutdown. Sweeping temporary garbage files...")
    import shutil
    import glob
    
    try:
        # Purge all compiled python caches
        for pycache in glob.glob("**/__pycache__", recursive=True):
            shutil.rmtree(pycache, ignore_errors=True)
            
        # Clean up SQLite journals and stray temporary dumps
        for garbage in glob.glob("**/*-journal", recursive=True) + glob.glob("**/*.tmp", recursive=True):
            try:
                os.remove(garbage)
            except OSError:
                pass
                
        logging.warning("🧹 [CLEANUP] Garbage collection complete. System teardown finished cleanly!")
    except Exception as e:
        logging.error(f"Error during teardown: {e}")

app = FastAPI(title="SmartWake Sleep Intelligence Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes — no API key required so phones can curl-install without credentials
app.include_router(termux.router)

# Protected routes — require X-API-Key header
app.include_router(sleep.router, dependencies=[Depends(get_api_key)])
app.include_router(alarms.router, dependencies=[Depends(get_api_key)])
app.include_router(dashboards.router, dependencies=[Depends(get_api_key)])

@app.get("/health")
def health_check():
    return {"status": "ok"}