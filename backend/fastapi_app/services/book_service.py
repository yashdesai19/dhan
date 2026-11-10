"""Business logic for DHAN Books."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.models.account import Account
from fastapi_app.models.book import Book
from fastapi_app.schemas.book import BookCreate


async def list_books(db: AsyncSession, user_id: uuid.UUID) -> list[Book]:
    """The user's active business books, oldest first."""
    query = (
        select(Book)
        .where(Book.user_id == user_id, Book.archived.is_(False))
        .order_by(Book.created_at)
    )
    return list((await db.execute(query)).scalars().all())


async def create_book(db: AsyncSession, user_id: uuid.UUID, data: BookCreate) -> Book:
    """Create a business book together with a cash account, so entries can start at once."""
    duplicate = select(Book.id).where(
        Book.user_id == user_id,
        func.lower(Book.name) == data.name.lower(),
        Book.archived.is_(False),
    )
    if (await db.execute(duplicate)).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A book named '{data.name}' already exists.",
        )

    book = Book(id=uuid.uuid4(), user_id=user_id, name=data.name, kind="business")
    db.add(book)
    await db.flush()

    # Account names are unique per user: an existing one with this name just isn't created
    cash_name = f"{data.name} Cash"
    taken = select(Account.id).where(
        Account.user_id == user_id,
        func.lower(Account.name) == cash_name.lower(),
        Account.archived.is_(False),
    )
    if (await db.execute(taken)).first() is None:
        db.add(Account(user_id=user_id, name=cash_name, type="cash", book_id=book.id))

    await db.commit()
    await db.refresh(book)
    return book


async def ensure_owned(db: AsyncSession, user_id: uuid.UUID, book_id: uuid.UUID) -> None:
    """Reject a book that is missing, archived or someone else's."""
    query = select(Book.id).where(
        Book.id == book_id, Book.user_id == user_id, Book.archived.is_(False)
    )
    if (await db.execute(query)).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found.")
