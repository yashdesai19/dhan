"""The only way DHAN AI reads financial data.

UserFinanceReader is created per request for the authenticated user and every read goes through
the existing services with that user's id, which already filter on it. The result is a plain,
JSON-safe dict (money as strings, no ids of users) holding only what the question's intent needs,
which is all a provider ever receives.
"""

import calendar
import uuid
from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.ai.intents import Intent
from fastapi_app.core.periods import local_date, month_key
from fastapi_app.models.category import Category
from fastapi_app.services import budget_service, split_service, transaction_service
from fastapi_app.services.goal_service import GoalService
from fastapi_app.services.net_worth_service import NetWorthService
from fastapi_app.services.recurring_service import RecurringService
from fastapi_app.services.report_service import Period, ReportService

RECENT_EXPENSES = 5


def month_label(year: int, month: int) -> str:
    return f"{calendar.month_name[month]} {year}"


def _money(value: Any) -> str:
    return str(value)


class UserFinanceReader:
    """Read-only view of one user's finances, shaped for DHAN AI."""

    def __init__(self, db: AsyncSession, user_id: uuid.UUID, tz: ZoneInfo, today: date) -> None:
        self._db = db
        self._user_id = user_id
        self._tz = tz
        self._today = today

    async def facts_for(self, intent: Intent, month: tuple[int, int]) -> dict[str, Any]:
        """Facts for one intent. month applies to spending and budget questions."""
        match intent:
            case Intent.SPENDING_SUMMARY:
                return await self.spending_summary(*month)
            case Intent.BUDGET_STATUS:
                return await self.budget_status(*month)
            case Intent.RECENT_EXPENSES:
                return await self.recent_expenses()
            case Intent.GOALS:
                return await self.goals()
            case Intent.RECURRING:
                return await self.recurring()
            case Intent.NET_WORTH:
                return await self.net_worth()
            case Intent.ACCOUNTS:
                return await self.accounts()
            case Intent.SPLITS:
                return await self.splits()
            case _:
                return {}

    async def spending_summary(self, year: int, month: int) -> dict[str, Any]:
        period = Period(year, month, self._tz)
        monthly = await ReportService.monthly(self._db, self._user_id, period, trend_months=1)
        categories = await ReportService.categories(self._db, self._user_id, period)
        return {
            "month": month_label(year, month),
            "income": _money(monthly.income),
            "spent": _money(monthly.spent),
            "net": _money(monthly.net),
            "savings_rate": monthly.savings_rate,
            "expense_count": monthly.expense_count,
            "categories": [
                {
                    "name": c.name,
                    "amount": _money(c.amount),
                    "share": _money(c.share),
                    "count": c.count,
                }
                for c in categories.categories
            ],
        }

    async def budget_status(self, year: int, month: int) -> dict[str, Any]:
        summary = await budget_service.get_budget_summary(
            self._db, self._user_id, month_key(year, month)
        )
        return {
            "month": month_label(year, month),
            "limit": _money(summary.limit),
            "spent": _money(summary.spent),
            "remaining": _money(summary.remaining),
            "percentage_used": summary.percentage_used,
            "tone": summary.tone,
            "categories": [
                {
                    "name": c.category_name,
                    "limit": _money(c.limit),
                    "spent": _money(c.spent),
                    "remaining": _money(c.remaining),
                    "percentage_used": c.percentage_used,
                    "tone": c.tone,
                }
                for c in summary.categories
            ],
        }

    async def recent_expenses(self) -> dict[str, Any]:
        transactions, _ = await transaction_service.list_transactions(
            self._db,
            self._user_id,
            transaction_type="expense",
            sort_by="date",
            sort_order="desc",
            limit=RECENT_EXPENSES,
        )
        category_ids = {t.category_id for t in transactions if t.category_id}
        names: dict[uuid.UUID, str] = {}
        if category_ids:
            rows = await self._db.execute(
                select(Category.id, Category.name).where(Category.id.in_(category_ids))
            )
            names = {row.id: row.name for row in rows}
        return {
            "expenses": [
                {
                    "description": t.description or "Expense",
                    "amount": _money(t.amount),
                    "date": local_date(t.transaction_date, self._tz).isoformat(),
                    "category": names.get(t.category_id) if t.category_id else None,
                }
                for t in transactions
                if t.status == "completed"
            ]
        }

    async def goals(self) -> dict[str, Any]:
        totals = await GoalService.get_goals_totals(self._db, self._user_id, self._today)
        return {
            "total_saved": _money(totals.total_saved),
            "total_left": _money(totals.total_left),
            "total_target": _money(totals.total_target),
            "count": totals.count,
            "goals": [
                {
                    "name": g.name,
                    "target": _money(g.target_amount),
                    "saved": _money(g.current_amount),
                    "pct": g.progress.pct,
                    "status": g.progress.status,
                    "pill": g.progress.pill,
                    "target_date": g.target_date.isoformat(),
                }
                for g in totals.goals
            ],
        }

    async def recurring(self) -> dict[str, Any]:
        summary = await RecurringService.get_summary(
            self._db, self._user_id, as_of_date=self._today
        )
        return {
            "month": month_label(self._today.year, self._today.month),
            "outgoing_total": _money(summary.outgoing_total),
            "outgoing_count": summary.outgoing_count,
            "incoming_total": _money(summary.incoming_total),
            "subscriptions_monthly": _money(summary.subscriptions_monthly),
            "subscriptions_yearly": _money(summary.subscriptions_yearly),
            "subscriptions_count": summary.subscriptions_count,
            "next_7_days_total": _money(summary.upcoming_soon_total),
            "next_7_days": [
                {
                    "title": p.title,
                    "amount": _money(p.amount),
                    "due": p.next_due_date.isoformat(),
                }
                for p in summary.upcoming_soon
            ],
        }

    async def net_worth(self) -> dict[str, Any]:
        nw = await NetWorthService.get_net_worth(self._db, self._user_id)
        return {
            "net_worth": _money(nw.net_worth),
            "total_assets": _money(nw.total_assets),
            "total_liabilities": _money(nw.total_liabilities),
            "assets": [{"name": r.name, "value": _money(r.value)} for r in nw.assets],
            "liabilities": [{"name": r.name, "value": _money(r.value)} for r in nw.liabilities],
        }

    async def accounts(self) -> dict[str, Any]:
        nw = await NetWorthService.get_net_worth(self._db, self._user_id)
        return {
            "net_balance": _money(nw.net_balance.total),
            "counted_accounts": nw.net_balance.count,
            "accounts": [
                {
                    "name": a.name,
                    "type": a.type,
                    "balance": _money(a.balance),
                    "included": a.included,
                }
                for a in nw.accounts
            ],
        }

    async def splits(self) -> dict[str, Any]:
        position = await split_service.calculate_balances(self._db, self._user_id)
        return {
            "owed": _money(position.owed),
            "owe": _money(position.owe),
            "net": _money(position.net),
            # Names only: other people's ids and emails never reach a provider
            "people": [
                {"name": p.name, "balance": _money(p.balance)}
                for p in sorted(position.people_balances, key=lambda p: -abs(p.balance))
                if p.balance != 0
            ],
        }
