"""Data access repositories package."""

from fastapi_app.repositories.base import BaseRepository
from fastapi_app.repositories.user import UserRepository

__all__ = ["BaseRepository", "UserRepository"]
