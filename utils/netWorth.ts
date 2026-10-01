// Net worth (spec §6: ₹2,18,680 = assets ₹2,62,080 − liabilities ₹43,400).
import type { Account, Asset, Liability, MonthHistory, MonthKey, Rupees } from '@/types/domain';
import type { IconName } from '@/components/icons/paths';
import { dayMonth } from './dates';

export interface NetWorthRow {
  id: string;
  name: string;
  note: string;
  icon: IconName;
  value: Rupees;
}

export interface NetWorth {
  assets: NetWorthRow[];
  liabilities: NetWorthRow[];
  totalAssets: Rupees;
  totalLiabilities: Rupees;
  net: Rupees;
}

export function netWorth(
  accounts: readonly Account[],
  assets: readonly Asset[],
  liabilities: readonly Liability[],
): NetWorth {
  const live = accounts.filter((a) => !a.archived && a.includeInTotal);
  const banks = live.filter((a) => a.type === 'bank' || a.type === 'savings');
  const cash = live.filter((a) => a.type === 'cash' || a.type === 'wallet' || a.type === 'custom');
  const credit = live.filter((a) => a.type === 'credit');
  const sum = (xs: readonly { balance: number }[]) => xs.reduce((s, a) => s + a.balance, 0);
  const short = (xs: readonly Account[]) => xs.map((a) => a.name.split(' ')[0]).join(', ');

  const assetRows: NetWorthRow[] = [
    { id: 'banks', name: 'Bank accounts', note: short(banks), icon: 'bank', value: sum(banks) },
    { id: 'cash', name: 'Cash and wallets', note: short(cash), icon: 'cash', value: sum(cash) },
    ...assets.map((a) => ({
      id: a.id,
      name: a.name,
      note: a.note ? `${a.note} · updated ${dayMonth(a.updatedAt)}` : `Updated ${dayMonth(a.updatedAt)}`,
      icon: a.icon,
      value: a.value,
    })),
  ];
  const liabilityRows: NetWorthRow[] = [
    ...credit.map((a) => ({
      id: a.id,
      name: a.name,
      note: a.dueDate ? `Due ${dayMonth(a.dueDate)}` : 'Card balance',
      icon: 'card' as IconName,
      value: Math.max(0, -a.balance),
    })),
    ...liabilities.map((l) => ({ id: l.id, name: l.name, note: l.note, icon: l.icon, value: l.value })),
  ];
  const totalAssets = assetRows.reduce((s, r) => s + r.value, 0);
  const totalLiabilities = liabilityRows.reduce((s, r) => s + r.value, 0);
  return {
    assets: assetRows,
    liabilities: liabilityRows,
    totalAssets,
    totalLiabilities,
    net: totalAssets - totalLiabilities,
  };
}

/** Closed months from history, then the live month. */
export function netWorthSeries(
  history: readonly MonthHistory[],
  current: { month: MonthKey; value: Rupees },
) {
  return [...history.map((h) => ({ month: h.month, value: h.netWorth })), current];
}
