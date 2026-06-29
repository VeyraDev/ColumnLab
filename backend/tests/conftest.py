from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models import User  # noqa: F401 - register models


def pytest_addoption(parser):
    parser.addoption("--update-golden", action="store_true", help="Regenerate golden fixtures")


@pytest.fixture
def db_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user(db_session):
    from app.core.security import hash_password

    user = User(username="tester", email="tester@example.com", password_hash=hash_password("secret12"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_engine, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _resolve_path(self, relative: str):
        path = tmp_path / relative
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr("app.core.config.Settings.resolve_path", _resolve_path)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
