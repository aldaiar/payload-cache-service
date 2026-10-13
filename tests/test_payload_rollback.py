import os
import uuid

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Payload, TransformCache
from app.schemas.payload import PayloadCreate
from app.services.payload_service import PayloadService


def test_payload_creation_rolls_back_after_failure(monkeypatch):
    database_url = os.environ.get("DATABASE_URL", "")

    if not database_url.startswith(("postgresql://", "postgresql+")):
        pytest.skip("This integration test requires PostgreSQL")

    engine = create_engine(database_url, pool_pre_ping=True)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    suffix = uuid.uuid4().hex

    request_data = PayloadCreate(
        list_1=[f"first-{suffix}", f"second-{suffix}"],
        list_2=[f"other-{suffix}", f"another-{suffix}"],
    )

    request_hash = PayloadService.make_request_hash(request_data)
    cache_values = request_data.list_1 + request_data.list_2

    try:
        # Prepopulate the cache so the test focuses on Payload rollback.
        with TestingSessionLocal.begin() as session:
            for value in cache_values:
                session.add(
                    TransformCache(
                        input_text=value,
                        output_text=value.upper(),
                    )
                )

        original_flush = Session.flush

        def flush_then_fail(session, objects=None):
            # Check whether this flush is about to insert a Payload.
            has_new_payload = any(
                isinstance(obj, Payload)
                for obj in session.new
            )

            # Execute the SQL INSERT inside the current transaction.
            result = original_flush(session, objects)

            # Simulate a failure after the INSERT but before commit.
            if has_new_payload:
                raise RuntimeError("Simulated failure after Payload INSERT")

            return result

        monkeypatch.setattr(Session, "flush", flush_then_fail)

        # The exception should escape, causing the transaction to roll back.
        with TestingSessionLocal() as session:
            service = PayloadService(session)

            with pytest.raises(
                RuntimeError,
                match="Simulated failure after Payload INSERT",
            ):
                service.create_payload_with_retry(request_data)

        # Verify that the uncommitted Payload was not persisted.
        with TestingSessionLocal() as session:
            payload = (
                session.query(Payload)
                .filter_by(request_hash=request_hash)
                .first()
            )

            assert payload is None

    finally:
        # Remove only the data created by this test.
        with TestingSessionLocal.begin() as session:
            session.execute(
                delete(Payload).where(
                    Payload.request_hash == request_hash
                )
            )

            session.execute(
                delete(TransformCache).where(
                    TransformCache.input_text.in_(cache_values)
                )
            )

        engine.dispose()