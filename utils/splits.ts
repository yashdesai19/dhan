// Split maths (spec §6 invariants: owed ₹5,700, owe ₹1,000, net ₹4,700).
import type { GroupExpense, ID, Rupees, Settlement, SplitMethod } from '@/types/domain';

export interface SplitItem {
  id: ID;
  title: string;
  amount: Rupees;
  memberIds: ID[];
}

export interface SplitInput {
  amount: Rupees;
  memberIds: readonly ID[];
  /** equal: who is included */
  included?: Record<ID, boolean>;
  /** exact: rupees per member */
  exact?: Record<ID, Rupees>;
  /** percent: 0–100 per member */
  percent?: Record<ID, number>;
  /** shares: share count per member */
  shares?: Record<ID, number>;
  /** item-wise: each item split evenly between its members */
  items?: SplitItem[];
}

/** Splits `amount` in whole rupees; any remainder goes to the first members so totals match. */
function evenly(amount: Rupees, ids: readonly ID[]): Record<ID, Rupees> {
  const out: Record<ID, Rupees> = {};
  if (ids.length === 0) return out;
  const base = Math.floor(amount / ids.length);
  let rem = amount - base * ids.length;
  for (const id of ids) {
    out[id] = base + (rem > 0 ? 1 : 0);
    if (rem > 0) rem -= 1;
  }
  return out;
}

/** Proportional split by weights, rounded to rupees, remainder to the largest weight. */
function byWeights(amount: Rupees, weights: Record<ID, number>, ids: readonly ID[]): Record<ID, Rupees> {
  const total = ids.reduce((s, id) => s + (weights[id] ?? 0), 0);
  const out: Record<ID, Rupees> = {};
  if (total <= 0) {
    for (const id of ids) out[id] = 0;
    return out;
  }
  let assigned = 0;
  let largest: ID | undefined;
  for (const id of ids) {
    const w = weights[id] ?? 0;
    const v = Math.floor((amount * w) / total);
    out[id] = v;
    assigned += v;
    if (largest === undefined || w > (weights[largest] ?? 0)) largest = id;
  }
  if (largest !== undefined) out[largest] = (out[largest] ?? 0) + (amount - assigned);
  return out;
}

export function computeShares(method: SplitMethod, input: SplitInput): Record<ID, Rupees> {
  const ids = input.memberIds;
  switch (method) {
    case 'equal': {
      const inc = ids.filter((id) => input.included?.[id] ?? true);
      const out = evenly(input.amount, inc);
      for (const id of ids) out[id] = out[id] ?? 0;
      return out;
    }
    case 'exact': {
      const out: Record<ID, Rupees> = {};
      for (const id of ids) out[id] = Math.max(0, Math.round(input.exact?.[id] ?? 0));
      return out;
    }
    case 'percent': {
      const out: Record<ID, Rupees> = {};
      for (const id of ids) out[id] = Math.round((input.amount * (input.percent?.[id] ?? 0)) / 100);
      return out;
    }
    case 'shares':
      return byWeights(input.amount, input.shares ?? {}, ids);
    case 'itemwise': {
      const out: Record<ID, Rupees> = {};
      for (const id of ids) out[id] = 0;
      for (const item of input.items ?? []) {
        const part = evenly(item.amount, item.memberIds);
        for (const [id, v] of Object.entries(part)) out[id] = (out[id] ?? 0) + v;
      }
      return out;
    }
  }
}

export function sumShares(shares: Record<ID, Rupees>): Rupees {
  return Object.values(shares).reduce((s, v) => s + v, 0);
}

/**
 * Pairwise balance between `me` and each other person.
 * Positive = they owe you; negative = you owe them.
 */
export function pairwiseBalances(expenses: readonly GroupExpense[], me: ID): Record<ID, Rupees> {
  const out: Record<ID, Rupees> = {};
  for (const e of expenses) {
    if (e.paidBy === me) {
      for (const [id, share] of Object.entries(e.shares)) {
        if (id !== me && share > 0) out[id] = (out[id] ?? 0) + share;
      }
    } else {
      const mine = e.shares[me] ?? 0;
      if (mine > 0) out[e.paidBy] = (out[e.paidBy] ?? 0) - mine;
    }
  }
  return out;
}

export function applySettlements(
  balances: Record<ID, Rupees>,
  settlements: readonly Settlement[],
  me: ID,
): Record<ID, Rupees> {
  const out = { ...balances };
  for (const s of settlements) {
    if (s.fromId === me) out[s.toId] = (out[s.toId] ?? 0) + s.amount;
    else if (s.toId === me) out[s.fromId] = (out[s.fromId] ?? 0) - s.amount;
  }
  return out;
}

export interface Position {
  byPerson: Record<ID, Rupees>;
  owed: Rupees;
  owe: Rupees;
  net: Rupees;
}

export function position(balances: Record<ID, Rupees>): Position {
  let owed = 0;
  let owe = 0;
  for (const v of Object.values(balances)) {
    if (v > 0) owed += v;
    else owe += -v;
  }
  return { byPerson: balances, owed, owe, net: owed - owe };
}

/** Overall position across every group, after recorded settlements. */
export function overallPosition(
  expenses: readonly GroupExpense[],
  settlements: readonly Settlement[],
  me: ID,
): Position {
  return position(applySettlements(pairwiseBalances(expenses, me), settlements, me));
}

export function groupPosition(expenses: readonly GroupExpense[], groupId: ID, me: ID): Position {
  return position(
    pairwiseBalances(
      expenses.filter((e) => e.groupId === groupId),
      me,
    ),
  );
}

/** "you lent ₹9,000" / "you borrowed ₹600" for one group expense. */
export function myShareOf(e: GroupExpense, me: ID): { kind: 'lent' | 'borrowed' | 'none'; amount: Rupees } {
  const mine = e.shares[me] ?? 0;
  if (e.paidBy === me) return { kind: 'lent', amount: e.amount - mine };
  if (mine > 0) return { kind: 'borrowed', amount: mine };
  return { kind: 'none', amount: 0 };
}
