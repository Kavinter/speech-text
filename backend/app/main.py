from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import meetings

app = FastAPI(
    title="STT FastAPI App",
    description="Minimal FastAPI backend with MySQL + SQLAlchemy",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meetings.router)
