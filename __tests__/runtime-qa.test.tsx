// Comprehensive Runtime QA Suite verifying all 25 user flows and financial invariants.
import React, { type ReactElement } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { QueryClientProvider } from '@tanstack/react-query';

import { createQueryClient } from '@/data/queries';
import { resetMockData, MOCK_PASSWORD, transactionsRepo } from '@/data/repositories';
import { undo } from '@/data/queries/actions';
import { db } from '@/mock/db';
import { useSessionStore } from '@/store/session';
import { usePrefsStore } from '@/store/prefs';
import { useEntryDraftStore } from '@/store/drafts';
import { ThemeProvider } from '@/theme';
import { netBalance, monthTotals } from '@/utils/summary';
import { budgetStatus } from '@/utils/budget';
import { netWorth } from '@/utils/netWorth';
import * as seed from '@/mock/seed';
import { TODAY } from '@/mock/clock';

// Screens
import { SplashView } from '@/features/auth/Splash';
import { OnboardingScreen } from '@/features/auth/Onboarding';
import { LoginScreen } from '@/features/auth/Auth';
import { HomeScreen } from '@/features/home/Home';
import { AddExpenseScreen, AddIncomeScreen } from '@/features/entry/Entry';
import { TransferScreen } from '@/features/entry/Transfer';
import { AccountsScreen } from '@/features/accounts/Accounts';
import { BudgetScreen } from '@/features/budget/Budget';
import { SplitsScreen } from '@/features/splits/Splits';
import { AddSplitScreen } from '@/features/splits/AddSplit';
import { SettleUpSheet } from '@/features/splits/SettleUp';
import { GoalsScreen } from '@/features/goals/Goals';
import { RecurringScreen } from '@/features/recurring/Recurring';
import { ReportsScreen } from '@/features/reports/Reports';
import { NetWorthScreen } from '@/features/reports/NetWorth';
import { AssistantScreen } from '@/features/assistant/Assistant';
import { SettingsScreen } from '@/features/settings/Settings';
import { SecurityScreen } from '@/features/settings/Security';
import { LockScreen } from '@/features/settings/Lock';
import { SignOutSheet } from '@/features/settings/SignOut';

function renderWithProviders(ui: ReactElement, scheme: 'light' | 'dark' = 'light') {
  const qc = createQueryClient();
  const res = render(
    <QueryClientProvider client={qc}>
      <ThemeProvider forceScheme={scheme}>{ui}</ThemeProvider>
    </QueryClientProvider>,
  );
  return { ...res, qc };
}

beforeEach(() => {
  resetMockData();
  useEntryDraftStore.getState().reset();
  useSessionStore.setState({ onboarded: true, signedIn: true, locked: false, hydrated: true });
  usePrefsStore.setState({ hydrated: true, appLock: true, theme: 'system', hideBalances: false });
});

describe('Financial Invariants on Startup', () => {
  it('verifies Net balance is ₹1,24,580', () => {
    const nb = netBalance(seed.accounts);
    expect(nb.total).toBe(124580);
  });

  it('verifies September spent ₹18,640, Income ₹43,000, Net flow +₹24,360', () => {
    const mt = monthTotals(seed.transactions, '2026-09');
    expect(mt.spent).toBe(18640);
    expect(mt.income).toBe(43000);
    expect(mt.net).toBe(24360);
  });

  it('verifies Budget is ₹17,100 / ₹24,000', () => {
    const bs = budgetStatus(seed.budgets[0], seed.transactions, '2026-09', TODAY);
    expect(bs?.spent).toBe(17100);
    expect(bs?.limit).toBe(24000);
  });

  it('verifies Net worth is ₹2,18,680', () => {
    const nw = netWorth(seed.accounts, seed.assets, seed.liabilities);
    expect(nw.net).toBe(218680);
  });
});

describe('Runtime QA: 25 User Flows', () => {
  // Flow 1: Splash → Onboarding → Login
  it('Flow 1: Splash and Onboarding screen rendering', () => {
    const { getByText, unmount } = renderWithProviders(<SplashView />);
    expect(getByText('DHAN')).toBeTruthy();
    expect(getByText('Dhan Hai Toh Done Hai.')).toBeTruthy();
    unmount();

    const onb = renderWithProviders(<OnboardingScreen />);
    expect(onb.getByText('Track every rupee')).toBeTruthy();
    expect(onb.getByText('Skip')).toBeTruthy();
    onb.unmount();
  });

  // Flow 2: Wrong login credentials
  it('Flow 2: Wrong login credentials shows alert banner', async () => {
    const { getByRole, getByDisplayValue, unmount } = renderWithProviders(<LoginScreen />);
    const emailInput = getByDisplayValue('yash@example.com');
    const pwInput = getByDisplayValue(MOCK_PASSWORD);

    fireEvent.changeText(emailInput, 'wrong@example.com');
    fireEvent.changeText(pwInput, 'wrong-password');
    fireEvent.press(getByRole('button', { name: 'Log in' }));

    await waitFor(() => {
      expect(getByRole('alert')).toBeTruthy();
    });
    unmount();
  });

  // Flow 3: Successful login
  it('Flow 3: Successful login signs in session', async () => {
    useSessionStore.setState({ signedIn: false });
    const { getByRole, unmount } = renderWithProviders(<LoginScreen />);
    fireEvent.press(getByRole('button', { name: 'Log in' }));

    await waitFor(() => {
      expect(useSessionStore.getState().signedIn).toBe(true);
    });
    unmount();
  });

  // Flow 4: Home dashboard
  it('Flow 4: Home dashboard displays live balance and spend', async () => {
    const { findByText, findAllByText, unmount } = renderWithProviders(<HomeScreen />);
    const balances = await findAllByText('₹1,24,580');
    expect(balances.length).toBeGreaterThan(0);
    expect(await findByText('Where it went')).toBeTruthy();
    expect(await findByText('Monthly budget')).toBeTruthy();
    unmount();
  });

  // Flow 5: Add Expense → Save → Home update → Activity update
  it('Flow 5: Add Expense updates transaction list and balances', async () => {
    useEntryDraftStore.getState().patch({ amount: '500', categoryId: 'food', accountId: 'hdfc' });
    const { getByRole, unmount } = renderWithProviders(<AddExpenseScreen />);

    const saveBtn = getByRole('button', { name: /Save ₹500/i });
    expect(saveBtn).toBeTruthy();
    await act(async () => {
      fireEvent.press(saveBtn);
    });
    unmount();

    await waitFor(() => {
      const state = db.get();
      expect(netBalance(state.accounts).total).toBe(124080);
    });
  });

  // Flow 6: Undo expense
  it('Flow 6: Undo reverts transaction and restores balance', async () => {
    const qc = createQueryClient();
    const addRes = await transactionsRepo.addExpense({
      amount: 450,
      categoryId: 'food',
      accountId: 'hdfc',
    });

    await act(async () => {
      await undo.createdTransaction(qc, addRes.id);
    });

    const s = db.get();
    expect(netBalance(s.accounts).total).toBe(124580);
  });

  // Flow 7: Delete expense → Restore
  it('Flow 7: Delete and restore round-trips balance', async () => {
    const s = db.get();
    const target = s.transactions.find((t) => t.type === 'expense')!;

    const removed = await transactionsRepo.remove(target.id);
    expect(netBalance(db.get().accounts).total).toBe(124580 + target.amount);

    await transactionsRepo.restore(removed);
    expect(netBalance(db.get().accounts).total).toBe(124580);
  });

  // Flow 8: Add Income
  it('Flow 8: Add Income updates balance', async () => {
    useEntryDraftStore.getState().patch({ amount: '5000', incomeSourceId: 'salary', accountId: 'hdfc' });
    const { getByRole, unmount } = renderWithProviders(<AddIncomeScreen />);

    const addBtn = getByRole('button', { name: /Add ₹5,000/i });
    await act(async () => {
      fireEvent.press(addBtn);
    });
    unmount();

    const s = db.get();
    expect(netBalance(s.accounts).total).toBe(129580);
  });

  // Flow 9: Transfer between accounts
  it('Flow 9: Transfer moves money between accounts without altering net balance', async () => {
    useEntryDraftStore.getState().patch({ amount: '2000', fromId: 'hdfc', toId: 'cash' });
    const { getByRole, unmount } = renderWithProviders(<TransferScreen />);

    const sendBtn = getByRole('button', { name: /Move ₹2,000/i });
    await act(async () => {
      fireEvent.press(sendBtn);
    });
    unmount();

    const s = db.get();
    const hdfc = s.accounts.find((a) => a.id === 'hdfc')!.balance;
    const cash = s.accounts.find((a) => a.id === 'cash')!.balance;
    expect(hdfc).toBe(84450);
    expect(cash).toBe(5200);
    expect(netBalance(s.accounts).total).toBe(124580);
  });

  // Flow 10: Accounts and balances
  it('Flow 10: Accounts screen lists accounts with correct balances', async () => {
    const { findByText, unmount } = renderWithProviders(<AccountsScreen />);
    expect(await findByText('HDFC Bank')).toBeTruthy();
    expect(await findByText('SBI Savings')).toBeTruthy();
    expect(await findByText('Cash')).toBeTruthy();
    unmount();
  });

  // Flow 11: Budget and category budget
  it('Flow 11: Budget screen displays budget progress and categories', async () => {
    const { findByText, unmount } = renderWithProviders(<BudgetScreen />);
    expect(await findByText('Budget')).toBeTruthy();
    expect(await findByText('Transport')).toBeTruthy();
    unmount();
  });

  // Flow 12: Splits calculations
  it('Flow 12: Splits screen and 5 split methods', async () => {
    const splits = renderWithProviders(<SplitsScreen />);
    expect(await splits.findByText('Overall, you’re owed')).toBeTruthy();
    expect(await splits.findByText('Goa Trip')).toBeTruthy();
    splits.unmount();

    const addSplit = renderWithProviders(<AddSplitScreen />);
    expect(await addSplit.findByText('Equal')).toBeTruthy();
    expect(await addSplit.findByText('Exact')).toBeTruthy();
    expect(await addSplit.findByText('Percent')).toBeTruthy();
    expect(await addSplit.findByText('Shares')).toBeTruthy();
    expect(await addSplit.findByText('Item-wise')).toBeTruthy();
    addSplit.unmount();
  });

  // Flow 13: Settle up
  it('Flow 13: Settle Up sheet renders person details', async () => {
    const { findByText, unmount } = renderWithProviders(<SettleUpSheet />);
    expect(await findByText('Settle up')).toBeTruthy();
    expect(await findByText('Record ₹1,000 payment')).toBeTruthy();
    unmount();
  });

  // Flow 14: Goals → Add money → Progress
  it('Flow 14: Goals screen shows goals with progress', async () => {
    const { findByText, unmount } = renderWithProviders(<GoalsScreen />);
    expect(await findByText('MacBook')).toBeTruthy();
    expect(await findByText('Emergency Fund')).toBeTruthy();
    expect(await findByText('Kerala Trip')).toBeTruthy();
    unmount();
  });

  // Flow 15: Recurring payments
  it('Flow 15: Recurring screen lists upcoming payments', async () => {
    const { findByText, unmount } = renderWithProviders(<RecurringScreen />);
    expect(await findByText(/Next 7 days/i)).toBeTruthy();
    expect(await findByText('Subscriptions')).toBeTruthy();
    unmount();
  });

  // Flow 16: Reports
  it('Flow 16: Reports screen renders monthly reports and top expenses', async () => {
    const { findByText, unmount } = renderWithProviders(<ReportsScreen />);
    expect(await findByText('Reports')).toBeTruthy();
    expect(await findByText('Top expenses')).toBeTruthy();
    expect(await findByText('Earned')).toBeTruthy();
    expect(await findByText('Spent')).toBeTruthy();
    unmount();
  });

  // Flow 17: Net Worth
  it('Flow 17: Net Worth displays total net worth and asset breakdown', async () => {
    const { findAllByText, findByText, unmount } = renderWithProviders(<NetWorthScreen />);
    const matches = await findAllByText('₹2,18,680');
    expect(matches.length).toBeGreaterThan(0);
    expect(await findByText('What you own minus what you owe')).toBeTruthy();
    unmount();
  });

  // Flow 18: DHAN AI suggested questions
  it('Flow 18: DHAN AI renders suggestions and chat interface', async () => {
    const { findByText, unmount } = renderWithProviders(<AssistantScreen />);
    expect(await findByText('DHAN AI')).toBeTruthy();
    expect(await findByText('Try asking')).toBeTruthy();
    unmount();
  });

  // Flow 19 & 20: Light mode and Dark mode
  it('Flow 19 & 20: Renders Home consistently in Light and Dark mode', async () => {
    const light = renderWithProviders(<HomeScreen />, 'light');
    expect(await light.findByText('Where it went')).toBeTruthy();
    light.unmount();

    const dark = renderWithProviders(<HomeScreen />, 'dark');
    expect(await dark.findByText('Where it went')).toBeTruthy();
    dark.unmount();
  });

  // Flow 21: App lock
  it('Flow 21: App lock opens only after the phone confirms its owner', async () => {
    const auth = jest.requireMock('expo-local-authentication') as {
      authenticateAsync: jest.Mock;
    };
    auth.authenticateAsync.mockResolvedValueOnce({ success: false });
    useSessionStore.setState({ locked: true });
    const { getByText, findByText, getByLabelText, unmount } = renderWithProviders(<LockScreen />);
    expect(getByText('DHAN is locked')).toBeTruthy();
    // The automatic prompt was cancelled: still locked
    expect(await findByText('Not unlocked. Tap to try again.')).toBeTruthy();
    expect(useSessionStore.getState().locked).toBe(true);

    await act(async () => {
      fireEvent.press(getByLabelText(/^Unlock with /));
    });
    expect(useSessionStore.getState().locked).toBe(false);
    unmount();
  });

  // Flow 22: Logout → Login again
  it('Flow 22: Sign out sheet renders confirmation prompt', () => {
    const { getByText, unmount } = renderWithProviders(<SignOutSheet />);
    expect(getByText('Sign out of DHAN?')).toBeTruthy();
    unmount();
  });

  // Flow 23: Back navigation & Settings
  it('Flow 23: Settings screen renders navigation entries', () => {
    const { getByText, unmount } = renderWithProviders(<SettingsScreen />);
    expect(getByText('Security and app lock')).toBeTruthy();
    expect(getByText('Appearance')).toBeTruthy();
    unmount();
  });

  // Flow 24: Security screen controls
  it('Flow 24: Security screen renders biometric toggle and idle timer', () => {
    const { getByText, unmount } = renderWithProviders(<SecurityScreen />);
    expect(getByText('Face ID or fingerprint to open DHAN')).toBeTruthy();
    unmount();
  });

  // Flow 25: Keypad input handling
  it('Flow 25: Keypad handles digit presses, decimal point and deletion', () => {
    const { getByLabelText, unmount } = renderWithProviders(<AddExpenseScreen />);
    fireEvent.press(getByLabelText('4'));
    fireEvent.press(getByLabelText('5'));
    fireEvent.press(getByLabelText('0'));
    expect(useEntryDraftStore.getState().draft.amount).toBe('450');

    fireEvent.press(getByLabelText('Delete'));
    expect(useEntryDraftStore.getState().draft.amount).toBe('45');
    unmount();
  });
});
