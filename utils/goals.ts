// Goal maths (spec §6: ₹98,000 saved across 3 goals, ₹2,52,000 to go).
import type { Goal, Rupees } from '@/types/domain';
import { daysBetween, monthsUntil } from './dates';
import { inr, percent } from './format';

export type GoalStatus = 'onTrack' | 'behind' | 'done';

export interface GoalProgress {
  saved: Rupees;
  left: Rupees;
  pct: number;
  monthsLeft: number;
  /** Rupees a month needed to hit the target date. */
  monthly: Rupees;
  status: GoalStatus;
  /** Row pill copy: "Behind", "On track", or "₹12,500/mo". */
  pill: string;
}

export function goalSaved(goal: Goal): Rupees {
  return goal.contributions.reduce((s, c) => s + c.amount, 0);
}

export function goalProgress(goal: Goal, today: string): GoalProgress {
  const saved = goalSaved(goal);
  const left = Math.max(0, goal.target - saved);
  const pct = percent(saved, goal.target);
  const monthsLeft = Math.max(1, monthsUntil(today, goal.targetDate));
  const monthly = Math.round(left / monthsLeft);
  const span = Math.max(1, daysBetween(goal.createdAt, goal.targetDate));
  const elapsed = Math.min(span, Math.max(0, daysBetween(goal.createdAt, today)));
  const expected = (goal.target * elapsed) / span;
  const status: GoalStatus = left === 0 ? 'done' : saved >= expected ? 'onTrack' : 'behind';
  const pill =
    status === 'done'
      ? 'Done'
      : status === 'behind'
        ? 'Behind'
        : pct >= 50
          ? 'On track'
          : `${inr(monthly)}/mo`;
  return { saved, left, pct, monthsLeft, monthly, status, pill };
}

export function goalsTotals(goals: readonly Goal[]): { saved: Rupees; left: Rupees; count: number } {
  let saved = 0;
  let left = 0;
  for (const g of goals) {
    const s = goalSaved(g);
    saved += s;
    left += Math.max(0, g.target - s);
  }
  return { saved, left, count: goals.length };
}
