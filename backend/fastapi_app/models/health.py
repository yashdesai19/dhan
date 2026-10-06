"""Infrastructure models."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.db.base import Base, TimestampMixin


class SystemCheck(Base, TimestampMixin):
    """Minimal infrastructure model to verify Alembic & database connectivity."""

    __tablename__ = "system_checks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(50), default="fastapi")
    status: Mapped[str] = mapped_column(String(20), default="ok")
