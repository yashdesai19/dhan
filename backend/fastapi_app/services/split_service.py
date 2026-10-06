"""Business logic, financial calculations, and database transactions for DHAN Splits."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi_app.models.split import GroupMember, Settlement, SplitExpense, SplitGroup
from fastapi_app.models.transaction import Transaction
from fastapi_app.models.user import User
from fastapi_app.schemas.split import (
    GroupCreate,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdate,
    PersonBalance,
    PersonResponse,
    PositionResponse,
    SettlementCreate,
    SettlementResponse,
    SplitExpenseCreate,
    SplitExpenseResponse,
    SplitExpenseUpdate,
    SplitItemInput,
)
from fastapi_app.services.transaction_service import _get_account_for_update


def _to_cents(amount: Decimal) -> int:
    """Convert Decimal rupee amount to integer paise (cents)."""
    return int(Decimal(str(amount)).quantize(Decimal("0.01")) * 100)


def _from_cents(cents: int) -> Decimal:
    """Convert integer paise (cents) to Decimal rupee amount."""
    return (Decimal(cents) / Decimal("100")).quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# Split Methods Math (Exact Decimal Precision)
# ---------------------------------------------------------------------------


def compute_shares(
    method: str,
    amount: Decimal,
    member_ids: list[uuid.UUID],
    included: list[uuid.UUID] | None = None,
    exact: dict[str, Decimal] | None = None,
    percentages: dict[str, Decimal] | None = None,
    shares_input: dict[str, Decimal] | None = None,
    items: list[SplitItemInput] | None = None,
) -> dict[str, Decimal]:
    """Compute member shares for any of the 5 DHAN split methods."""
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Split expense amount must be greater than zero.",
        )
    if not member_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one group member must participate in the split.",
        )

    out: dict[str, Decimal] = {}
    total_cents = _to_cents(amount)

    # 1. EQUAL SPLIT
    if method == "equal":
        active_ids = [m for m in member_ids if not included or m in included]
        if not active_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one member must be included in the equal split.",
            )
        n = len(active_ids)
        base_cents = total_cents // n
        rem_cents = total_cents % n

        for m in member_ids:
            if m in active_ids:
                cents = base_cents + (1 if rem_cents > 0 else 0)
                if rem_cents > 0:
                    rem_cents -= 1
                out[str(m)] = _from_cents(cents)
            else:
                out[str(m)] = Decimal("0.00")

    # 2. EXACT AMOUNTS
    elif method == "exact":
        if not exact:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exact amounts mapping is required for exact split.",
            )
        exact_cents_sum = 0
        for m in member_ids:
            val = exact.get(str(m), Decimal("0.00"))
            val = Decimal(str(val)).quantize(Decimal("0.01"))
            if val < Decimal("0.00"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Exact amount for member '{m}' cannot be negative.",
                )
            out[str(m)] = val
            exact_cents_sum += _to_cents(val)

        if exact_cents_sum != total_cents:
            sum_dec = _from_cents(exact_cents_sum)
            diff_dec = amount - sum_dec
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sum of exact shares ({sum_dec}) must equal total amount ({amount}). Difference: {diff_dec}",
            )

    # 3. PERCENTAGE SPLIT
    elif method == "percentage":
        if not percentages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Percentages mapping is required for percentage split.",
            )
        pct_sum = Decimal("0.00")
        pct_map: dict[uuid.UUID, Decimal] = {}
        for m in member_ids:
            val = Decimal(str(percentages.get(str(m), 0)))
            if val < Decimal("0.00") or val > Decimal("100.00"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Percentage for member '{m}' must be between 0 and 100.",
                )
            pct_map[m] = val
            pct_sum += val

        if pct_sum != Decimal("100.00") and pct_sum != Decimal("100"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Percentages must sum to exactly 100%, got {pct_sum}%.",
            )

        # Distribute cents based on percentage
        shares_cents: dict[uuid.UUID, int] = {}
        for m in member_ids:
            p = pct_map[m]
            shares_cents[m] = int(round(float(total_cents) * (float(p) / 100.0)))

        # Rounding discrepancy reconciliation
        diff_cents = total_cents - sum(shares_cents.values())
        if diff_cents != 0:
            # Allocate difference to the member with the largest percentage
            largest_member = max(member_ids, key=lambda m: pct_map[m])
            shares_cents[largest_member] += diff_cents

        for m in member_ids:
            out[str(m)] = _from_cents(shares_cents[m])

    # 4. SHARES (WEIGHTS) SPLIT
    elif method == "shares":
        if not shares_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Share weights mapping is required for shares split.",
            )
        weights: dict[uuid.UUID, Decimal] = {}
        total_weight = Decimal("0.00")
        for m in member_ids:
            w = Decimal(str(shares_input.get(str(m), 0)))
            if w < Decimal("0.00"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Share weight for member '{m}' cannot be negative.",
                )
            weights[m] = w
            total_weight += w

        if total_weight <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Total shares weight must be greater than zero.",
            )

        assigned_cents: dict[uuid.UUID, int] = {}
        for m in member_ids:
            w = weights[m]
            assigned_cents[m] = int((Decimal(total_cents) * w) // total_weight)

        rem_cents = total_cents - sum(assigned_cents.values())
        if rem_cents > 0:
            # Allocate remainder to the member with the largest weight
            highest_weight_member = max(member_ids, key=lambda m: weights[m])
            assigned_cents[highest_weight_member] += rem_cents

        for m in member_ids:
            out[str(m)] = _from_cents(assigned_cents[m])

    # 5. ITEM-WISE SPLIT
    elif method == "itemwise":
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="List of items is required for item-wise split.",
            )
        items_total_cents = sum(_to_cents(item.amount) for item in items)
        if items_total_cents != total_cents:
            items_total_dec = _from_cents(items_total_cents)
            diff_dec = amount - items_total_dec
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sum of item amounts ({items_total_dec}) must equal expense amount ({amount}). Difference: {diff_dec}",
            )

        member_cents_accum: dict[str, int] = {str(m): 0 for m in member_ids}
        for item in items:
            item_cents = _to_cents(item.amount)
            item_members = [m for m in item.member_ids if m in member_ids]
            if not item_members:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item '{item.title}' has no valid group members assigned.",
                )
            n = len(item_members)
            b_cents = item_cents // n
            r_cents = item_cents % n
            for m in item_members:
                share_c = b_cents + (1 if r_cents > 0 else 0)
                if r_cents > 0:
                    r_cents -= 1
                member_cents_accum[str(m)] += share_c

        for m in member_ids:
            out[str(m)] = _from_cents(member_cents_accum[str(m)])

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported split method: '{method}'.",
        )

    # Final assertion: total calculated shares must exactly equal amount
    computed_sum = sum(out.values())
    if computed_sum != amount:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Financial calculation reconciliation error: computed shares ({computed_sum}) != amount ({amount})",
        )

    return out


# ---------------------------------------------------------------------------
# Group Management Service
# ---------------------------------------------------------------------------


async def _group_member_roles(db: AsyncSession, group_id: uuid.UUID) -> dict[uuid.UUID, str]:
    """{user_id: role} for everyone in the group."""
    res = await db.execute(
        select(GroupMember.user_id, GroupMember.role).where(GroupMember.group_id == group_id)
    )
    return {row.user_id: row.role for row in res}


async def create_group(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: GroupCreate,
) -> GroupResponse:
    """Create a new group and automatically enroll the creator as admin."""
    group = SplitGroup(
        name=data.name.strip(),
        description=data.description.strip(),
        currency=data.currency.strip().upper(),
        created_by_id=user_id,
    )
    db.add(group)
    await db.flush()

    # Creator is enrolled as admin
    creator_member = GroupMember(
        group_id=group.id,
        user_id=user_id,
        role="admin",
    )
    db.add(creator_member)

    # Add initial members if provided
    for m_id in data.member_ids:
        if m_id != user_id:
            # Check user exists
            u = await db.get(User, m_id)
            if u is not None:
                db.add(GroupMember(group_id=group.id, user_id=m_id, role="member"))

    await db.commit()
    return await get_group_by_id(db, user_id, group.id)


async def get_group_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
) -> GroupResponse:
    """Retrieve group details, verifying that the user is an active member or creator."""
    stmt = (
        select(SplitGroup)
        .options(selectinload(SplitGroup.members).selectinload(GroupMember.user))
        .where(SplitGroup.id == group_id)
    )
    result = await db.execute(stmt)
    group = result.scalars().first()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

    member_user_ids = {m.user_id for m in group.members}
    if user_id not in member_user_ids and group.created_by_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group.",
        )

    member_responses = [
        GroupMemberResponse(
            id=m.id,
            group_id=m.group_id,
            user_id=m.user_id,
            user_name=m.user.name,
            user_email=m.user.email,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in group.members
    ]

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        about=group.description,
        currency=group.currency,
        created_by_id=group.created_by_id,
        members=member_responses,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


async def list_groups(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[GroupResponse]:
    """List all groups that the user is a member of or created."""
    stmt = (
        select(SplitGroup)
        .join(GroupMember, GroupMember.group_id == SplitGroup.id)
        .options(selectinload(SplitGroup.members).selectinload(GroupMember.user))
        .where(GroupMember.user_id == user_id)
        .order_by(SplitGroup.created_at.desc())
    )
    result = await db.execute(stmt)
    groups = result.scalars().all()

    out: list[GroupResponse] = []
    for g in groups:
        member_responses = [
            GroupMemberResponse(
                id=m.id,
                group_id=m.group_id,
                user_id=m.user_id,
                user_name=m.user.name,
                user_email=m.user.email,
                role=m.role,
                joined_at=m.joined_at,
            )
            for m in g.members
        ]
        out.append(
            GroupResponse(
                id=g.id,
                name=g.name,
                description=g.description,
                about=g.description,
                currency=g.currency,
                created_by_id=g.created_by_id,
                members=member_responses,
                created_at=g.created_at,
                updated_at=g.updated_at,
            )
        )
    return out


async def update_group(
    db: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    data: GroupUpdate,
) -> GroupResponse:
    """Update group information (creator or admin only)."""
    group = await db.get(SplitGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    if group.created_by_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only group creator can update details."
        )

    if data.name is not None:
        group.name = data.name.strip()
    if data.description is not None:
        group.description = data.description.strip()
    if data.currency is not None:
        group.currency = data.currency.strip().upper()

    await db.commit()
    return await get_group_by_id(db, user_id, group_id)


async def delete_group(
    db: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
) -> None:
    """Delete a split group and cascade expenses and memberships."""
    group = await db.get(SplitGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    if group.created_by_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can delete this group."
        )

    await db.delete(group)
    await db.commit()


async def add_group_member(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    group_id: uuid.UUID,
    data: GroupMemberAdd,
) -> GroupMemberResponse:
    """Add a new member to the group by user_id or email (group creator or admins only)."""
    group = await db.get(SplitGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    roles = await _group_member_roles(db, group_id)
    if current_user_id not in roles and group.created_by_id != current_user_id:
        # Outsiders learn nothing about the group, not even that it exists
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    if group.created_by_id != current_user_id and roles.get(current_user_id) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group creator or a group admin can add members.",
        )

    target_user: User | None = None
    if data.user_id:
        target_user = await db.get(User, data.user_id)
    elif data.email:
        res = await db.execute(select(User).where(User.email == data.email.strip().lower()))
        target_user = res.scalars().first()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User to add as member not found."
        )

    # Check if already member
    res = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == target_user.id,
        )
    )
    if res.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this group.",
        )

    member = GroupMember(
        group_id=group_id,
        user_id=target_user.id,
        role=data.role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return GroupMemberResponse(
        id=member.id,
        group_id=member.group_id,
        user_id=member.user_id,
        user_name=target_user.name,
        user_email=target_user.email,
        role=member.role,
        joined_at=member.joined_at,
    )


async def remove_group_member(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    group_id: uuid.UUID,
    member_user_id: uuid.UUID,
) -> None:
    """Remove a member from the group."""
    group = await db.get(SplitGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    if group.created_by_id != current_user_id and current_user_id != member_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot remove this member."
        )

    res = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == member_user_id,
        )
    )
    member = res.scalars().first()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this group."
        )

    await db.delete(member)
    await db.commit()


# ---------------------------------------------------------------------------
# Split Expense Operations
# ---------------------------------------------------------------------------


async def create_split_expense(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    data: SplitExpenseCreate,
) -> SplitExpenseResponse:
    """Create a split expense using one of the five split methods."""
    paid_by_id = data.paid_by_id or current_user_id

    # 1. Resolve members
    member_ids: list[uuid.UUID] = list(data.member_ids)
    if data.group_id:
        group = await db.get(SplitGroup, data.group_id)
        if group is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

        # Check membership
        all_group_members = list(await _group_member_roles(db, data.group_id))
        if current_user_id not in all_group_members and group.created_by_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized in this group."
            )

        if not member_ids:
            member_ids = all_group_members

        # Only group members can pay or share a group expense
        outsiders = {paid_by_id, *member_ids} - set(all_group_members)
        if outsiders:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The payer and everyone sharing a group expense must be group members.",
            )
    elif paid_by_id != current_user_id:
        # Outside a group you can only record what you paid; others record their own payments
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Without a group, the payer must be you.",
        )

    if not member_ids:
        # Default to payer and current user if peer-to-peer
        member_ids = [current_user_id]
        if paid_by_id not in member_ids:
            member_ids.append(paid_by_id)

    # 2. Compute shares
    calculated_shares = compute_shares(
        method=data.split_type,
        amount=data.amount,
        member_ids=member_ids,
        included=data.included,
        exact=data.exact,
        percentages=data.percentages,
        shares_input=data.shares_input,
        items=data.items,
    )

    # Serialize shares to JSON-compatible strings
    serialized_shares = {k: str(v) for k, v in calculated_shares.items()}

    expense = SplitExpense(
        group_id=data.group_id,
        title=data.title.strip(),
        amount=data.amount,
        paid_by_id=paid_by_id,
        split_type=data.split_type,
        shares=serialized_shares,
        split_details={"method": data.display_method} if data.display_method else None,
        date=data.date or datetime.now(UTC),
        notes=data.notes,
    )
    db.add(expense)
    if data.account_id is not None:
        # Paid from one of your accounts: the money leaves it, but it isn't spending
        if paid_by_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account can only be charged for an expense you paid.",
            )
        account = await _get_account_for_update(db, current_user_id, data.account_id)
        await db.flush()
        db.add(
            Transaction(
                user_id=current_user_id,
                account_id=account.id,
                amount=data.amount,
                type="split",
                description=data.title.strip(),
                transaction_date=expense.date,
                notes=data.notes or "",
                split_expense_id=expense.id,
            )
        )
        account.balance = Decimal(str(account.balance)) - data.amount
    await db.commit()
    await db.refresh(expense)

    paid_by_user = await db.get(User, paid_by_id)
    return SplitExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        title=expense.title,
        amount=expense.amount,
        paid_by_id=expense.paid_by_id,
        paid_by_name=paid_by_user.name if paid_by_user else "Unknown",
        split_type=expense.split_type,
        display_method=(expense.split_details or {}).get("method"),
        shares=calculated_shares,
        date=expense.date,
        notes=expense.notes,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )


async def get_split_expense(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    expense_id: uuid.UUID,
) -> SplitExpenseResponse:
    """Retrieve an individual split expense."""
    stmt = (
        select(SplitExpense)
        .options(selectinload(SplitExpense.paid_by))
        .where(SplitExpense.id == expense_id)
    )
    res = await db.execute(stmt)
    exp = res.scalars().first()
    if exp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Split expense not found."
        )

    # Check permission (must be payer, or mentioned in shares, or in group)
    shares_keys = set(exp.shares.keys())
    if str(current_user_id) not in shares_keys and exp.paid_by_id != current_user_id:
        if exp.group_id:
            m_res = await db.execute(
                select(GroupMember).where(
                    GroupMember.group_id == exp.group_id,
                    GroupMember.user_id == current_user_id,
                )
            )
            if m_res.scalars().first() is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    shares_dec = {k: Decimal(str(v)) for k, v in exp.shares.items()}
    return SplitExpenseResponse(
        id=exp.id,
        group_id=exp.group_id,
        title=exp.title,
        amount=exp.amount,
        paid_by_id=exp.paid_by_id,
        paid_by_name=exp.paid_by.name if exp.paid_by else "Unknown",
        split_type=exp.split_type,
        display_method=(exp.split_details or {}).get("method"),
        shares=shares_dec,
        date=exp.date,
        notes=exp.notes,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
    )


async def update_split_expense(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    expense_id: uuid.UUID,
    data: SplitExpenseUpdate,
) -> SplitExpenseResponse:
    """Update title or notes of an existing split expense."""
    exp = await db.get(SplitExpense, expense_id)
    if exp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Split expense not found."
        )
    if exp.paid_by_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only payer can edit this expense."
        )

    if data.title is not None:
        exp.title = data.title.strip()
    if data.notes is not None:
        exp.notes = data.notes.strip()
    if data.date is not None:
        exp.date = data.date

    await db.commit()
    await db.refresh(exp)
    return await get_split_expense(db, current_user_id, expense_id)


async def delete_split_expense(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    expense_id: uuid.UUID,
) -> None:
    """Delete a split expense."""
    exp = await db.get(SplitExpense, expense_id)
    if exp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Split expense not found."
        )
    if exp.paid_by_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only payer can delete this expense."
        )

    # Put back what its payment took from the payer's account
    linked = await db.execute(select(Transaction).where(Transaction.split_expense_id == exp.id))
    for tx in linked.scalars().all():
        account = await _get_account_for_update(db, tx.user_id, tx.account_id)
        account.balance = Decimal(str(account.balance)) + tx.amount
        await db.delete(tx)
    await db.delete(exp)
    await db.commit()


# ---------------------------------------------------------------------------
# Balance & Settlement Calculations
# ---------------------------------------------------------------------------


async def calculate_balances(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    group_id: uuid.UUID | None = None,
) -> PositionResponse:
    """Compute overall pairwise balances and net position for the authenticated user.

    Strictly applies DHAN domain math:
    - Expenses you paid: others owe you their share (+).
    - Expenses others paid: you owe them your share (-).
    - Settlements you paid: debt decreases (+).
    - Settlements you received: debt decreases (-).
    """
    # 1. Fetch the expenses this user paid or has a share in (not every user's)
    stmt = select(SplitExpense).where(
        or_(
            SplitExpense.paid_by_id == current_user_id,
            SplitExpense.shares.has_key(str(current_user_id)),
        )
    )
    if group_id:
        stmt = stmt.where(SplitExpense.group_id == group_id)
    exp_res = await db.execute(stmt)
    expenses = exp_res.scalars().all()

    # 2. Pairwise balance map: target_user_id -> Decimal net balance
    balances: dict[uuid.UUID, Decimal] = {}

    for e in expenses:
        shares = {uuid.UUID(k): Decimal(str(v)) for k, v in e.shares.items()}
        if e.paid_by_id == current_user_id:
            for uid, s_amt in shares.items():
                if uid != current_user_id and s_amt > Decimal("0.00"):
                    balances[uid] = balances.get(uid, Decimal("0.00")) + s_amt
        else:
            mine = shares.get(current_user_id, Decimal("0.00"))
            if mine > Decimal("0.00"):
                balances[e.paid_by_id] = balances.get(e.paid_by_id, Decimal("0.00")) - mine

    # 3. Fetch completed settlements
    set_stmt = select(Settlement).where(
        Settlement.status == "completed",
        or_(
            Settlement.payer_id == current_user_id,
            Settlement.payee_id == current_user_id,
        ),
    )
    if group_id:
        set_stmt = set_stmt.where(Settlement.group_id == group_id)
    set_res = await db.execute(set_stmt)
    settlements = set_res.scalars().all()

    for s in settlements:
        if s.payer_id == current_user_id:
            # I paid payee, reducing my debt to them (increases balance)
            balances[s.payee_id] = balances.get(s.payee_id, Decimal("0.00")) + s.amount
        elif s.payee_id == current_user_id:
            # Payer paid me, reducing their debt to me (decreases balance)
            balances[s.payer_id] = balances.get(s.payer_id, Decimal("0.00")) - s.amount

    # 4. Compute overall position
    owed = Decimal("0.00")
    owe = Decimal("0.00")
    by_person: dict[str, Decimal] = {}
    people_balances: list[PersonBalance] = []

    for uid, bal in balances.items():
        bal_quant = bal.quantize(Decimal("0.01"))
        by_person[str(uid)] = bal_quant
        if bal_quant > Decimal("0.00"):
            owed += bal_quant
        elif bal_quant < Decimal("0.00"):
            owe += abs(bal_quant)

        user_obj = await db.get(User, uid)
        people_balances.append(
            PersonBalance(
                user_id=uid,
                name=user_obj.name if user_obj else "Unknown",
                email=user_obj.email if user_obj else "",
                balance=bal_quant,
            )
        )

    net = owed - owe
    return PositionResponse(
        owed=owed.quantize(Decimal("0.01")),
        owe=owe.quantize(Decimal("0.01")),
        net=net.quantize(Decimal("0.01")),
        by_person=by_person,
        people_balances=people_balances,
    )


async def create_settlement(
    db: AsyncSession,
    current_user_id: uuid.UUID,
    data: SettlementCreate,
) -> SettlementResponse:
    """Record a debt settlement between the current user and a peer.

    direction="paid": the current user paid the other person. direction="received": the other
    person paid the current user, which can only reduce what they owe, never add to it.
    """
    if current_user_id == data.payee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot settle a debt with yourself.",
        )

    payee = await db.get(User, data.payee_id)
    if payee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payee user not found.")

    if data.group_id is not None:
        roles = await _group_member_roles(db, data.group_id)
        if current_user_id not in roles:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
        if data.payee_id not in roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The payee is not a member of this group.",
            )

    if data.direction == "received":
        payer_id, payee_id = data.payee_id, current_user_id
    else:
        payer_id, payee_id = current_user_id, data.payee_id

    # Duplicate settlement prevention within 10 seconds
    recent_cutoff = datetime.now(UTC) - timedelta(seconds=10)
    dup_stmt = select(Settlement).where(
        Settlement.payer_id == payer_id,
        Settlement.payee_id == payee_id,
        Settlement.amount == data.amount,
        Settlement.group_id == data.group_id,
        Settlement.created_at >= recent_cutoff,
    )
    dup_res = await db.execute(dup_stmt)
    if dup_res.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate settlement detected. A matching payment was just recorded.",
        )

    settlement = Settlement(
        group_id=data.group_id,
        payer_id=payer_id,
        payee_id=payee_id,
        amount=data.amount,
        status="completed",
        method=data.method,
        notes=data.notes,
        settled_at=datetime.now(UTC),
    )
    db.add(settlement)
    await db.commit()
    await db.refresh(settlement)

    names = await _user_names(db, {payer_id, payee_id})
    return _settlement_response(settlement, names)


async def _user_names(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    res = await db.execute(select(User.id, User.name).where(User.id.in_(ids)))
    return {row.id: row.name for row in res}


def _settlement_response(s: Settlement, names: dict[uuid.UUID, str]) -> SettlementResponse:
    return SettlementResponse(
        id=s.id,
        group_id=s.group_id,
        payer_id=s.payer_id,
        payer_name=names.get(s.payer_id, "Unknown"),
        payee_id=s.payee_id,
        payee_name=names.get(s.payee_id, "Unknown"),
        amount=s.amount,
        status=s.status,
        method=s.method,
        notes=s.notes,
        settled_at=s.settled_at,
        created_at=s.created_at,
    )


async def list_settlements(
    db: AsyncSession, current_user_id: uuid.UUID
) -> list[SettlementResponse]:
    """Settlements the user paid or received, newest first. Nobody else's."""
    res = await db.execute(
        select(Settlement)
        .where(or_(Settlement.payer_id == current_user_id, Settlement.payee_id == current_user_id))
        .order_by(Settlement.created_at.desc())
    )
    settlements = list(res.scalars().all())
    names = await _user_names(db, {u for s in settlements for u in (s.payer_id, s.payee_id)})
    return [_settlement_response(s, names) for s in settlements]


async def delete_settlement(
    db: AsyncSession, current_user_id: uuid.UUID, settlement_id: uuid.UUID
) -> None:
    """Undo a settlement. Only the two people it is between can; to anyone else it's not found."""
    settlement = await db.get(Settlement, settlement_id)
    if settlement is None or current_user_id not in (settlement.payer_id, settlement.payee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found.")
    await db.delete(settlement)
    await db.commit()


async def list_split_expenses(
    db: AsyncSession, current_user_id: uuid.UUID
) -> list[SplitExpenseResponse]:
    """Expenses the user can see: in their groups, paid by them, or with a share for them."""
    my_groups = select(GroupMember.group_id).where(GroupMember.user_id == current_user_id)
    res = await db.execute(
        select(SplitExpense)
        .where(
            or_(
                SplitExpense.group_id.in_(my_groups),
                SplitExpense.paid_by_id == current_user_id,
                SplitExpense.shares.has_key(str(current_user_id)),
            )
        )
        .order_by(SplitExpense.date.desc(), SplitExpense.created_at.desc())
    )
    expenses = list(res.scalars().all())
    names = await _user_names(db, {e.paid_by_id for e in expenses})
    return [
        SplitExpenseResponse(
            id=e.id,
            group_id=e.group_id,
            title=e.title,
            amount=e.amount,
            paid_by_id=e.paid_by_id,
            paid_by_name=names.get(e.paid_by_id, "Unknown"),
            split_type=e.split_type,
            display_method=(e.split_details or {}).get("method"),
            shares={k: Decimal(str(v)) for k, v in e.shares.items()},
            date=e.date,
            notes=e.notes,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in expenses
    ]


async def list_people(
    db: AsyncSession,
    current_user_id: uuid.UUID,
) -> list[PersonResponse]:
    """People the user shares a group with. Never a directory of other registered users."""
    # Fetch all users who share a group with current user
    stmt = (
        select(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(
            GroupMember.group_id.in_(
                select(GroupMember.group_id).where(GroupMember.user_id == current_user_id)
            )
        )
        .distinct()
    )
    res = await db.execute(stmt)
    users = [u for u in res.scalars().all() if u.id != current_user_id]

    tones = ["primary", "blue", "green", "sand"]
    out: list[PersonResponse] = []
    for i, u in enumerate(users):
        name_parts = u.name.split()
        initials = "".join(p[0].upper() for p in name_parts[:2]) if name_parts else "U"
        tone = tones[i % len(tones)]
        out.append(
            PersonResponse(
                id=u.id,
                name=u.name,
                email=u.email,
                initials=initials,
                avatar_tone=tone,
            )
        )
    return out
