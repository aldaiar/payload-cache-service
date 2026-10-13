
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_session
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
def create_payload(
    data: PayloadCreate,
    session: Session = Depends(get_session),
):
    try:
        service = PayloadService(session)
        payload_id = service.create_payload_with_retry(data)
        return PayloadCreated(id=payload_id)

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="A database integrity conflict occurred",
        )

@app.get("/payload/{payload_id}", response_model=PayloadRead)
def read_payload(
    payload_id: str,
    session: Session = Depends(get_session),
):
    service = PayloadService(session)
    payload = service.get_payload(payload_id)

    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="Payload not found",
        )

    return PayloadRead(output=payload.output)