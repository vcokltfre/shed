from datetime import datetime
from hmac import compare_digest
from os import environ
from typing import Any, Optional

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

from src.impl.database import ScheduledTask, database
from src.impl.dispatcher import Dispatcher
from src.impl.scheduler import Scheduler

router = APIRouter(prefix="/tasks")

dispatcher = Dispatcher()
scheduler = Scheduler(dispatcher.dispatch)


class CreateAPITask(BaseModel):
    channel: str
    execute_at: datetime
    repeat: bool = False
    repeat_every: Optional[int] = None
    repeat_until: Optional[datetime] = None
    data: Optional[Any] = None
    key: Optional[str] = None


class APITask(BaseModel):
    id: int
    channel: str
    execute_at: datetime
    repeat: bool = False
    repeat_every: Optional[int] = None
    repeat_until: Optional[datetime] = None
    data: Optional[Any] = None
    key: Optional[str] = None


class ConnectPayload(BaseModel):
    channels: list[str]
    auth: str


@router.on_event("startup")  # type: ignore
async def startup() -> None:
    await database.connect()
    scheduler.start()


@router.get("/")
async def get_tasks() -> list[APITask]:
    # This is done to prevent private model fields being sent to the client.
    return [APITask(**task.dict()) for task in await ScheduledTask.objects.all()]  # type: ignore


@router.post("/")
async def create_task(task: CreateAPITask) -> APITask:
    scheduled_task = await scheduler.schedule(
        task.channel, task.execute_at, task.repeat, task.repeat_every, task.repeat_until, task.data, task.key
    )

    return APITask(**scheduled_task.dict())  # type: ignore


@router.delete("/{id}")
async def delete_task(id: int) -> None:
    await scheduler.unschedule(id)


@router.websocket("/ws")
async def websocket_tasks(websocket: WebSocket) -> None:
    auth = websocket.headers["Authorization"]

    if not compare_digest(environ["AUTH"], auth):
        await websocket.close()
        return

    await websocket.accept()

    channels: list[str] = await websocket.receive_json()

    async def dispatch(id: int, data: Any, did: int) -> None:
        await websocket.send_json(
            {
                "id": id,
                "data": data,
                "did": did,
            }
        )

    dispatcher.add_channel_handler(channels, dispatch)

    try:
        async for _msg in websocket.iter_json():
            pass
    finally:
        dispatcher.remove_channel_handler(channels)
