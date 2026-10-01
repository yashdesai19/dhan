// OFFLINE TYPE STUBS — used only by offline/tsconfig.app.json because the npm registry was not
// reachable in the build environment. They model the subset of each library the app uses so
// strict TypeScript can catch mistakes in DHAN's own code. `npm run typecheck` uses the real types.
/* eslint-disable */
declare module 'react' {
  export type Key = string | number;
  export interface ReactElement<P = any> {
    type: any;
    props: P;
    key: Key | null;
  }
  export type ReactNode = ReactElement | string | number | bigint | boolean | null | undefined | Iterable<ReactNode>;
  export type PropsWithChildren<P = unknown> = P & { children?: ReactNode };
  export type FC<P = {}> = (props: P) => ReactNode;
  export type ComponentType<P = {}> = (props: P) => ReactNode;
  export type ComponentProps<T> = T extends (props: infer P) => any ? P : never;
  export interface RefObject<T> {
    current: T | null;
  }
  export interface MutableRefObject<T> {
    current: T;
  }
  export type RefCallback<T> = (instance: T | null) => void;
  export type Ref<T> = RefCallback<T> | RefObject<T> | null;
  export type Dispatch<A> = (value: A) => void;
  export type SetStateAction<S> = S | ((prev: S) => S);
  export type DependencyList = readonly unknown[];
  export type EffectCallback = () => void | (() => void);
  export interface Context<T> {
    Provider: (props: { value: T; children?: ReactNode }) => ReactElement;
  }
  export function createContext<T>(defaultValue: T): Context<T>;
  export function useContext<T>(ctx: Context<T>): T;
  export function useState<S>(initial: S | (() => S)): [S, Dispatch<SetStateAction<S>>];
  export function useState<S = undefined>(): [S | undefined, Dispatch<SetStateAction<S | undefined>>];
  export function useEffect(effect: EffectCallback, deps?: DependencyList): void;
  export function useLayoutEffect(effect: EffectCallback, deps?: DependencyList): void;
  export function useMemo<T>(factory: () => T, deps: DependencyList): T;
  export function useCallback<T extends (...args: any[]) => any>(cb: T, deps: DependencyList): T;
  export function useRef<T>(initial: T): MutableRefObject<T>;
  export function useRef<T>(initial: T | null): RefObject<T>;
  export function useRef<T = undefined>(): MutableRefObject<T | undefined>;
  export function useId(): string;
  export function memo<P>(c: (props: P) => ReactNode, eq?: (a: P, b: P) => boolean): (props: P) => ReactNode;
  export function forwardRef<T, P = {}>(render: (props: P, ref: Ref<T>) => ReactNode): (props: P & { ref?: Ref<T> }) => ReactNode;
  export function useImperativeHandle<T>(ref: Ref<T> | undefined, init: () => T, deps?: DependencyList): void;
  export const Fragment: (props: { children?: ReactNode }) => ReactElement;
  export function isValidElement(v: unknown): v is ReactElement;
  export function cloneElement<P>(el: ReactElement<P>, props?: Partial<P>): ReactElement<P>;
  export const Children: { toArray(children: ReactNode): ReactNode[]; count(children: ReactNode): number };
  const React: { Fragment: typeof Fragment };
  export default React;
}

declare module 'react/jsx-runtime' {
  import type { Key, ReactElement, ReactNode } from 'react';
  export function jsx(type: any, props: any, key?: Key): ReactElement;
  export function jsxs(type: any, props: any, key?: Key): ReactElement;
  export const Fragment: any;
  export namespace JSX {
    type ElementType = string | ((props: any) => ReactNode);
    interface Element extends ReactElement {}
    interface ElementAttributesProperty {}
    interface ElementChildrenAttribute {
      children: {};
    }
    interface IntrinsicAttributes {
      key?: Key | null;
    }
    interface IntrinsicElements {}
  }
}
