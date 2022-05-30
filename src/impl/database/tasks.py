# pyright: reportGeneralTypeIssues=false
# pyright: reportIncompatibleVariableOverride=false

from datetime import datetime
from typing import Any, Optional

from ormar import JSON, BigInteger, Boolean, DateTime, Model, String

from .metadata import database, metadata


class ScheduledTask(Model):
    class Meta:
        database = database
        metadata = metadata
        tablename = "tasks"

    id: int = BigInteger(auto_increment=True, primary_key=True)
    channel: str = String(max_length=255, default="default")
    execute_at: datetime = DateTime()
    repeat: bool = Boolean(default=False)
    repeat_every: Optional[int] = BigInteger(default=None)
    repeat_until: Optional[datetime] = DateTime(default=None)
    data: Any = JSON(default={})
    key: Optional[str] = String(max_length=255, default=None)
