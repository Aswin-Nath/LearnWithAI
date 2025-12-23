from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import threading

from app.core.database import engine, Base
from app.core.config import APP_NAME, APP_VERSION
from app.core.errors import APIError, error_response
from app.core.logger import get_logger
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.problems import router as problems_router
from app.routes.submissions import router as submissions_router
from judge_worker import worker_loop

# Setup logging
logger = get_logger("main")

# Judge worker thread
judge_worker_thread = None

# Create tables
Base.metadata.create_all(bind=engine)
logger.info("Database tables created/verified")

# Initialize FastAPI app
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Authentication API for Ticket Raiser"
)

# UTF-8 Charset Middleware
class UTF8Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Ensure Content-Type includes charset
        if response.headers.get("content-type"):
            content_type = response.headers.get("content-type")
            if "charset" not in content_type:
                response.headers["content-type"] = f"{content_type}; charset=utf-8"
        return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add UTF-8 charset middleware
app.add_middleware(UTF8Middleware)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(problems_router)
app.include_router(submissions_router)


# ============================================================================
# Global Exception Handler
# ============================================================================

@app.exception_handler(APIError)
async def api_error_handler(request, exc: APIError):
    """Handle API errors with consistent response format"""
    return {
        "success": False,
        "error_code": exc.error_code,
        "message": exc.message,
        "details": exc.details
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unhandled exception: {exc}")
    return error_response(
        error_code="INTERNAL_ERROR",
        message="Internal server error",
        details={"exception": str(exc)}
    )


# ============================================================================
# Judge Worker Startup/Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Start judge worker on app startup"""
    global judge_worker_thread
    
    logger.info("Starting judge worker...")
    judge_worker_thread = threading.Thread(target=worker_loop, daemon=True)
    judge_worker_thread.start()
    logger.info("Judge worker thread started (daemon mode)")
    logger.info(f"{APP_NAME} v{APP_VERSION} started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown"""
    logger.info("Application shutting down...")


@app.get("/")
def root():
    return {
        "message": "Ticket Raiser API is live",
        "version": APP_VERSION,
        "docs": "/docs"
    }
