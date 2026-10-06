"""Base repository pattern for future data access modules."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.db.base import Base


class BaseRepository[ModelType: Base]:
    """Generic base repository providing standard asynchronous CRUD utilities."""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> ModelType | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelType]:
        result = await self.session.execute(select(self.model).limit(limit).offset(offset))
        return result.scalars().all()
