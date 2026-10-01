import { mockConfig } from '@/mock/config';

export class MockError extends Error {
  constructor(
    message: string,
    readonly code: 'offline' | 'failed' | 'invalid' | 'not_found' = 'failed',
  ) {
    super(message);
    this.name = 'MockError';
  }
}

/** Simulated network latency (spec §13, step 2). Never touches the network. */
export async function simulate<T>(work: () => T, opts: { readsReports?: boolean } = {}): Promise<T> {
  const [min, max] = mockConfig.latency;
  const ms = min + Math.random() * Math.max(0, max - min);
  if (ms > 0) await new Promise<void>((resolve) => setTimeout(() => resolve(), ms));
  if (mockConfig.failNext) {
    mockConfig.failNext = false;
    throw new MockError('Something went wrong. Please try again.');
  }
  if (opts.readsReports && mockConfig.offline) {
    throw new MockError('You’re offline.', 'offline');
  }
  return work();
}
