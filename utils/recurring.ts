// Recurring payments (spec §6: October outgoing ₹14,391 across 9 payments; subscriptions ₹2,692 a month).
import type { MonthKey, Recurring, Rupees } from '@/types/domain';
import { addDays, monthOf } from './dates';

export const LIST_SUBSCRIPTION_FROM = 1000;

export function outgoingInMonth(items: readonly Recurring[], month: MonthKey) {
  const list = items.filter((r) => r.kind !== 'income' && monthOf(r.nextDate) === month);
  return { total: list.reduce((s, r) => s + r.amount, 0), count: list.length, items: list };
}

export function incomingInMonth(items: readonly Recurring[], month: MonthKey) {
  const list = items.filter((r) => r.kind === 'income' && monthOf(r.nextDate) === month);
  return { total: list.reduce((s, r) => s + r.amount, 0), items: list };
}

/** Bills and EMIs (not subscriptions) split into the next 7 days and the rest of the month. */
export function upcomingSplit(items: readonly Recurring[], today: string, month: MonthKey) {
  const horizon = addDays(today, 7);
  const bills = items
    .filter((r) => r.kind !== 'income' && monthOf(r.nextDate) === month)
    .sort((a, b) => a.nextDate.localeCompare(b.nextDate));
  const soon = bills.filter((r) => r.nextDate > today && r.nextDate <= horizon);
  // Bills and EMIs are listed individually; subscriptions of ₹1,000 or more are too, the rest
  // roll up into the Subscriptions row (canvas: ChatGPT Plus is listed, Netflix and others are not).
  const later = bills.filter(
    (r) => r.nextDate > horizon && (r.kind !== 'subscription' || r.amount >= LIST_SUBSCRIPTION_FROM),
  );
  return { soon, soonTotal: soon.reduce((s, r) => s + r.amount, 0), later };
}

export function subscriptions(items: readonly Recurring[]) {
  const list = items
    .filter((r) => r.kind === 'subscription')
    .sort((a, b) => a.nextDate.localeCompare(b.nextDate));
  const monthly: Rupees = list.reduce((s, r) => s + r.amount, 0);
  return { list, monthly, yearly: monthly * 12, count: list.length };
}
