"""
Propilkki Tournament API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers import stats, sessions

app = FastAPI(
    title="Propilkki Tournament API",
    description="API for Pro Pilkki 2 ice fishing tournament statistics",
    version="1.0.0"
)

# CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(stats.router)
app.include_router(sessions.router)

@app.get("/")
def root():
    return {
        "message": "Propilkki Tournament API",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
