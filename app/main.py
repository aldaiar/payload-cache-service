import os

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(
    title="Payload Cache Service",
    description="API for storing and retrieving transformed payloads.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "Payload Cache Service is running"}


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )
