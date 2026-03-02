from fastapi import FastAPI
from app.CHANGE.routers import dreams

app = FastAPI(
    title="Dream Maker API",
    version="1.0",
    description="Description of project"
)

app.include_router(dreams.router)