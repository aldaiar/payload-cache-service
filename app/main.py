
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import Base, SessionLocal, engine
from app.models import Payload, TransformCache
from app.schemas.payload import (
    PayloadCreate,
    PayloadCreated,
    PayloadRead,
)
from app.services.payload_service import PayloadService


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Payload Cache Service",
    version="0.1.0",
    lifespan=lifespan,
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


@app.post("/payload", response_model=PayloadCreated)
def create_payload(data: PayloadCreate):
    try:
        with SessionLocal.begin() as session:
            service = PayloadService(session)
            payload_id = service.create_payload(data)

        return PayloadCreated(id=payload_id)

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="A concurrent request caused a database conflict",
        )


@app.get("/payload/{payload_id}", response_model=PayloadRead)
def read_payload(payload_id: str):
    with SessionLocal() as session:
        service = PayloadService(session)
        payload = service.get_payload(payload_id)

        if payload is None:
            raise HTTPException(
                status_code=404,
                detail="Payload not found",
            )

        return PayloadRead(output=payload.output)