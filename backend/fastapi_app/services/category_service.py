"""Business logic and database service for DHAN Categories."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.models.category import Category
from fastapi_app.schemas.category import CategoryCreate, CategoryUpdate


async def list_categories(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_type: str | None = None,
    is_active: bool | None = None,
) -> list[Category]:
    """List system default categories plus user's custom categories.

    Strictly excludes categories created by other users.
    """
    # Allowed: (user_id == current_user) OR (user_id is NULL) OR (is_default is TRUE)
    query = select(Category).where(
        or_(
            Category.user_id == user_id,
            Category.user_id.is_(None),
            Category.is_default.is_(True),
        )
    )

    if category_type:
        query = query.where(Category.category_type == category_type.lower().strip())

    if is_active is not None:
        query = query.where(Category.is_active.is_(is_active))

    query = query.order_by(Category.ordering.asc(), Category.name.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: CategoryCreate,
) -> Category:
    """Create a new custom user category enforcing uniqueness and ownership."""
    clean_name = data.name.strip()
    clean_type = data.category_type.lower().strip()

    # Check duplicate category name within system or user's custom categories for this type
    dup_query = select(Category).where(
        func.lower(Category.name) == clean_name.lower(),
        Category.category_type == clean_type,
        or_(
            Category.user_id == user_id,
            Category.is_default.is_(True),
            Category.user_id.is_(None),
        ),
    )
    existing = (await db.execute(dup_query)).scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A category named '{clean_name}' for type '{clean_type}' already exists.",
        )

    category = Category(
        user_id=user_id,
        name=clean_name,
        category_type=clean_type,
        icon=data.icon,
        color=data.color,
        is_default=False,
        is_active=data.is_active,
        ordering=data.ordering,
        parent_id=data.parent_id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def get_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category:
    """Retrieve a category ensuring user owns it or it is a system default."""
    query = select(Category).where(Category.id == category_id)
    result = await db.execute(query)
    category = result.scalars().first()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    # If it is owned by someone else and not a system category, deny access
    if category.user_id is not None and category.user_id != user_id and not category.is_default:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    return category


async def update_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    data: CategoryUpdate,
) -> Category:
    """Update a custom category owned by the authenticated user.

    System categories cannot be modified by regular users.
    """
    query = select(Category).where(Category.id == category_id)
    result = await db.execute(query)
    category = result.scalars().first()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    # Protect system categories from mutation
    if category.is_default or category.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Default platform categories cannot be modified.",
        )

    # Strictly enforce ownership: User A cannot modify User B's category
    if category.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    target_type = (
        data.category_type.lower().strip() if data.category_type else category.category_type
    )
    target_name = data.name.strip() if data.name else category.name

    if (data.name is not None and data.name.lower().strip() != category.name.lower()) or (
        data.category_type is not None
        and data.category_type.lower().strip() != category.category_type
    ):
        dup_query = select(Category).where(
            func.lower(Category.name) == target_name.lower(),
            Category.category_type == target_type,
            Category.id != category_id,
            or_(
                Category.user_id == user_id,
                Category.is_default.is_(True),
                Category.user_id.is_(None),
            ),
        )
        existing = (await db.execute(dup_query)).scalars().first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A category named '{target_name}' for type '{target_type}' already exists.",
            )

    if data.name is not None:
        category.name = data.name
    if data.category_type is not None:
        category.category_type = data.category_type.lower().strip()
    if data.icon is not None:
        category.icon = data.icon
    if data.color is not None:
        category.color = data.color
    if data.is_active is not None:
        category.is_active = data.is_active
    if data.ordering is not None:
        category.ordering = data.ordering

    await db.commit()
    await db.refresh(category)
    return category
