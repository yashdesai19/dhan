// OFFLINE TYPE STUBS — see offline/shims/react.d.ts.
/* eslint-disable */
declare module 'react-native-svg' {
  import type { ReactElement, ReactNode } from 'react';
  import type { AccessibilityProps, StyleProp, ViewStyle } from 'react-native';
  interface Common {
    fill?: string;
    fillOpacity?: number;
    stroke?: string;
    strokeWidth?: number;
    strokeLinecap?: 'butt' | 'round' | 'square';
    strokeLinejoin?: 'miter' | 'round' | 'bevel';
    strokeDasharray?: string | number[];
    strokeDashoffset?: number;
    opacity?: number;
    transform?: string;
    rotation?: number;
    origin?: string;
    children?: ReactNode;
  }
  export interface SvgProps extends Common, AccessibilityProps {
    width?: number | string;
    height?: number | string;
    viewBox?: string;
    preserveAspectRatio?: string;
    style?: StyleProp<ViewStyle>;
    testID?: string;
  }
  const Svg: (p: SvgProps) => ReactElement;
  export default Svg;
  export const Path: (p: Common & { d: string }) => ReactElement;
  export const Circle: (p: Common & { cx: number; cy: number; r: number }) => ReactElement;
  export const Rect: (p: Common & { x?: number; y?: number; width: number; height: number; rx?: number; ry?: number }) => ReactElement;
  export const Line: (p: Common & { x1: number; y1: number; x2: number; y2: number }) => ReactElement;
  export const Polyline: (p: Common & { points: string }) => ReactElement;
  export const Polygon: (p: Common & { points: string }) => ReactElement;
  export const G: (p: Common) => ReactElement;
  export const Defs: (p: { children?: ReactNode }) => ReactElement;
  export const LinearGradient: (p: { id: string; x1?: string; y1?: string; x2?: string; y2?: string; children?: ReactNode }) => ReactElement;
  export const Stop: (p: { offset: string; stopColor: string; stopOpacity?: number }) => ReactElement;
}

declare module 'react-native-reanimated' {
  import type { ReactElement } from 'react';
  import type { StyleProp, TextProps, TextStyle, ViewProps, ViewStyle } from 'react-native';
  export interface SharedValue<T> {
    value: T;
  }
  export interface EntryExitBuilder {
    duration(ms: number): EntryExitBuilder;
    delay(ms: number): EntryExitBuilder;
    springify(): EntryExitBuilder;
    reduceMotion(m: unknown): EntryExitBuilder;
  }
  type AnimatedStyle = Record<string, unknown>;
  interface AnimatedExtra {
    entering?: EntryExitBuilder;
    exiting?: EntryExitBuilder;
    layout?: EntryExitBuilder;
  }
  export interface AnimatedViewProps extends Omit<ViewProps, 'style'>, AnimatedExtra {
    style?: StyleProp<ViewStyle> | AnimatedStyle | ReadonlyArray<StyleProp<ViewStyle> | AnimatedStyle>;
  }
  export interface AnimatedTextProps extends Omit<TextProps, 'style'>, AnimatedExtra {
    style?: StyleProp<TextStyle> | AnimatedStyle | ReadonlyArray<StyleProp<TextStyle> | AnimatedStyle>;
  }
  const Animated: {
    View: (p: AnimatedViewProps) => ReactElement;
    Text: (p: AnimatedTextProps) => ReactElement;
    createAnimatedComponent<P>(c: (p: P) => ReactElement): (p: P & { animatedProps?: Partial<P> }) => ReactElement;
  };
  export default Animated;
  export function useSharedValue<T>(v: T): SharedValue<T>;
  export function useAnimatedStyle(fn: () => AnimatedStyle, deps?: readonly unknown[]): AnimatedStyle;
  export function useAnimatedProps<P>(fn: () => Partial<P>, deps?: readonly unknown[]): Partial<P>;
  export function useDerivedValue<T>(fn: () => T, deps?: readonly unknown[]): SharedValue<T>;
  export function useAnimatedReaction<T>(prepare: () => T, react: (cur: T, prev: T | null) => void, deps?: readonly unknown[]): void;
  export interface TimingConfig {
    duration?: number;
    easing?: (t: number) => number;
  }
  export function withTiming<T extends number | string>(to: T, cfg?: TimingConfig, cb?: (finished?: boolean) => void): T;
  export function withSpring<T extends number>(to: T, cfg?: { damping?: number; stiffness?: number; mass?: number }): T;
  export function withRepeat<T>(a: T, reps?: number, reverse?: boolean): T;
  export function withSequence<T>(...a: T[]): T;
  export function withDelay<T>(ms: number, a: T): T;
  export function cancelAnimation(v: SharedValue<unknown>): void;
  export function runOnJS<A extends unknown[], R>(fn: (...a: A) => R): (...a: A) => void;
  export function interpolate(v: number, input: readonly number[], output: readonly number[], extrapolate?: unknown): number;
  export const Extrapolation: { CLAMP: unknown };
  export const Easing: {
    linear: (t: number) => number;
    quad: (t: number) => number;
    cubic: (t: number) => number;
    ease: (t: number) => number;
    out(e: (t: number) => number): (t: number) => number;
    in(e: (t: number) => number): (t: number) => number;
    inOut(e: (t: number) => number): (t: number) => number;
    bezier(a: number, b: number, c: number, d: number): (t: number) => number;
  };
  export function useReducedMotion(): boolean;
  export const FadeIn: EntryExitBuilder;
  export const FadeOut: EntryExitBuilder;
  export const FadeInDown: EntryExitBuilder;
  export const FadeOutDown: EntryExitBuilder;
  export const LinearTransition: EntryExitBuilder;
  export const ReduceMotion: { System: unknown; Always: unknown; Never: unknown };
}

declare module 'react-native-gesture-handler' {
  import type { ReactElement } from 'react';
  import type { ViewProps } from 'react-native';
  export const GestureHandlerRootView: (p: ViewProps) => ReactElement;
}

declare module 'react-native-safe-area-context' {
  import type { ReactElement, ReactNode } from 'react';
  import type { ViewProps } from 'react-native';
  export interface EdgeInsets {
    top: number;
    bottom: number;
    left: number;
    right: number;
  }
  export const SafeAreaProvider: (p: { children?: ReactNode }) => ReactElement;
  export const SafeAreaView: (p: ViewProps & { edges?: ReadonlyArray<'top' | 'bottom' | 'left' | 'right'> }) => ReactElement;
  export function useSafeAreaInsets(): EdgeInsets;
}

declare module '@gorhom/bottom-sheet' {
  import type { ReactElement, ReactNode, Ref } from 'react';
  import type { ScrollViewProps, StyleProp, TextInputProps, ViewProps, ViewStyle } from 'react-native';
  export interface BottomSheetMethods {
    close(): void;
    expand(): void;
    snapToIndex(i: number): void;
    forceClose(): void;
  }
  export interface BottomSheetBackdropProps {
    animatedIndex: unknown;
    animatedPosition: unknown;
    style?: StyleProp<ViewStyle>;
  }
  export interface BottomSheetProps {
    ref?: Ref<BottomSheetMethods>;
    index?: number;
    snapPoints?: ReadonlyArray<string | number>;
    enableDynamicSizing?: boolean;
    enablePanDownToClose?: boolean;
    enableOverDrag?: boolean;
    animateOnMount?: boolean;
    onClose?: () => void;
    onChange?: (index: number) => void;
    backdropComponent?: (p: BottomSheetBackdropProps) => ReactNode;
    backgroundStyle?: StyleProp<ViewStyle>;
    handleIndicatorStyle?: StyleProp<ViewStyle>;
    handleStyle?: StyleProp<ViewStyle>;
    keyboardBehavior?: 'extend' | 'fillParent' | 'interactive';
    keyboardBlurBehavior?: 'none' | 'restore';
    android_keyboardInputMode?: 'adjustPan' | 'adjustResize';
    accessible?: boolean;
    accessibilityLabel?: string;
    children?: ReactNode;
  }
  type BottomSheet = BottomSheetMethods;
  const BottomSheet: (p: BottomSheetProps) => ReactElement;
  export default BottomSheet;
  export const BottomSheetView: (p: ViewProps) => ReactElement;
  export const BottomSheetScrollView: (p: ScrollViewProps) => ReactElement;
  export const BottomSheetTextInput: (p: TextInputProps) => ReactElement;
  export const BottomSheetBackdrop: (
    p: BottomSheetBackdropProps & { appearsOnIndex?: number; disappearsOnIndex?: number; pressBehavior?: 'none' | 'close' | 'collapse'; opacity?: number; accessibilityLabel?: string },
  ) => ReactElement;
  export const BottomSheetModalProvider: (p: { children?: ReactNode }) => ReactElement;
}

declare module 'expo-router' {
  import type { ReactElement, ReactNode } from 'react';
  import type { StyleProp, ViewStyle } from 'react-native';
  export type Href = string | { pathname: string; params?: Record<string, string | number | undefined> };
  export interface Router {
    push(href: Href): void;
    replace(href: Href): void;
    navigate(href: Href): void;
    back(): void;
    dismiss(count?: number): void;
    dismissAll(): void;
    dismissTo(href: Href): void;
    canGoBack(): boolean;
    canDismiss(): boolean;
    setParams(p: Record<string, string>): void;
  }
  export const router: Router;
  export function useRouter(): Router;
  export function useLocalSearchParams<T extends Record<string, string | string[] | undefined> = Record<string, string>>(): Partial<T>;
  export function usePathname(): string;
  export function useSegments(): string[];
  export function useFocusEffect(cb: () => void | (() => void)): void;
  export function Redirect(p: { href: Href }): ReactElement;
  export function Slot(): ReactElement;
  export interface StackOptions {
    headerShown?: boolean;
    presentation?: 'card' | 'modal' | 'transparentModal' | 'containedTransparentModal' | 'fullScreenModal' | 'formSheet';
    animation?: 'default' | 'fade' | 'none' | 'slide_from_bottom' | 'slide_from_right' | 'fade_from_bottom' | 'ios_from_right';
    contentStyle?: StyleProp<ViewStyle>;
    gestureEnabled?: boolean;
    animationDuration?: number;
    freezeOnBlur?: boolean;
  }
  export const Stack: ((p: { screenOptions?: StackOptions; children?: ReactNode }) => ReactElement) & {
    Screen: (p: { name: string; options?: StackOptions }) => ReactElement;
  };
  export interface TabBarProps {
    state: { index: number; routes: { key: string; name: string }[] };
    navigation: { navigate(name: string): void; emit(e: { type: string; target: string; canPreventDefault?: boolean }): { defaultPrevented: boolean } };
    insets: { bottom: number };
  }
  export const Tabs: ((p: { tabBar?: (p: TabBarProps) => ReactNode; screenOptions?: { headerShown?: boolean; lazy?: boolean; animation?: 'none' | 'fade' | 'shift' }; children?: ReactNode }) => ReactElement) & {
    Screen: (p: { name: string; options?: { title?: string } }) => ReactElement;
  };
}

declare module '@react-navigation/bottom-tabs' {
  import type { TabBarProps } from 'expo-router';
  export type BottomTabBarProps = TabBarProps;
}

declare module 'expo-font' {
  export function useFonts(map: Record<string, unknown>): [boolean, Error | null];
}
declare module 'expo-splash-screen' {
  export function preventAutoHideAsync(): Promise<boolean>;
  export function hideAsync(): Promise<void>;
  export function setOptions(o: { duration?: number; fade?: boolean }): void;
}
declare module 'expo-status-bar' {
  import type { ReactElement } from 'react';
  export const StatusBar: (p: { style?: 'light' | 'dark' | 'auto' }) => ReactElement;
}
declare module 'expo-system-ui' {
  export function setBackgroundColorAsync(color: string): Promise<void>;
}
declare module 'expo-haptics' {
  export enum ImpactFeedbackStyle {
    Light = 'light',
    Medium = 'medium',
  }
  export enum NotificationFeedbackType {
    Success = 'success',
    Warning = 'warning',
    Error = 'error',
  }
  export function impactAsync(s?: ImpactFeedbackStyle): Promise<void>;
  export function notificationAsync(t?: NotificationFeedbackType): Promise<void>;
  export function selectionAsync(): Promise<void>;
}

declare module 'zustand' {
  export type SetState<T> = (partial: Partial<T> | ((s: T) => Partial<T>)) => void;
  export type StateCreator<T> = (set: SetState<T>, get: () => T) => T;
  export interface UseBoundStore<T> {
    (): T;
    <U>(selector: (s: T) => U): U;
    getState(): T;
    setState: SetState<T>;
    subscribe(l: (s: T, prev: T) => void): () => void;
  }
  export function create<T>(): (init: StateCreator<T>) => UseBoundStore<T>;
  export function create<T>(init: StateCreator<T>): UseBoundStore<T>;
}
declare module 'zustand/middleware' {
  import type { StateCreator } from 'zustand';
  export interface StateStorage {
    getItem(name: string): string | null | Promise<string | null>;
    setItem(name: string, value: string): unknown;
    removeItem(name: string): unknown;
  }
  export function createJSONStorage(get: () => StateStorage): unknown;
  export function persist<T>(
    init: StateCreator<T>,
    opts: {
      name: string;
      storage?: unknown;
      partialize?: (s: T) => Partial<T>;
      onRehydrateStorage?: (s: T) => ((state: T | undefined, err?: unknown) => void) | void;
    },
  ): StateCreator<T>;
}

declare module '@react-native-async-storage/async-storage' {
  const AsyncStorage: {
    getItem(k: string): Promise<string | null>;
    setItem(k: string, v: string): Promise<void>;
    removeItem(k: string): Promise<void>;
  };
  export default AsyncStorage;
}

declare module '@tanstack/react-query' {
  import type { ReactElement, ReactNode } from 'react';
  export type QueryKey = readonly unknown[];
  export class QueryClient {
    constructor(opts?: { defaultOptions?: { queries?: { staleTime?: number; retry?: number | boolean }; mutations?: { retry?: number } } });
    invalidateQueries(f: { queryKey: QueryKey }): Promise<void>;
    refetchQueries(f?: { queryKey?: QueryKey }): Promise<void>;
    clear(): void;
  }
  export const QueryClientProvider: (p: { client: QueryClient; children?: ReactNode }) => ReactElement;
  export function useQueryClient(): QueryClient;
  export interface UseQueryResult<T> {
    data: T | undefined;
    error: Error | null;
    isLoading: boolean;
    isPending: boolean;
    isError: boolean;
    isSuccess: boolean;
    isFetching: boolean;
    isRefetching: boolean;
    refetch(): Promise<unknown>;
    status: 'pending' | 'error' | 'success';
  }
  export function useQuery<T>(o: { queryKey: QueryKey; queryFn: () => Promise<T>; enabled?: boolean; staleTime?: number; retry?: number | boolean }): UseQueryResult<T>;
  export interface UseMutationResult<D, V> {
    mutate(v: V, o?: { onSuccess?: (d: D) => void; onError?: (e: Error) => void; onSettled?: () => void }): void;
    mutateAsync(v: V): Promise<D>;
    isPending: boolean;
    isError: boolean;
    error: Error | null;
    reset(): void;
    data: D | undefined;
  }
  export function useMutation<D, V = void>(o: { mutationFn: (v: V) => Promise<D>; onSuccess?: (d: D, v: V) => unknown; onError?: (e: Error) => void }): UseMutationResult<D, V>;
}

declare const require: (path: string) => number;
declare const process: { env: Record<string, string | undefined> };
declare function setTimeout(fn: () => void, ms?: number): number;
declare function clearTimeout(id: number | undefined): void;
declare function setInterval(fn: () => void, ms?: number): number;
declare function clearInterval(id: number | undefined): void;
declare const __DEV__: boolean;
