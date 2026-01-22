from fastapi import FastAPI
from app.api.routes import jobs, directories, products, health
from app.config import get_settings
from app.db.base import Base
from app.db.session import engine
from fastapi.middleware.cors import CORSMiddleware
import app.models  # Import models to register them with Base

settings = get_settings()

app = FastAPI(
    title="AutoSaaS Directory Submission Agent",
    description="Automated SaaS directory submission system using vision-based LLM reasoning",
    version="1.0.0",
)

origins = [
    "http://localhost",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(directories.router, prefix="/api/v1/directories", tags=["Directories"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])


@app.on_event("startup")
async def startup_event():
    # Create all tables
    Base.metadata.create_all(bind=engine)


@app.on_event("shutdown")
async def shutdown_event():
    pass
