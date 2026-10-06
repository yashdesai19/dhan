// Offline-only: the subset of Jest globals the logic tests use.
declare function describe(name: string, fn: () => void): void;
declare function it(name: string, fn: () => void | Promise<void>): void;
declare function test(name: string, fn: () => void | Promise<void>): void;
declare function beforeEach(fn: () => void | Promise<void>): void;
interface OfflineMatchers {
  toBe(v: unknown): void;
  toEqual(v: unknown): void;
  toBeCloseTo(v: number, digits?: number): void;
  toBeGreaterThan(v: number): void;
  toBeLessThan(v: number): void;
  toContain(v: unknown): void;
  toHaveLength(n: number): void;
  toBeUndefined(): void;
  toBeDefined(): void;
  toBeNull(): void;
  toBeTruthy(): void;
  toBeFalsy(): void;
}
declare function expect(actual: unknown): OfflineMatchers;
declare const process: { env: Record<string, string | undefined> };
