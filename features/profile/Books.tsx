import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Banner,
  Button,
  Icon,
  IconTile,
  ListCard,
  ListRow,
  Screen,
  SectionLabel,
  TextField,
  TopBar,
} from '@/components';
import { useCreateBook } from '@/data/queries';
import { useActiveBook } from '@/features/shared/hooks';
import { usePrefsStore } from '@/store/prefs';
import { useToastStore } from '@/store/ui';
import { iconSize, space } from '@/theme';

export function BooksScreen() {
  const router = useRouter();
  const { id, books } = useActiveBook();
  const set = usePrefsStore((s) => s.set);
  const show = useToastStore((s) => s.show);
  const create = useCreateBook();
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const add = () => {
    setError(null);
    create.mutate(name.trim(), {
      onSuccess: (b) => {
        setName('');
        set('activeBookId', b.id);
        show({ message: `${b.name} is ready`, placement: 'bottom' });
      },
      onError: (e) => setError(e.message),
    });
  };

  return (
    <Screen gap={space[20]} keyboard>
      <TopBar title="Books" />
      <Banner icon="info" tone="neutral">
        Keep each business apart from your personal money, with its own accounts and profit. Moving money
        between books is a transfer, so it never counts as income or spending.
      </Banner>
      <ListCard>
        {books.map((b) => (
          <ListRow
            key={b.id}
            leading={<IconTile icon={b.kind === 'business' ? 'briefcase' : 'home'} size="sm" />}
            title={b.name}
            subtitle={b.kind === 'business' ? 'Business' : 'Your own money'}
            trailing={b.id === id ? <Icon name="check" size={iconSize.lg} color="primary" /> : undefined}
            onPress={() => {
              set('activeBookId', b.id);
              router.back();
            }}
          />
        ))}
      </ListCard>
      <View style={styles.gap10}>
        <SectionLabel>Add a business</SectionLabel>
        <TextField
          label="Business name"
          value={name}
          onChangeText={setName}
          placeholder="Sharma Traders"
          maxLength={60}
        />
        <Button label="Create book" onPress={add} loading={create.isPending} disabled={!name.trim()} />
      </View>
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({ gap10: { gap: space[10] } });
