"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, users, modules, enrolments, sessions, attendance, face, dashboard
from app.seed import seed_demo_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    logger.info(f"Starting AttendanceMS (env={settings.APP_ENV})")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Seed demo data if enabled
    if settings.SEED_DEMO_DATA:
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()
    
    yield
    
    # Shutdown
    logger.info("Shutting down AttendanceMS")


app = FastAPI(
    title="AttendanceMS API",
    description="Role-based facial recognition attendance management system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint for load balancer / container orchestration."""
    return {"status": "healthy", "service": "attendancems"}


# API routes
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(enrolments.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(attendance.router, prefix="/api")
app.include_router(face.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


# Serve static frontend files
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the SPA for all non-API routes."""
        # Skip API routes
        if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json", "health"]:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        
        # Try to serve the exact file
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Fallback to index.html for SPA routing
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        
        return JSONResponse({"detail": "Not Found"}, status_code=404)
else:
    @app.get("/")
    def root():
        """Root endpoint when no frontend is built."""
        return {
            "message": "AttendanceMS API",
            "docs": "/docs",
            "health": "/health",
        }
