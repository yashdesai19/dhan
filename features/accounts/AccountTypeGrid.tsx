import { StyleSheet, View } from 'react-native';

import { Icon, type IconName } from '@/components/icons/Icon';
import { Text } from '@/components/ui/Text';
import { Touchable } from '@/components/ui/Touchable';
import { iconSize, radius, space, useColors } from '@/theme';
import type { AccountType } from '@/types/domain';

const TYPES: { value: AccountType; label: string; icon: IconName }[] = [
  { value: 'bank', label: 'Bank', icon: 'bank' },
  { value: 'cash', label: 'Cash', icon: 'cash' },
  { value: 'savings', label: 'Savings', icon: 'coin' },
  { value: 'credit', label: 'Credit card', icon: 'card' },
  { value: 'wallet', label: 'Wallet', icon: 'wallet' },
  { value: 'custom', label: 'Custom', icon: 'tag' },
];

/** 3 × 2 account type picker (Create first account, Add / edit account). */
export function AccountTypeGrid({
  value,
  onChange,
}: {
  value: AccountType;
  onChange: (v: AccountType) => void;
}) {
  const c = useColors();
  return (
    <View style={styles.grid} accessibilityRole="radiogroup" accessibilityLabel="Account type">
      {TYPES.map((t) => {
        const on = t.value === value;
        return (
          <Touchable
            key={t.value}
            accessibilityRole="radio"
            accessibilityLabel={t.label}
            accessibilityState={{ selected: on }}
            onPress={() => onChange(t.value)}
            style={[
              styles.cell,
              {
                backgroundColor: on ? c.primarySoft : c.surface,
                borderColor: on ? c.primary : c.line,
                borderWidth: on ? 2 : 1,
              },
            ]}
          >
            <Icon name={t.icon} size={iconSize.xxl} color={on ? 'primary' : 'ink'} />
            <Text variant="small" weight="medium">
              {t.label}
            </Text>
          </Touchable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: space[10] },
  cell: { width: '31%', flexGrow: 1, gap: space[10], padding: space[14], borderRadius: radius.button },
});
