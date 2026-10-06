import { useState } from 'react';
import { useRouter } from 'expo-router';

import { Banner, Button, Screen, Text, TextField, TopBar } from '@/components';
import { useConfirmReset } from '@/data/queries';
import { layout, space } from '@/theme';

/** Second half of password reset: the code from the email plus a new password. */
export function ResetPasswordScreen() {
  const router = useRouter();
  const confirm = useConfirmReset();
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const submit = () => {
    setError(null);
    confirm.mutate(
      { code, password },
      { onSuccess: () => setDone(true), onError: (e) => setError(e.message) },
    );
  };

  return (
    <Screen top="stack" gutter={layout.gutterAuth} gap={space[20]} keyboard>
      <TopBar />
      <Text variant="display" accessibilityRole="header">
        Set a new password
      </Text>
      {done ? (
        <>
          <Banner icon="check" tone="primary">
            Your password has been changed. Log in with the new one.
          </Banner>
          <Button label="Back to log in" onPress={() => router.replace('/login')} />
        </>
      ) : (
        <>
          <TextField
            label="Reset code"
            value={code}
            onChangeText={setCode}
            autoCapitalize="none"
            hint="It’s in the reset email."
          />
          <TextField
            label="New password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoCapitalize="none"
            hint="At least 8 characters."
            error={error}
          />
          <Button
            label="Change password"
            onPress={submit}
            loading={confirm.isPending}
            disabled={!code.trim() || password.length < 8}
          />
        </>
      )}
    </Screen>
  );
}
