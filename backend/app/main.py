from fastapi import FastAPI

from .database import init_db
from .routers import leagues


app = FastAPI()

app.include_router(leagues.router, prefix="/api/v1", tags=["leagues"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def read_root():
    return {"Hello": "World"}
