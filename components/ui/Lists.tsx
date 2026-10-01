// Card, ListCard, ListRow, SelectRow, TransactionRow.
import { Children, Fragment, memo, type ReactNode } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { Icon, type IconName } from '@/components/icons/Icon';
import { iconSize, radius, space, useColors, type ColorName, type TileSize } from '@/theme';
import type { TxView } from '@/utils/describe';
import { IconTile } from './Display';
import { Text } from './Text';
import { Touchable } from './Touchable';

export function Card({
  children,
  style,
  gap = space[14],
  padding = space[18],
  tone,
}: {
  children?: ReactNode;
  style?: StyleProp<ViewStyle>;
  gap?: number;
  padding?: number;
  tone?: 'inset';
}) {
  const c = useColors();
  if (tone === 'inset') {
    return (
      <View
        style={[
          { backgroundColor: c.soft2, borderRadius: radius.field, padding: space[14], gap: space[12] },
          style,
        ]}
      >
        {children}
      </View>
    );
  }
  return (
    <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.line, gap, padding }, style]}>
      {children}
    </View>
  );
}

/** Surface list with a divider between rows (radius 20, padding 4 × 16). */
export function ListCard({ children, style }: { children?: ReactNode; style?: StyleProp<ViewStyle> }) {
  const c = useColors();
  const rows = Children.toArray(children).filter(Boolean);
  return (
    <View style={[styles.listCard, { backgroundColor: c.surface, borderColor: c.line }, style]}>
      {rows.map((row, i) => (
        <Fragment key={i}>
          {i > 0 ? <View style={[styles.divider, { backgroundColor: c.divider }]} /> : null}
          {row}
        </Fragment>
      ))}
    </View>
  );
}

export function Divider() {
  const c = useColors();
  return <View style={[styles.divider, { backgroundColor: c.divider }]} />;
}

export interface ListRowProps {
  leading?: ReactNode;
  title: string;
  subtitle?: string;
  subtitleColor?: ColorName;
  trailing?: ReactNode;
  onPress?: () => void;
  chevron?: boolean;
  /** Vertical padding: 12 (default), 10 (dense lists), 14 (settings rows). */
  pad?: 10 | 12 | 14;
  titleWeight?: 'medium' | 'semibold';
  accessibilityLabel?: string;
  accessibilityHint?: string;
}

function ListRowBase({
  leading,
  title,
  subtitle,
  subtitleColor = 'muted',
  trailing,
  onPress,
  chevron,
  pad = 12,
  titleWeight = 'medium',
  accessibilityLabel,
  accessibilityHint,
}: ListRowProps) {
  const inner = (
    <>
      {leading}
      <View style={styles.rowText}>
        <Text variant="body" weight={titleWeight} numberOfLines={2}>
          {title}
        </Text>
        {subtitle ? (
          <Text variant="meta" color={subtitleColor}>
            {subtitle}
          </Text>
        ) : null}
      </View>
      {trailing}
      {chevron ? <Icon name="chevR" size={iconSize.lg} color="faint" strokeWidth={2} /> : null}
    </>
  );
  const style = [styles.row, { paddingVertical: pad }];
  if (onPress) {
    return (
      <Touchable
        onPress={onPress}
        style={style}
        accessibilityRole="button"
        accessibilityLabel={accessibilityLabel ?? [title, subtitle].filter(Boolean).join(', ')}
        accessibilityHint={accessibilityHint}
      >
        {inner}
      </Touchable>
    );
  }
  return (
    <View style={style} accessible={!!accessibilityLabel} accessibilityLabel={accessibilityLabel}>
      {inner}
    </View>
  );
}

export const ListRow = memo(ListRowBase);

/** Amount on the right of a row, tabular, never wraps. */
export function RowAmount({
  value,
  color = 'ink',
  weight = 'semibold',
  note,
}: {
  value: string;
  color?: ColorName;
  weight?: 'medium' | 'semibold';
  note?: string;
}) {
  return (
    <View style={styles.amount}>
      <Text variant="body" weight={weight} color={color} tabular numberOfLines={1} maxScale={1.4}>
        {value}
      </Text>
      {note ? (
        <Text variant="caption" color="muted">
          {note}
        </Text>
      ) : null}
    </View>
  );
}

export function SelectRow({
  label,
  value,
  icon,
  onPress,
}: {
  label: string;
  value: string;
  icon?: IconName;
  onPress?: () => void;
}) {
  return (
    <Touchable
      onPress={onPress}
      style={[styles.row, styles.selectRow]}
      accessibilityLabel={`${label}, ${value}`}
      accessibilityHint="Opens options"
    >
      {icon ? <IconTile icon={icon} size="sm" /> : null}
      <Text variant="body" color="muted" style={styles.grow}>
        {label}
      </Text>
      <Text variant="body" weight="medium" numberOfLines={1}>
        {value}
      </Text>
      <Icon name="chevR" size={iconSize.lg} color="faint" strokeWidth={2} />
    </Touchable>
  );
}

function TransactionRowBase({
  view,
  onPress,
  tileSize = 'md',
  highlight,
}: {
  view: TxView;
  onPress?: () => void;
  tileSize?: TileSize;
  highlight?: boolean;
}) {
  const c = useColors();
  const tone =
    view.tone === 'income'
      ? 'income'
      : view.tone === 'primary'
        ? 'primary'
        : highlight
          ? 'surface'
          : 'neutral';
  const body = (
    <>
      <IconTile icon={view.icon} tone={tone} size={tileSize} />
      <View style={styles.rowText}>
        <Text variant="body" weight="medium" numberOfLines={1}>
          {view.title}
        </Text>
        <Text variant="meta" color="muted" numberOfLines={1}>
          {view.subtitle}
        </Text>
      </View>
      <RowAmount value={view.amount} color={view.amountColor} note={view.note} />
    </>
  );
  const style = [
    styles.row,
    styles.txRow,
    highlight ? [styles.highlight, { backgroundColor: c.primarySoft }] : null,
  ];
  if (!onPress)
    return (
      <View style={style} accessible accessibilityLabel={view.a11y}>
        {body}
      </View>
    );
  return (
    <Touchable
      onPress={onPress}
      style={style}
      accessibilityLabel={view.a11y}
      accessibilityHint="Opens details"
    >
      {body}
    </Touchable>
  );
}

export const TransactionRow = memo(TransactionRowBase);

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: radius.card },
  listCard: {
    borderWidth: 1,
    borderRadius: radius.card,
    paddingVertical: space[4],
    paddingHorizontal: space[16],
  },
  divider: { height: 1 },
  row: { flexDirection: 'row', alignItems: 'center', gap: space[12], minHeight: 44 },
  rowText: { flex: 1, minWidth: 0, gap: 2 },
  amount: { alignItems: 'flex-end', gap: 2, flexShrink: 0 },
  selectRow: { paddingVertical: space[14] },
  grow: { flex: 1 },
  txRow: { paddingVertical: space[10] },
  highlight: { borderRadius: radius.tile, marginHorizontal: -space[10], paddingHorizontal: space[10] },
});
