import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


from app.database import Base, get_session
from app.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_session():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    # I don't use context manager, so i don't connect to main db
    test_client = TestClient(app)

    yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_create_payload_returns_id(client):
    response = client.post(
        "/payload",
        json={
            "list_1": ["first", "second"],
            "list_2": ["other", "another"],
        },
    )

    assert response.status_code == 200
    assert "id" in response.json()


def test_read_payload_returns_interleaved_output(client):
    create_response = client.post(
        "/payload",
        json={
            "list_1": ["first", "second"],
            "list_2": ["other", "another"],
        },
    )
    payload_id = create_response.json()["id"]

    response = client.get(f"/payload/{payload_id}")

    assert response.status_code == 200
    assert response.json() == {
        "output": "FIRST, OTHER, SECOND, ANOTHER"
    }


def test_identical_request_reuses_payload_id(client):
    request_data = {
        "list_1": ["first", "second"],
        "list_2": ["other", "another"],
    }

    first_response = client.post("/payload", json=request_data)
    second_response = client.post("/payload", json=request_data)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["id"] == second_response.json()["id"]


def test_transform_results_are_cached(client, monkeypatch):
    calls = []

    def fake_transform(value: str) -> str:
        calls.append(value)
        return value.upper()

    monkeypatch.setattr(
        "app.services.payload_service.transform",
        fake_transform,
    )

    first_response = client.post(
        "/payload",
        json={
            "list_1": ["hello"],
            "list_2": ["world"],
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/payload",
        json={
            "list_1": ["hello"],
            "list_2": ["python"],
        },
    )
    assert second_response.status_code == 200

    # "hello" is transformed only once.
    # "world" and "python" are each transformed once.
    assert calls == ["hello", "world", "python"]


def test_different_list_lengths_return_422(client):
    response = client.post(
        "/payload",
        json={
            "list_1": ["first", "second"],
            "list_2": ["other"],
        },
    )

    assert response.status_code == 422


def test_unknown_payload_returns_404(client):
    response = client.get(
        "/payload/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


def test_empty_lists_return_empty_output(client):
    create_response = client.post(
        "/payload",
        json={
            "list_1": [],
            "list_2": [],
        },
    )

    assert create_response.status_code == 200

    payload_id = create_response.json()["id"]
    read_response = client.get(f"/payload/{payload_id}")

    assert read_response.status_code == 200
    assert read_response.json() == {"output": ""}





