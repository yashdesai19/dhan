export const qk = {
  user: ['user'],
  accounts: ['accounts'],
  categories: ['categories'],
  transactions: ['transactions'],
  budgets: ['budgets'],
  people: ['people'],
  groups: ['groups'],
  groupExpenses: ['groupExpenses'],
  settlements: ['settlements'],
  goals: ['goals'],
  recurring: ['recurring'],
  assets: ['assets'],
  liabilities: ['liabilities'],
  history: ['history'],
  notifications: ['notifications'],
  aiResponses: ['aiResponses'],
  insights: ['insights'],
  devices: ['devices'],
  recentSearches: ['recentSearches'],
  chipOrder: ['chipOrder'],
} as const;

export type QueryKeyName = keyof typeof qk;
