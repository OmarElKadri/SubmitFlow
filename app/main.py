from fastapi import FastAPI
from app.api.routes import jobs, directories, products, health
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AutoSaaS Directory Submission Agent",
    description="Automated SaaS directory submission system using vision-based LLM reasoning",
    version="1.0.0",
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(directories.router, prefix="/api/v1/directories", tags=["Directories"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])


@app.on_event("startup")
async def startup_event():
    pass


@app.on_event("shutdown")
async def shutdown_event():
    pass
