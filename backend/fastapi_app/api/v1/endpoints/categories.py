"""FastAPI endpoints for DHAN Categories."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import require_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from fastapi_app.services import category_service

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryResponse])
@router.get("/", response_model=list[CategoryResponse], include_in_schema=False)
async def list_categories(
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category_type: str | None = Query(default=None, description="Filter by type (expense, income)"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
) -> list[CategoryResponse]:
    """Retrieve system categories plus user's custom categories."""
    items = await category_service.list_categories(
        db=db,
        user_id=current_user.id,
        category_type=category_type,
        is_active=is_active,
    )
    return [CategoryResponse.model_validate(item) for item in items]


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_category(
    payload: CategoryCreate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryResponse:
    """Create a new custom category for the authenticated user."""
    category = await category_service.create_category(
        db=db,
        user_id=current_user.id,
        data=payload,
    )
    return CategoryResponse.model_validate(category)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryResponse:
    """Retrieve a single category by ID (accessible if owned or system default)."""
    category = await category_service.get_category(
        db=db,
        user_id=current_user.id,
        category_id=category_id,
    )
    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryResponse:
    """Update a custom category owned by the authenticated user."""
    category = await category_service.update_category(
        db=db,
        user_id=current_user.id,
        category_id=category_id,
        data=payload,
    )
    return CategoryResponse.model_validate(category)
