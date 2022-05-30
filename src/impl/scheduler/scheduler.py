from asyncio import Task, create_task, sleep
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Final, Optional

from src.impl.database import ScheduledTask

LOADER_INTERVAL: Final[int] = 60 * 60
LOADER_BUFFER: Final[int] = LOADER_INTERVAL // 20


class Scheduler:
    def __init__(self, dispatch: Callable[[int, str, Any], Coroutine[None, None, None]]) -> None:
        self._loader: Optional[Task[None]] = None
        self._scheduled_tasks: dict[int, Task[None]] = {}

        self._dispatch = dispatch

    async def _run(self, task: ScheduledTask) -> None:
        print(datetime.now(), task)

        if task.repeat:
            if (
                task.repeat_until
                and task.repeat_until < datetime.now()
                and task.repeat_until != datetime.fromtimestamp(0)
            ):
                await self.unschedule(task.id)
                return

            if task.repeat_every is None or task.repeat_every == -1:
                return

            now = datetime.now().timestamp()
            next_exec = task.execute_at.timestamp()

            while next_exec < now:
                next_exec += task.repeat_every

            sleep_time = next_exec - now
        else:
            sleep_time = (task.execute_at - datetime.now()).total_seconds()

        await sleep(sleep_time)

        await self._dispatch(task.id, task.channel, task.data)

        if task.repeat:
            await sleep(0.1)
            self._scheduled_tasks[task.id] = create_task(self._run(task))
        else:
            await self.unschedule(task.id)

    def _schedule(self, task: ScheduledTask) -> None:
        if task.id in self._scheduled_tasks:
            return

        self._scheduled_tasks[task.id] = create_task(self._run(task))

    def _unschedule(self, task: ScheduledTask) -> None:
        if task.id not in self._scheduled_tasks:
            return

        self._scheduled_tasks[task.id].cancel()

    async def _load(self) -> None:
        while True:
            close_tasks = await ScheduledTask.objects.filter(
                execute_at__lt=datetime.now() + timedelta(seconds=LOADER_INTERVAL + LOADER_BUFFER)
            ).all()

            print(close_tasks)

            to_remove: list[ScheduledTask] = []

            for task in close_tasks:
                if not task.repeat and task.execute_at < datetime.now():
                    to_remove.append(task)

                self._schedule(task)

            for task in to_remove:
                await self.unschedule(task.id)

            await sleep(LOADER_INTERVAL)

    def start(self) -> None:
        self._loader = create_task(self._load())
        self._loader.add_done_callback(lambda _: exit(1))

    def stop(self) -> None:
        if self._loader is not None:
            self._loader.cancel()

    async def schedule(
        self,
        channel: str,
        execute_at: datetime,
        repeat: bool = False,
        repeat_every: Optional[int] = None,
        repeat_until: Optional[datetime] = None,
        data: Optional[Any] = None,
        key: Optional[str] = None,
    ) -> ScheduledTask:
        task = await ScheduledTask.objects.create(
            channel=channel,
            execute_at=execute_at,
            repeat=repeat,
            repeat_every=repeat_every or -1,
            repeat_until=repeat_until or datetime.fromtimestamp(0),
            data=data,
            key=key,
        )

        self._schedule(task)

        return task

    async def unschedule(self, id: int) -> None:
        task = await ScheduledTask.objects.get(id=id)
        self._unschedule(task)
        await task.delete()

    async def unschedule_by_key(self, key: str) -> None:
        tasks = await ScheduledTask.objects.filter(key=key).all()

        for task in tasks:
            self._unschedule(task)
            await task.delete()
