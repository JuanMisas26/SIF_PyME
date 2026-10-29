import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.paths import STATIC_DIR
from app.database import init_db
from app.errors import (
    AppException, app_exception_handler,
    RequestValidationError, validation_exception_handler,
    HTTPException, http_exception_handler,
    unhandled_exception_handler
)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield

# Initialize FastAPI app
app = FastAPI(
    title="SIF - Sistema de Facturación Local",
    description="Software de Facturación para PyME",
    version="1.0.0",
    lifespan=lifespan
)

# Register typed exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# CORS middleware for local development and embedded webview
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

from app.routes import clientes, productos, facturas, configuracion, presupuestos, descuentos, backups, papelera, contadores

# Include API routers (standardized under /api prefix)
app.include_router(contadores.router, prefix="/api", tags=["Contadores"])
app.include_router(clientes.router, prefix="/api", tags=["Clientes"])
app.include_router(productos.router, prefix="/api", tags=["Productos"])
app.include_router(descuentos.router, prefix="/api", tags=["Descuentos"])
app.include_router(facturas.router, prefix="/api", tags=["Facturas"])
app.include_router(presupuestos.router, prefix="/api", tags=["Presupuestos"])
app.include_router(configuracion.router, prefix="/api", tags=["Configuracion"])
app.include_router(backups.router, prefix="/api", tags=["Backups"])
app.include_router(papelera.router, prefix="/api", tags=["Papelera"])

# Include page routes
from app.routes.pages import router as pages_router
app.include_router(pages_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
