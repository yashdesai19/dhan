import { useState } from 'react';
import { useRouter } from 'expo-router';

import { Banner, Button, Screen, StickyFooter, TextField, TopBar } from '@/components';
import { useCreateGroup } from '@/data/queries';
import { useToastStore } from '@/store/ui';
import { space } from '@/theme';

export function NewGroupScreen() {
  const router = useRouter();
  const create = useCreateGroup();
  const show = useToastStore((s) => s.show);
  const [name, setName] = useState('');
  const [emails, setEmails] = useState('');
  const [error, setError] = useState<string | null>(null);

  const save = () => {
    setError(null);
    create.mutate(
      { name, memberEmails: emails.split(/[\s,;]+/) },
      {
        onSuccess: () => {
          router.back();
          show({ message: `${name.trim()} created`, placement: 'bottom' });
        },
        onError: (e) => setError(e.message),
      },
    );
  };

  return (
    <Screen
      bottom="footer"
      gap={space[20]}
      keyboard
      overlay={
        <StickyFooter>
          <Button label="Create group" onPress={save} loading={create.isPending} disabled={!name.trim()} />
        </StickyFooter>
      }
    >
      <TopBar variant="modal" title="New group" />
      <TextField label="Group name" value={name} onChangeText={setName} placeholder="Goa Trip" />
      <TextField
        label="Members’ emails"
        value={emails}
        onChangeText={setEmails}
        placeholder="aman@example.com, rahul@example.com"
        keyboardType="email-address"
        autoCapitalize="none"
        hint="People need a DHAN account to be added. You can add more later."
      />
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}
