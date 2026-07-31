from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.task import Task, TaskStatus, TaskPriority
from app.schemas.task import TaskCreate, TaskUpdate, TaskList


async def create_task(db: AsyncSession, data: TaskCreate, owner_id: int) -> Task:
    task = Task(**data.model_dump(), owner_id=owner_id)
    db.add(task)
    await db.flush()
    return task


async def get_task(db: AsyncSession, task_id: int, owner_id: int) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.owner_id == owner_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def list_tasks(
    db: AsyncSession,
    owner_id: int,
    page: int = 1,
    page_size: int = 20,
    status_filter: TaskStatus | None = None,
    priority_filter: TaskPriority | None = None,
) -> TaskList:
    query = select(Task).where(Task.owner_id == owner_id)
    count_query = select(func.count()).select_from(Task).where(Task.owner_id == owner_id)

    if status_filter:
        query = query.where(Task.status == status_filter)
        count_query = count_query.where(Task.status == status_filter)
    if priority_filter:
        query = query.where(Task.priority == priority_filter)
        count_query = count_query.where(Task.priority == priority_filter)

    total = (await db.execute(count_query)).scalar_one()
    tasks = (
        await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    return TaskList(items=list(tasks), total=total, page=page, page_size=page_size)


async def update_task(db: AsyncSession, task_id: int, data: TaskUpdate, owner_id: int) -> Task:
    task = await get_task(db, task_id, owner_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.flush()
    return task


async def delete_task(db: AsyncSession, task_id: int, owner_id: int) -> None:
    task = await get_task(db, task_id, owner_id)
    await db.delete(task)
