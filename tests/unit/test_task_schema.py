import pytest
from pydantic import ValidationError

from backend.app.api.tasks import TaskCreate, TaskOut, TaskDetail


def test_valid_task_create_schemas():
    for t_type in ["document", "coding", "vision"]:
        task = TaskCreate(
            title=f"Sample {t_type} task",
            task_type=t_type,
            prompt="Perform the required analysis",
            file_ids=["f_1", "f_2"],
        )
        assert task.title == f"Sample {t_type} task"
        assert task.task_type == t_type
        assert len(task.file_ids) == 2


def test_invalid_task_type_rejection():
    with pytest.raises(ValidationError):
        TaskCreate(
            title="Invalid task",
            task_type="invalid_type",  # Not in ('document', 'coding', 'vision')
            prompt="Do something",
        )


def test_empty_fields_rejection():
    with pytest.raises(ValidationError):
        TaskCreate(
            title="",  # Empty title
            task_type="document",
            prompt="Valid prompt",
        )

    with pytest.raises(ValidationError):
        TaskCreate(
            title="Valid title",
            task_type="document",
            prompt="",  # Empty prompt
        )
