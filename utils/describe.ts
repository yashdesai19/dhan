// How a transaction reads in a row: icon, tone, subtitle, signed amount and a spoken label.
import type { IconName } from '@/components/icons/paths';
import type { Account, Category, Transaction } from '@/types/domain';
import { dayMonth, time12 } from './dates';
import { inr, inrSpoken } from './format';

export interface TxView {
  icon: IconName;
  tone: 'neutral' | 'income' | 'primary';
  title: string;
  subtitle: string;
  amount: string;
  amountColor: 'ink' | 'income' | 'muted';
  note?: string;
  a11y: string;
}

export function describeTransaction(
  t: Transaction,
  categories: readonly Category[],
  accounts: readonly Account[],
  opts: { today: string; showDate?: boolean; quietTransfers?: boolean },
): TxView {
  const cat = categories.find((c) => c.id === t.categoryId);
  const acct = accounts.find((a) => a.id === t.accountId)?.name;
  const when = t.date === opts.today ? time12(t.time) : opts.showDate ? dayMonth(t.date) : '';
  const join = (...xs: (string | undefined)[]) => xs.filter(Boolean).join(' · ');

  switch (t.type) {
    case 'income':
      return {
        icon: cat?.icon === 'income' || !cat ? 'income' : cat.icon,
        tone: 'income',
        title: t.title,
        subtitle: join(t.detail ?? 'Income', acct, when),
        amount: inr(t.amount, 'plus'),
        amountColor: 'income',
        a11y: `${t.title}, income, ${inrSpoken(t.amount)}, ${acct ?? ''}`,
      };
    case 'transfer':
      return {
        icon: 'transfer',
        tone: 'neutral',
        title: t.title,
        subtitle: join('Transfer', t.detail, when),
        amount: inr(t.amount, 'none'),
        amountColor: opts.quietTransfers ? 'muted' : 'ink',
        note: opts.quietTransfers ? undefined : 'not spending',
        a11y: `${t.title}, transfer, ${inrSpoken(t.amount)}, not spending`,
      };
    case 'split':
      return {
        icon: 'users',
        tone: 'primary',
        title: t.title,
        subtitle: join(t.detail, when),
        amount: inr(t.amount, 'none'),
        amountColor: 'ink',
        note: t.lentAmount ? `you lent ${inr(t.lentAmount)}` : undefined,
        a11y: `${t.title}, split expense, ${inrSpoken(t.amount)}${t.lentAmount ? `, you lent ${inrSpoken(t.lentAmount)}` : ''}`,
      };
    default:
      return {
        icon: cat?.icon ?? 'receipt',
        tone: 'neutral',
        title: t.title,
        subtitle: join(cat?.short, acct, when),
        amount: inr(t.amount, 'minus'),
        amountColor: 'ink',
        a11y: `${t.title}, expense, ${inrSpoken(t.amount)}, ${cat?.short ?? ''}, ${acct ?? ''}`,
      };
  }
}
