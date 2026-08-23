import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.persistence.db import Base
from backend.app.persistence.task_repository import TaskRepository


@pytest.fixture
def temp_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionFactory()

    yield session

    session.close()
    engine.dispose()


def test_create_and_get_task(temp_db_session):
    repo = TaskRepository(temp_db_session)
    task = repo.create(
        title="Review SOP",
        task_type="document",
        prompt="Check compliance with Safety SOP",
    )
    assert task.task_id is not None
    assert task.title == "Review SOP"
    assert task.task_type == "document"
    assert task.status == "created"
    assert task.created_at is not None

    fetched = repo.get_by_id(task.task_id)
    assert fetched is not None
    assert fetched.task_id == task.task_id
    assert fetched.prompt == "Check compliance with Safety SOP"


def test_update_task_status(temp_db_session):
    repo = TaskRepository(temp_db_session)
    task = repo.create(title="Coding test", task_type="coding", prompt="Write tests")
    
    updated = repo.update_status(task.task_id, status="running", model_used="local-coding-model")
    assert updated is not None
    assert updated.status == "running"
    assert updated.model_used == "local-coding-model"


def test_task_events_logging(temp_db_session):
    repo = TaskRepository(temp_db_session)
    task = repo.create(title="Vision analysis", task_type="vision", prompt="Inspect image")
    
    event1 = repo.add_event(task.task_id, node="Task Understanding", message="Parsed request", level="info")
    event2 = repo.add_event(task.task_id, node="Model Selection", message="Selected vision model", level="info")
    
    events = repo.get_events(task.task_id)
    assert len(events) == 2
    assert events[0].node == "Task Understanding"
    assert events[1].node == "Model Selection"
