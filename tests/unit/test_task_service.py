import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.persistence.db import Base
from backend.app.services.task_service import (
    InvalidTaskPayloadError,
    TaskNotFoundError,
    TaskService,
)


@pytest.fixture
def temp_service():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionFactory()
    service = TaskService(session)

    yield service

    session.close()
    engine.dispose()


def test_service_create_and_get(temp_service):
    res = temp_service.create_task(
        title="Document Intelligence",
        task_type="document",
        prompt="Extract findings from report",
        file_ids=["f_123"],
    )
    assert res["task_id"] is not None
    assert res["status"] == "created"
    assert res["file_ids"] == ["f_123"]

    detail = temp_service.get_task(res["task_id"])
    assert detail["task_id"] == res["task_id"]
    assert detail["title"] == "Document Intelligence"


def test_service_invalid_payload_raises(temp_service):
    with pytest.raises(InvalidTaskPayloadError):
        temp_service.create_task(title="", task_type="document", prompt="valid")

    with pytest.raises(InvalidTaskPayloadError):
        temp_service.create_task(title="valid", task_type="invalid_type", prompt="valid")


def test_service_not_found_raises(temp_service):
    with pytest.raises(TaskNotFoundError):
        temp_service.get_task("nonexistent-uuid-12345")
