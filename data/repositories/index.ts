// Repository entry point. Screens never import this directly; they use the hooks in data/queries.
// With EXPO_PUBLIC_DHAN_API_URL set the app talks to FastAPI, otherwise it runs on the in-memory
// mock data (tests and offline demos). Both implementations share these exports.
import * as apiRepos from '@/data/api/repositories';
import { isApiMode } from '@/data/api/config';
import * as mockRepos from './mock';

type Repos = typeof mockRepos;
const impl: Pick<
  Repos,
  | 'readRepo'
  | 'transactionsRepo'
  | 'accountsRepo'
  | 'budgetRepo'
  | 'splitsRepo'
  | 'goalsRepo'
  | 'recurringRepo'
  | 'netWorthRepo'
  | 'profileRepo'
  | 'notificationsRepo'
  | 'aiRepo'
  | 'authRepo'
> = isApiMode ? apiRepos : mockRepos;

export const {
  readRepo,
  transactionsRepo,
  accountsRepo,
  budgetRepo,
  splitsRepo,
  goalsRepo,
  recurringRepo,
  netWorthRepo,
  profileRepo,
  notificationsRepo,
  aiRepo,
  authRepo,
} = impl;

export { isApiMode };
export { MockError, MOCK_PASSWORD, resetMockData } from './mock';
export type { AccountInput, NewEntry, NewGroupExpense, NewHolding, NewRecurring } from './mock';
export { isLoanType } from './mock';
