from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import asyncio
import threading

from app.core.database import engine, Base
from app.core.config import APP_NAME, APP_VERSION
from app.core.errors import APIError, error_response
from app.core.logger import get_logger

from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.problems import router as problems_router
from app.routes.submissions import router as submissions_router
from app.routes.chat import router as chat_router

from judge_worker import worker_loop

# --------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------
logger = get_logger("main")
    
# --------------------------------------------------------------------
# Global worker reference
# --------------------------------------------------------------------
judge_worker_thread: threading.Thread | None = None


# --------------------------------------------------------------------
# Lifespan (startup / shutdown)
# --------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global judge_worker_thread

    try:
        # ---- Startup ----
        logger.info("Creating/verifying database tables...")
        Base.metadata.create_all(bind=engine)

        logger.info("Starting judge worker thread...")
        judge_worker_thread = threading.Thread(
            target=worker_loop,
            daemon=True
        )
        judge_worker_thread.start()

        logger.info("Judge worker started (daemon mode)")
        logger.info(f"{APP_NAME} v{APP_VERSION} started successfully")

        yield

    except asyncio.CancelledError:
        # Expected during reload / shutdown
        logger.info("Application lifespan cancelled (reload/shutdown)")

    finally:
        # ---- Shutdown ----
        logger.info("Application shutdown complete")


# --------------------------------------------------------------------
# FastAPI app
# --------------------------------------------------------------------
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Authentication API for Ticket Raiser",
    lifespan=lifespan,
)

# --------------------------------------------------------------------
# UTF-8 Charset Middleware
# --------------------------------------------------------------------
class UTF8Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type")
        if content_type and "charset" not in content_type:
            response.headers["content-type"] = f"{content_type}; charset=utf-8"
        return response


# --------------------------------------------------------------------
# Middleware
# --------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(UTF8Middleware)

# --------------------------------------------------------------------
# Routers
# --------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(problems_router)
app.include_router(submissions_router)
app.include_router(chat_router)


# --------------------------------------------------------------------
# Exception Handlers
# --------------------------------------------------------------------
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return {
        "success": False,
        "error_code": exc.error_code,
        "message": exc.message,
        "details": exc.details,
    }


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, asyncio.CancelledError):
        raise exc

    logger.error("Unhandled exception", exc_info=True)
    return error_response(
        error_code="INTERNAL_ERROR",
        message="Internal server error",
        details={"exception": str(exc)},
    )


# --------------------------------------------------------------------
# Health / Root
# --------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Ticket Raiser API is live",
        "version": APP_VERSION,
        "docs": "/docs",
    }
