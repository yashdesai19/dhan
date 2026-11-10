"""FastAPI endpoints for DHAN Books."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import require_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.book import BookCreate, BookResponse
from fastapi_app.services import book_service

router = APIRouter(prefix="/books", tags=["Books"])


@router.get("", response_model=list[BookResponse])
async def list_books(
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BookResponse]:
    """List the authenticated user's business books."""
    books = await book_service.list_books(db=db, user_id=current_user.id)
    return [BookResponse.model_validate(b) for b in books]


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    payload: BookCreate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BookResponse:
    """Create a business book and its cash account."""
    book = await book_service.create_book(db=db, user_id=current_user.id, data=payload)
    return BookResponse.model_validate(book)
