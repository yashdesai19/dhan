// The FastAPI client and mappers, with fetch and the secure store replaced by fakes.
const mockStore = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async (k: string) => mockStore.get(k) ?? null),
  setItemAsync: jest.fn(async (k: string, v: string) => void mockStore.set(k, v)),
  deleteItemAsync: jest.fn(async (k: string) => void mockStore.delete(k)),
}));

import { ApiError, api, setSessionExpiredHandler } from '@/data/api/client';
import {
  localParts,
  nextDueDate,
  toAccount,
  toCategory,
  toGroupExpense,
  toInstant,
  toSettlement,
  toTransaction,
  type WireAccount,
} from '@/data/api/mappers';
import { tokens } from '@/data/api/tokens';

type Reply = { status: number; body?: unknown };
const json = (status: number, body?: unknown): Reply => ({ status, body });

function respond(r: Reply): Response {
  const textBody = r.body === undefined ? '' : typeof r.body === 'string' ? r.body : JSON.stringify(r.body);
  return {
    ok: r.status >= 200 && r.status < 300,
    status: r.status,
    text: async () => textBody,
    json: async () => {
      if (r.body === undefined) throw new Error('no body');
      return r.body;
    },
  } as Response;
}

let calls: { url: string; init: RequestInit }[] = [];
function serve(handler: (url: string, init: RequestInit) => Reply | Promise<Reply>) {
  calls = [];
  globalThis.fetch = jest.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(url), init: init ?? {} });
    return respond(await handler(String(url), init ?? {}));
  }) as typeof fetch;
}
const authHeader = (i: number) => (calls[i]!.init.headers as Record<string, string>).Authorization;

beforeEach(async () => {
  await tokens.clear();
  await tokens.save('access-1', 'refresh-1');
  setSessionExpiredHandler(null);
});

describe('API client', () => {
  it('sends the access token', async () => {
    serve(() => json(200, { ok: true }));
    await api.get('/accounts');
    expect(authHeader(0)).toBe('Bearer access-1');
  });

  it('renews an expired access token once and retries the request', async () => {
    serve((url, init) => {
      if (url.endsWith('/auth/refresh'))
        return json(200, { access_token: 'access-2', refresh_token: 'refresh-2' });
      const auth = (init.headers as Record<string, string>).Authorization;
      return auth === 'Bearer access-2' ? json(200, ['ok']) : json(401, { detail: 'expired' });
    });
    await expect(api.get('/accounts')).resolves.toEqual(['ok']);
    expect(calls.map((c) => c.url.replace(/^.*?(\/[a-z])/, '$1'))).toEqual([
      '/accounts',
      '/auth/refresh',
      '/accounts',
    ]);
    expect(await tokens.refresh()).toBe('refresh-2'); // the rotated token replaces the used one
  });

  it('shares one refresh between requests that expire together', async () => {
    let refreshes = 0;
    serve(async (url, init) => {
      if (url.endsWith('/auth/refresh')) {
        refreshes += 1;
        await new Promise((r) => setTimeout(r, 10));
        return json(200, { access_token: 'access-2', refresh_token: 'refresh-2' });
      }
      const auth = (init.headers as Record<string, string>).Authorization;
      return auth === 'Bearer access-2' ? json(200, []) : json(401, {});
    });
    await Promise.all([api.get('/a'), api.get('/b'), api.get('/c')]);
    expect(refreshes).toBe(1);
  });

  it('ends the session when it cannot be renewed', async () => {
    const expired = jest.fn();
    setSessionExpiredHandler(expired);
    serve((url) => (url.endsWith('/auth/refresh') ? json(401, { detail: 'revoked' }) : json(401, {})));
    await expect(api.get('/accounts')).rejects.toMatchObject({ code: 'unauthorized' });
    expect(expired).toHaveBeenCalledTimes(1);
    expect(await tokens.access()).toBeNull();
    expect(await tokens.refresh()).toBeNull();
  });

  it('keeps the session when the server fails during renewal', async () => {
    const expired = jest.fn();
    setSessionExpiredHandler(expired);
    serve((url) => (url.endsWith('/auth/refresh') ? json(500, { detail: 'db down' }) : json(401, {})));
    await expect(api.get('/accounts')).rejects.toMatchObject({ code: 'failed' });
    expect(expired).not.toHaveBeenCalled();
    expect(await tokens.refresh()).toBe('refresh-1'); // still signed in once the server recovers
  });

  it('signs a disabled account out', async () => {
    const expired = jest.fn();
    setSessionExpiredHandler(expired);
    serve(() => json(403, { detail: 'Account is disabled or inactive.' }));
    await expect(api.get('/auth/me')).rejects.toBeInstanceOf(ApiError);
    expect(expired).toHaveBeenCalled();
  });

  it('reports no network as offline', async () => {
    globalThis.fetch = jest.fn(async () => {
      throw new TypeError('Network request failed');
    }) as typeof fetch;
    await expect(api.get('/accounts')).rejects.toMatchObject({ code: 'offline' });
  });

  it('turns API errors into sentences without leaking internals', async () => {
    serve(() => json(400, { detail: "An active account named 'Cash' already exists." }));
    await expect(api.post('/accounts', {})).rejects.toThrow("An active account named 'Cash' already exists.");

    serve(() => json(422, { detail: [{ loc: ['body', 'amount'], msg: 'Input should be greater than 0' }] }));
    await expect(api.post('/transactions', {})).rejects.toThrow('Input should be greater than 0 (amount)');

    serve(() => json(500, { detail: 'psycopg OperationalError at db:5432' }));
    const err = (await api.get('/accounts').catch((e: unknown) => e)) as ApiError;
    expect(err.message).toBe('Something went wrong on our side. Please try again.');
    expect(err.code).toBe('failed');

    serve(() => json(429, { detail: 'Too many attempts. Please wait and try again.' }));
    await expect(api.get('/accounts')).rejects.toMatchObject({ code: 'limited' });
  });

  it('logs in without sending an old token', async () => {
    serve(() => json(200, {}));
    await api.post('/auth/login', { email: 'a@b.com', password: 'x' }, { auth: false });
    expect(authHeader(0)).toBeUndefined();
  });
});

describe('API mappers', () => {
  it('reads stored instants in India time', () => {
    expect(localParts('2026-09-30T18:30:00Z')).toEqual({ date: '2026-10-01', time: '00:00' });
    expect(localParts('2026-09-30T18:29:00Z')).toEqual({ date: '2026-09-30', time: '23:59' });
    expect(toInstant('2026-09-30', '23:30')).toBe('2026-09-30T23:30:00+05:30');
  });

  it('puts card bill days on the next matching date', () => {
    expect(nextDueDate(12, '2026-10-04')).toBe('2026-10-12');
    expect(nextDueDate(2, '2026-10-04')).toBe('2026-11-02');
    expect(nextDueDate(31, '2026-11-05')).toBe('2026-11-30');
    expect(nextDueDate(5, '2026-12-20')).toBe('2027-01-05');
  });

  it('maps accounts and their types', () => {
    const wire: WireAccount = {
      id: 'a1',
      name: 'ICICI',
      type: 'credit_card',
      balance: '-5000.00',
      credit_limit: '100000.00',
      due_date: 12,
      archived: false,
      include_in_total: true,
      institution_name: 'Credit card',
      account_number_mask: '7710',
    };
    expect(toAccount(wire, '2026-10-04')).toEqual({
      id: 'a1',
      name: 'ICICI',
      type: 'credit',
      subtitle: 'Credit card',
      last4: '7710',
      balance: -5000,
      creditLimit: 100000,
      dueDate: '2026-10-12',
      includeInTotal: true,
      archived: false,
    });
  });

  it('shows the signed-in user as "me" in splits', () => {
    const e = toGroupExpense(
      {
        id: 'e1',
        group_id: 'g1',
        title: 'Villa',
        amount: '1200.00',
        paid_by_id: 'uuid-me',
        split_type: 'exact',
        shares: { 'uuid-me': '600.00', 'uuid-aman': '600.00' },
        date: '2026-09-27T06:30:00Z',
      },
      'uuid-me',
    );
    expect(e.paidBy).toBe('me');
    expect(e.shares).toEqual({ me: 600, 'uuid-aman': 600 });
    const s = toSettlement(
      {
        id: 's1',
        payer_id: 'uuid-aman',
        payee_id: 'uuid-me',
        amount: '200',
        method: 'cash',
        created_at: '2026-10-01T05:00:00Z',
      },
      'uuid-me',
    );
    expect([s.fromId, s.toId, s.amount]).toEqual(['uuid-aman', 'me', 200]);
  });

  it('keeps the app’s category styling for its standard categories', () => {
    const food = toCategory({
      id: 'c1',
      user_id: 'u',
      name: 'Fun and subscriptions',
      category_type: 'expense',
      icon: 'not-an-icon',
      is_default: false,
      is_active: true,
    });
    expect([food.short, food.icon, food.kind]).toEqual(['Fun', 'film', 'expense']);
    const tx = toTransaction(
      {
        id: 't1',
        account_id: 'a1',
        destination_account_id: null,
        category_id: 'c1',
        amount: '450.00',
        type: 'expense',
        description: '',
        transaction_date: '2026-09-30T07:50:00Z',
        notes: '',
        status: 'completed',
      },
      new Map([['c1', food]]),
    );
    expect([tx.title, tx.date, tx.time, tx.amount]).toEqual(['Fun', '2026-09-30', '13:20', 450]);
  });
});
