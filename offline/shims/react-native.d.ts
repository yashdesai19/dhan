// OFFLINE TYPE STUBS — see offline/shims/react.d.ts.
/* eslint-disable */
declare module 'react-native' {
  import type { ReactElement, ReactNode, Ref } from 'react';

  export type DimensionValue = number | `${number}%` | 'auto';
  type Falsy = undefined | null | false | '';
  export type StyleProp<T> = T | Falsy | readonly StyleProp<T>[];
  export type ColorValue = string;

  export interface ViewStyle {
    flex?: number;
    flexDirection?: 'row' | 'column' | 'row-reverse' | 'column-reverse';
    flexWrap?: 'wrap' | 'nowrap';
    flexGrow?: number;
    flexShrink?: number;
    flexBasis?: DimensionValue;
    alignItems?: 'flex-start' | 'flex-end' | 'center' | 'stretch' | 'baseline';
    alignSelf?: 'auto' | 'flex-start' | 'flex-end' | 'center' | 'stretch' | 'baseline';
    alignContent?: 'flex-start' | 'flex-end' | 'center' | 'stretch' | 'space-between' | 'space-around';
    justifyContent?: 'flex-start' | 'flex-end' | 'center' | 'space-between' | 'space-around' | 'space-evenly';
    gap?: number;
    rowGap?: number;
    columnGap?: number;
    position?: 'absolute' | 'relative';
    top?: DimensionValue;
    bottom?: DimensionValue;
    left?: DimensionValue;
    right?: DimensionValue;
    zIndex?: number;
    width?: DimensionValue;
    height?: DimensionValue;
    minWidth?: DimensionValue;
    maxWidth?: DimensionValue;
    minHeight?: DimensionValue;
    maxHeight?: DimensionValue;
    aspectRatio?: number;
    margin?: DimensionValue;
    marginTop?: DimensionValue;
    marginBottom?: DimensionValue;
    marginLeft?: DimensionValue;
    marginRight?: DimensionValue;
    marginHorizontal?: DimensionValue;
    marginVertical?: DimensionValue;
    padding?: DimensionValue;
    paddingTop?: DimensionValue;
    paddingBottom?: DimensionValue;
    paddingLeft?: DimensionValue;
    paddingRight?: DimensionValue;
    paddingHorizontal?: DimensionValue;
    paddingVertical?: DimensionValue;
    backgroundColor?: ColorValue;
    opacity?: number;
    overflow?: 'visible' | 'hidden' | 'scroll';
    borderRadius?: number;
    borderTopLeftRadius?: number;
    borderTopRightRadius?: number;
    borderBottomLeftRadius?: number;
    borderBottomRightRadius?: number;
    borderWidth?: number;
    borderTopWidth?: number;
    borderBottomWidth?: number;
    borderLeftWidth?: number;
    borderRightWidth?: number;
    borderColor?: ColorValue;
    borderTopColor?: ColorValue;
    borderBottomColor?: ColorValue;
    borderLeftColor?: ColorValue;
    borderRightColor?: ColorValue;
    borderStyle?: 'solid' | 'dotted' | 'dashed';
    shadowColor?: ColorValue;
    shadowOffset?: { width: number; height: number };
    shadowOpacity?: number;
    shadowRadius?: number;
    elevation?: number;
    transform?: ReadonlyArray<
      | { translateX: number }
      | { translateY: number }
      | { scale: number }
      | { scaleX: number }
      | { scaleY: number }
      | { rotate: string }
    >;
    display?: 'flex' | 'none';
    direction?: 'ltr' | 'rtl';
    pointerEvents?: 'auto' | 'none' | 'box-none' | 'box-only';
  }

  export interface TextStyle extends ViewStyle {
    color?: ColorValue;
    fontFamily?: string;
    fontSize?: number;
    fontWeight?: '400' | '500' | '600' | '700' | 'normal' | 'bold';
    fontStyle?: 'normal' | 'italic';
    lineHeight?: number;
    letterSpacing?: number;
    textAlign?: 'auto' | 'left' | 'right' | 'center' | 'justify';
    textAlignVertical?: 'auto' | 'top' | 'bottom' | 'center';
    textTransform?: 'none' | 'uppercase' | 'lowercase' | 'capitalize';
    textDecorationLine?: 'none' | 'underline' | 'line-through';
    fontVariant?: ReadonlyArray<'tabular-nums' | 'lining-nums' | 'small-caps'>;
    includeFontPadding?: boolean;
  }

  export interface ImageStyle extends ViewStyle {}

  export type AccessibilityRole =
    | 'none'
    | 'button'
    | 'link'
    | 'header'
    | 'text'
    | 'image'
    | 'switch'
    | 'checkbox'
    | 'tab'
    | 'tablist'
    | 'radio'
    | 'radiogroup'
    | 'progressbar'
    | 'alert'
    | 'summary'
    | 'search'
    | 'adjustable'
    | 'keyboardkey'
    | 'menu'
    | 'menuitem'
    | 'list';

  export interface AccessibilityState {
    selected?: boolean;
    disabled?: boolean;
    checked?: boolean | 'mixed';
    busy?: boolean;
    expanded?: boolean;
  }

  export interface Insets {
    top?: number;
    bottom?: number;
    left?: number;
    right?: number;
  }

  export interface LayoutChangeEvent {
    nativeEvent: { layout: { x: number; y: number; width: number; height: number } };
  }

  export interface AccessibilityProps {
    accessible?: boolean;
    accessibilityLabel?: string;
    accessibilityHint?: string;
    accessibilityRole?: AccessibilityRole;
    accessibilityState?: AccessibilityState;
    accessibilityValue?: { min?: number; max?: number; now?: number; text?: string };
    accessibilityLiveRegion?: 'none' | 'polite' | 'assertive';
    accessibilityElementsHidden?: boolean;
    accessibilityViewIsModal?: boolean;
    importantForAccessibility?: 'auto' | 'yes' | 'no' | 'no-hide-descendants';
    accessibilityActions?: ReadonlyArray<{ name: string; label?: string }>;
    onAccessibilityAction?: (e: { nativeEvent: { actionName: string } }) => void;
    role?: string;
  }

  export interface ViewProps extends AccessibilityProps {
    style?: StyleProp<ViewStyle>;
    children?: ReactNode;
    testID?: string;
    pointerEvents?: 'auto' | 'none' | 'box-none' | 'box-only';
    onLayout?: (e: LayoutChangeEvent) => void;
    hitSlop?: Insets | number;
    collapsable?: boolean;
    nativeID?: string;
  }

  export interface PressableStateCallbackType {
    pressed: boolean;
  }

  export interface PressableProps extends Omit<ViewProps, 'style' | 'children'> {
    style?: StyleProp<ViewStyle> | ((state: PressableStateCallbackType) => StyleProp<ViewStyle>);
    children?: ReactNode | ((state: PressableStateCallbackType) => ReactNode);
    onPress?: () => void;
    onPressIn?: () => void;
    onPressOut?: () => void;
    onLongPress?: () => void;
    disabled?: boolean;
    android_ripple?: { color?: ColorValue; borderless?: boolean; radius?: number; foreground?: boolean };
    unstable_pressDelay?: number;
  }

  export interface TextProps extends AccessibilityProps {
    style?: StyleProp<TextStyle>;
    children?: ReactNode;
    numberOfLines?: number;
    ellipsizeMode?: 'head' | 'middle' | 'tail' | 'clip';
    allowFontScaling?: boolean;
    maxFontSizeMultiplier?: number;
    adjustsFontSizeToFit?: boolean;
    minimumFontScale?: number;
    selectable?: boolean;
    onPress?: () => void;
    testID?: string;
    nativeID?: string;
  }

  export type KeyboardTypeOptions = 'default' | 'email-address' | 'numeric' | 'phone-pad' | 'decimal-pad' | 'number-pad';

  export interface TextInputProps extends AccessibilityProps {
    style?: StyleProp<TextStyle>;
    value?: string;
    defaultValue?: string;
    onChangeText?: (text: string) => void;
    placeholder?: string;
    placeholderTextColor?: ColorValue;
    secureTextEntry?: boolean;
    keyboardType?: KeyboardTypeOptions;
    inputMode?: 'text' | 'decimal' | 'numeric' | 'email' | 'tel' | 'search';
    autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
    autoComplete?: 'email' | 'password' | 'new-password' | 'name' | 'tel' | 'off';
    autoCorrect?: boolean;
    autoFocus?: boolean;
    textContentType?: 'emailAddress' | 'password' | 'newPassword' | 'name' | 'telephoneNumber' | 'none';
    returnKeyType?: 'done' | 'go' | 'next' | 'search' | 'send';
    onSubmitEditing?: () => void;
    onFocus?: () => void;
    onBlur?: () => void;
    editable?: boolean;
    maxLength?: number;
    selectionColor?: ColorValue;
    cursorColor?: ColorValue;
    testID?: string;
    nativeID?: string;
    clearButtonMode?: 'never' | 'while-editing' | 'unless-editing' | 'always';
  }

  export interface TextInputHandle {
    focus(): void;
    blur(): void;
    clear(): void;
  }

  export interface ScrollViewProps extends ViewProps {
    contentContainerStyle?: StyleProp<ViewStyle>;
    showsVerticalScrollIndicator?: boolean;
    showsHorizontalScrollIndicator?: boolean;
    horizontal?: boolean;
    keyboardShouldPersistTaps?: 'always' | 'never' | 'handled';
    keyboardDismissMode?: 'none' | 'on-drag' | 'interactive';
    refreshControl?: ReactElement;
    pagingEnabled?: boolean;
    bounces?: boolean;
    scrollEventThrottle?: number;
    onScroll?: (e: { nativeEvent: { contentOffset: { x: number; y: number } } }) => void;
    onMomentumScrollEnd?: (e: {
      nativeEvent: { contentOffset: { x: number; y: number }; layoutMeasurement: { width: number } };
    }) => void;
    contentInsetAdjustmentBehavior?: 'automatic' | 'never';
    ref?: Ref<ScrollViewHandle>;
  }

  export interface ScrollViewHandle {
    scrollTo(opts: { x?: number; y?: number; animated?: boolean }): void;
    scrollToEnd(opts?: { animated?: boolean }): void;
  }

  export interface ListRenderItemInfo<T> {
    item: T;
    index: number;
  }

  export interface FlatListProps<T> extends Omit<ScrollViewProps, 'ref'> {
    data: ReadonlyArray<T> | null | undefined;
    renderItem: (info: ListRenderItemInfo<T>) => ReactElement | null;
    keyExtractor?: (item: T, index: number) => string;
    ListHeaderComponent?: ReactElement | null;
    ListFooterComponent?: ReactElement | null;
    ListEmptyComponent?: ReactElement | null;
    ItemSeparatorComponent?: () => ReactElement | null;
    initialNumToRender?: number;
    windowSize?: number;
    removeClippedSubviews?: boolean;
    extraData?: unknown;
  }

  export interface SectionBase<T> {
    data: ReadonlyArray<T>;
    key?: string;
  }

  export interface SectionListProps<T, S extends SectionBase<T>> extends Omit<ScrollViewProps, 'ref'> {
    sections: ReadonlyArray<S>;
    renderItem: (info: { item: T; index: number; section: S }) => ReactElement | null;
    renderSectionHeader?: (info: { section: S }) => ReactElement | null;
    renderSectionFooter?: (info: { section: S }) => ReactElement | null;
    keyExtractor?: (item: T, index: number) => string;
    stickySectionHeadersEnabled?: boolean;
    ListHeaderComponent?: ReactElement | null;
    ListFooterComponent?: ReactElement | null;
    ListEmptyComponent?: ReactElement | null;
    initialNumToRender?: number;
  }

  export const View: (props: ViewProps) => ReactElement;
  export const Text: (props: TextProps) => ReactElement;
  export const Pressable: (props: PressableProps) => ReactElement;
  export const TextInput: (props: TextInputProps & { ref?: Ref<TextInputHandle> }) => ReactElement;
  export const ScrollView: (props: ScrollViewProps) => ReactElement;
  export type ScrollView = ScrollViewHandle;
  export type TextInput = TextInputHandle;
  export function FlatList<T>(props: FlatListProps<T>): ReactElement;
  export function SectionList<T, S extends SectionBase<T>>(props: SectionListProps<T, S>): ReactElement;
  export const RefreshControl: (props: { refreshing: boolean; onRefresh?: () => void; tintColor?: string; colors?: string[] }) => ReactElement;
  export const KeyboardAvoidingView: (props: ViewProps & { behavior?: 'height' | 'position' | 'padding'; keyboardVerticalOffset?: number; enabled?: boolean }) => ReactElement;
  export const ActivityIndicator: (props: ViewProps & { color?: string; size?: 'small' | 'large' | number }) => ReactElement;

  export const StyleSheet: {
    create<T extends Record<string, ViewStyle | TextStyle>>(styles: T): T;
    flatten<T>(style: StyleProp<T>): T;
    absoluteFillObject: { position: 'absolute'; top: 0; left: 0; right: 0; bottom: 0 };
    absoluteFill: ViewStyle;
    hairlineWidth: number;
  };

  export const Platform: {
    OS: 'ios' | 'android' | 'web';
    Version: number | string;
    select<T>(spec: { ios?: T; android?: T; default?: T }): T;
  };

  export const BackHandler: {
    addEventListener(event: 'hardwareBackPress', handler: () => boolean): { remove(): void };
  };

  export const AccessibilityInfo: {
    announceForAccessibility(message: string): void;
    isReduceMotionEnabled(): Promise<boolean>;
  };

  export const Linking: {
    openURL(url: string): Promise<void>;
    canOpenURL(url: string): Promise<boolean>;
  };

  export const Keyboard: {
    dismiss(): void;
  };

  export type AppStateStatus = 'active' | 'background' | 'inactive';
  export const AppState: {
    currentState: AppStateStatus;
    addEventListener(event: 'change', handler: (s: AppStateStatus) => void): { remove(): void };
  };

  export function useColorScheme(): 'light' | 'dark' | null | undefined;
  export function useWindowDimensions(): { width: number; height: number; fontScale: number; scale: number };
}
