"""
pytest 配置文件：提供共享 fixtures。
使用 SQLite 文件（临时）数据库，每个测试函数都得到全新的数据库状态。
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models.user import User
from app.core.security import hash_password


@pytest.fixture(scope="function")
def db_engine():
    # 使用临时文件数据库（TestClient 使用 threading，in-memory 跨线程不共享）
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    os.unlink(path)


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_engine):
    """返回 TestClient，同时将 get_db 依赖替换为使用测试数据库的 session。"""
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)

    def _override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    # raise_server_exceptions=True so test failures surface cleanly
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_token(client, db_engine):
    """创建 admin 用户并返回 JWT token。"""
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    with Session() as sess:
        admin = User(
            username="admin",
            hashed_password=hash_password("admin123"),
            role="admin",
            is_active=True,
        )
        sess.add(admin)
        sess.commit()

    resp = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
