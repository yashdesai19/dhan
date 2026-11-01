/**
 * End-to-end check of the app's API layer against a running backend. Skipped unless
 * LIVE_API_URL is set:  LIVE_API_URL=https://dhan-api-jqfp.onrender.com npx jest live-api
 */
const LIVE = process.env.LIVE_API_URL;
const run = LIVE ? describe : describe.skip;

jest.mock('expo-secure-store', () => {
  const store = new Map<string, string>();
  return {
    getItemAsync: async (k: string) => store.get(k) ?? null,
    setItemAsync: async (k: string, v: string) => void store.set(k, v),
    deleteItemAsync: async (k: string) => void store.delete(k),
  };
});

run('live API: a new user from sign-up to transactions', () => {
  jest.setTimeout(180_000);
  let repos: typeof import('@/data/api/repositories');

  beforeAll(() => {
    // Name the failing request: the app's errors only carry a user-facing message
    // The React Native test setup replaces fetch with a stub; this suite needs the real network
    const realFetch = jest.requireActual('node-fetch') as unknown as typeof fetch;
    globalThis.fetch = (async (url: string, init?: RequestInit) => {
      const t0 = Date.now();
      const res = await realFetch(url, init);
      if (process.env.LIVE_API_TIMING) process.stderr.write(`TIME ${Date.now() - t0}ms ${init?.method ?? 'GET'} ${url.replace(LIVE!, '')}
`);
      if (!res.ok) {
        const body = await res.clone().text();
        process.stderr.write(`${init?.method ?? 'GET'} ${url} -> ${res.status} ${body.slice(0, 300)} | sent ${init?.body ?? ''}
`);
      }
      return res;
    }) as typeof fetch;
    process.env.EXPO_PUBLIC_DHAN_API_URL = LIVE;
    jest.resetModules();
    repos = require('@/data/api/repositories');
  });

  it('signs up and can read every screen', async () => {
    await repos.authRepo.signUp('Audit Test', `audit${Date.now()}@example.com`, 'AuditPass123!');
    const r = repos.readRepo;
    for (const [name, read] of Object.entries(r)) {
      try {
        await (read as () => Promise<unknown>)();
      } catch (e) {
        throw new Error(`readRepo.${name} failed: ${String(e)}`);
      }
    }
    expect((await r.categories()).length).toBeGreaterThan(0);
  });

  it('adds an expense and an income right after sign-up', async () => {
    const categories = await repos.readRepo.categories();
    const expenseCat = categories.find((c) => c.kind === 'expense')!;
    const incomeCat = categories.find((c) => c.kind === 'income')!;
    const accounts = await repos.readRepo.accounts();
    const accountId = accounts[0]?.id ?? '';

    const expense = await repos.transactionsRepo.addExpense({ amount: 120, categoryId: expenseCat.id, accountId });
    const income = await repos.transactionsRepo.addIncome({ amount: 500, categoryId: incomeCat.id, accountId });
    expect(expense.type).toBe('expense');
    expect(income.type).toBe('income');

    const ids = (await repos.readRepo.transactions()).map((t) => t.id);
    expect(ids).toEqual(expect.arrayContaining([expense.id, income.id]));
  });

  it('creates a second account and transfers between them', async () => {
    const bank = await repos.accountsRepo.upsert({
      name: 'Bank',
      type: 'bank',
      balance: 0,
    } as Parameters<typeof repos.accountsRepo.upsert>[0]);
    const [from] = (await repos.readRepo.accounts()).filter((a) => a.id !== bank.id);
    const t = await repos.transactionsRepo.addTransfer({ amount: 50, fromId: from!.id, toId: bank.id });
    expect(t.type).toBe('transfer');
  });
});
