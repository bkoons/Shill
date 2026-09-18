import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.database import init_db
from backend.app.core.rewards import init_rewards_table
from backend.app.core.udp_mesh import start_udp_mesh
from backend.app.engine.turn_manager import turn_manager
from backend.app.api.routes import router
from backend.app.api.openai_compat import openai_router
from backend.app.api.admin import admin_router, record_udp_telemetry
from backend.app.core.rate_limit import RateLimitMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_rewards_table()
    
    # Initialize Real UDP Peer Socket Mesh
    udp_port = int(os.getenv("UDP_PORT", "9999"))
    mesh = await start_udp_mesh(port=udp_port, audit_cb=record_udp_telemetry)
    turn_manager.set_udp_mesh(mesh)
    
    turn_manager.start()
    yield
    turn_manager.stop()

from backend.app.version import __version__

app = FastAPI(
    title="Shill Sovereign P2P Bot Messenger & OpenAI Engine",
    description="Decentralized sovereign bot messenger over real UDP socket mesh with gated security breach investigation.",
    version=__version__,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("SHILL_CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(RateLimitMiddleware)
app.include_router(router, prefix="/api")
app.include_router(admin_router)
app.include_router(openai_router)
_START_TIME = __import__("time").time()

@app.get("/health")
def health():
    return {"status": "ok", "service": "shill"}

@app.get("/ready")
def ready():
    try:
        from backend.app.core.database import get_db_connection
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        return {"ready": False, "db": f"down: {e}"}
    return {"ready": True, "db": "up"}

@app.get("/version")
def version():
    return {"service": "shill", "version": os.getenv("SHILL_VERSION", __version__),
            "uptime_sec": round(__import__("time").time() - _START_TIME, 1)}


# Support multiple frontend locations (local dev, Vercel, Docker, etc.)
_base = os.path.dirname(__file__)
_candidates = [
    os.path.join(_base, "../frontend"),      # Local dev: project_root/frontend
    os.path.join(_base, "frontend"),         # Vercel: outputDirectory/backend/frontend
    os.path.join(_base, "../public"),        # Local alt: project_root/public
    os.path.join(_base, "public"),           # Vercel alt: outputDirectory/backend/public
]
_frontend_dir = next((p for p in _candidates if os.path.exists(p)), None)
if _frontend_dir:
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    http_port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=http_port, reload=False)
