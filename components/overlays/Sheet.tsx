import { createContext, useCallback, useContext, useEffect, useRef, type ReactNode } from 'react';
import { BackHandler, StyleSheet, View } from 'react-native';
import BottomSheet, {
  BottomSheetBackdrop,
  BottomSheetView,
  type BottomSheetBackdropProps,
} from '@gorhom/bottom-sheet';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';

import { Icon, type IconName } from '@/components/icons/Icon';
import { Button, IconButton } from '@/components/ui/Button';
import { Text } from '@/components/ui/Text';
import { haptics } from '@/hooks/feedback';
import { layout, radius, size, space, useColors, type ColorName } from '@/theme';

interface SheetApi {
  /** Animate the sheet down, then run `then` (usually a navigation). */
  close: (then?: () => void) => void;
}

const SheetContext = createContext<SheetApi>({ close: (then) => then?.() });
export const useSheet = () => useContext(SheetContext);

interface SheetProps {
  children: ReactNode;
  title?: string;
  /** Screen-reader name of the dialog. */
  label: string;
  /** Replaces the close button in the title row (Filters shows Reset). */
  headerRight?: ReactNode;
}

/**
 * Bottom sheet route body (spec §3, §9): radius 28 top corners, 40 × 5 handle, scrim behind.
 * Closes on scrim tap, swipe down and Android back; closing pops the route.
 */
export function Sheet({ children, title, label, headerRight }: SheetProps) {
  const c = useColors();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const ref = useRef<BottomSheet>(null);
  const after = useRef<(() => void) | null>(null);

  const close = useCallback((then?: () => void) => {
    after.current = then ?? null;
    ref.current?.close();
  }, []);

  const onClose = useCallback(() => {
    const next = after.current;
    after.current = null;
    if (router.canGoBack()) router.back();
    next?.();
  }, [router]);

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      close();
      return true;
    });
    return () => sub.remove();
  }, [close]);

  const renderBackdrop = useCallback(
    (p: BottomSheetBackdropProps) => (
      <BottomSheetBackdrop
        {...p}
        appearsOnIndex={0}
        disappearsOnIndex={-1}
        pressBehavior="close"
        opacity={1}
        style={[p.style, { backgroundColor: c.scrim }]}
        accessibilityLabel="Close"
      />
    ),
    [c.scrim],
  );

  return (
    <SheetContext.Provider value={{ close }}>
      <View style={StyleSheet.absoluteFill}>
        <BottomSheet
          ref={ref}
          index={0}
          enableDynamicSizing
          enablePanDownToClose
          onClose={onClose}
          backdropComponent={renderBackdrop}
          backgroundStyle={{
            backgroundColor: c.sheet,
            borderTopLeftRadius: radius.sheet,
            borderTopRightRadius: radius.sheet,
          }}
          handleIndicatorStyle={{
            backgroundColor: c.btnBorder,
            width: size.sheetHandleW,
            height: size.sheetHandleH,
          }}
          handleStyle={{ paddingTop: layout.sheetPad.top }}
          keyboardBehavior="interactive"
          keyboardBlurBehavior="restore"
          android_keyboardInputMode="adjustResize"
          accessible={false}
        >
          <BottomSheetView
            accessibilityViewIsModal
            accessibilityLabel={label}
            style={[styles.body, { paddingBottom: Math.max(insets.bottom, layout.sheetPad.bottom) }]}
          >
            {title ? (
              <View style={styles.header}>
                <Text variant="sheetTitle" accessibilityRole="header" style={styles.grow}>
                  {title}
                </Text>
                {headerRight ?? (
                  <IconButton icon="close" accessibilityLabel="Close" onPress={() => close()} />
                )}
              </View>
            ) : null}
            {children}
          </BottomSheetView>
        </BottomSheet>
      </View>
    </SheetContext.Provider>
  );
}

interface ConfirmSheetProps {
  icon: IconName;
  tone?: 'danger' | 'neutral';
  title: string;
  body: string;
  confirmLabel: string;
  cancelLabel?: string;
  onConfirm: () => void;
  loading?: boolean;
}

/** Icon circle, title, body and two stacked buttons (Delete, Sign out). */
export function ConfirmSheet({
  icon,
  tone = 'danger',
  title,
  body,
  confirmLabel,
  cancelLabel = 'Cancel',
  onConfirm,
  loading,
}: ConfirmSheetProps) {
  const c = useColors();
  const { close } = useSheet();
  const circle: { bg: ColorName; fg: ColorName } =
    tone === 'danger' ? { bg: 'expenseSoft', fg: 'expense' } : { bg: 'soft', fg: 'ink' };
  useEffect(() => {
    if (tone === 'danger') haptics.warning();
  }, [tone]);
  return (
    <>
      <View style={styles.confirm}>
        <View style={[styles.confirmIcon, { backgroundColor: c[circle.bg] }]}>
          <Icon name={icon} size={26} color={circle.fg} />
        </View>
        <Text variant="sheetTitle" align="center" accessibilityRole="header" style={styles.confirmTitle}>
          {title}
        </Text>
        <Text variant="body" color="muted" align="center" style={styles.confirmBody}>
          {body}
        </Text>
      </View>
      <Button label={confirmLabel} kind="danger" onPress={onConfirm} loading={loading} />
      <Button label={cancelLabel} kind="secondary" onPress={() => close()} />
    </>
  );
}

const styles = StyleSheet.create({
  body: { paddingHorizontal: layout.sheetPad.side, gap: layout.sheetPad.gap, paddingTop: space[8] },
  header: { flexDirection: 'row', alignItems: 'center', gap: space[12] },
  grow: { flex: 1 },
  confirm: { alignItems: 'center', gap: space[10], paddingTop: space[6] },
  confirmIcon: {
    width: size.confirmIcon,
    height: size.confirmIcon,
    borderRadius: size.confirmIcon / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  confirmTitle: { paddingTop: space[4] },
  confirmBody: { maxWidth: 300 },
});
