import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import { IconButton } from '@/components/ui/Button';
import { Text } from '@/components/ui/Text';
import { space } from '@/theme';

interface TopBarProps {
  title?: string;
  /** tab: 26/600 title, no back. stack: back circle + 22/600. modal: close circle + 18/600. */
  variant?: 'tab' | 'stack' | 'modal';
  onBack?: () => void;
  trailing?: ReactNode;
  backLabel?: string;
}

export function TopBar({ title = '', variant = 'stack', onBack, trailing, backLabel }: TopBarProps) {
  const router = useRouter();
  const back = onBack ?? (() => (router.canGoBack() ? router.back() : router.replace('/')));
  return (
    <View style={styles.bar}>
      {variant !== 'tab' ? (
        <IconButton
          icon={variant === 'modal' ? 'close' : 'chevL'}
          accessibilityLabel={backLabel ?? (variant === 'modal' ? 'Close' : 'Back')}
          onPress={back}
        />
      ) : null}
      <Text
        variant={variant === 'tab' ? 'title' : variant === 'modal' ? 'profileName' : 'heading'}
        accessibilityRole="header"
        numberOfLines={1}
        style={styles.title}
      >
        {title}
      </Text>
      {trailing}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: { flexDirection: 'row', alignItems: 'center', gap: space[12], minHeight: 44 },
  title: { flex: 1 },
});
