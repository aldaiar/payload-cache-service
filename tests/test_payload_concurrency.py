
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_session
from app.main import app
from app.models import Payload, TransformCache
from app.schemas.payload import PayloadCreate
from app.services.payload_service import PayloadService


def test_concurrent_identical_requests_reuse_payload_id(monkeypatch):
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

    request_data = {
        "list_1": [f"first-{suffix}", f"second-{suffix}"],
        "list_2": [f"other-{suffix}", f"another-{suffix}"],
    }

    request_hash = PayloadService.make_request_hash(
        PayloadCreate(**request_data)
    )

    # Prepopulate the cache to avoid concurrent cache insertions.
    with TestingSessionLocal.begin() as session:
        for value in request_data["list_1"] + request_data["list_2"]:
            session.add(
                TransformCache(
                    input_text=value,
                    output_text=value.upper(),
                )
            )

    # Synchronize both requests immediately before flushing a new Payload.
    barrier = Barrier(2)
    original_flush = Session.flush

    def synchronized_flush(session, objects=None):
        if any(isinstance(obj, Payload) for obj in session.new):
            barrier.wait(timeout=10)

        return original_flush(session, objects)

    monkeypatch.setattr(Session, "flush", synchronized_flush)

    # Record IntegrityError exceptions raised during payload creation.
    integrity_errors = []
    integrity_errors_lock = Lock()

    original_create_payload = PayloadService.create_payload

    def tracked_create_payload(self, data):
        try:
            return original_create_payload(self, data)
        except IntegrityError:
            with integrity_errors_lock:
                integrity_errors.append(True)
            raise

    monkeypatch.setattr(
        PayloadService,
        "create_payload",
        tracked_create_payload,
    )

    def override_get_session():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client_1 = TestClient(app)
        client_2 = TestClient(app)

        def send_request(client):
            return client.post("/payload", json=request_data)

        # Send two identical requests concurrently.
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_1 = executor.submit(send_request, client_1)
            future_2 = executor.submit(send_request, client_2)

            response_1 = future_1.result(timeout=20)
            response_2 = future_2.result(timeout=20)

        # Both requests should complete successfully.
        assert response_1.status_code == 200, response_1.text
        assert response_2.status_code == 200, response_2.text

        # Both requests should return the same ID.
        assert response_1.json()["id"] == response_2.json()["id"]

        # At least one IntegrityError must occur during payload creation.
        assert len(integrity_errors) >= 1, (
            "Expected a concurrent INSERT to raise IntegrityError"
        )

        # Exactly one record should exist in the database.
        with TestingSessionLocal() as session:
            payloads = (
                session.query(Payload)
                .filter_by(request_hash=request_hash)
                .all()
            )

            assert len(payloads) == 1

    finally:
        app.dependency_overrides.clear()

        # Delete only the data created by this test.
        with TestingSessionLocal.begin() as session:
            session.execute(
                delete(Payload).where(
                    Payload.request_hash == request_hash
                )
            )

            session.execute(
                delete(TransformCache).where(
                    TransformCache.input_text.in_(
                        request_data["list_1"] + request_data["list_2"]
                    )
                )
            )

        engine.dispose()