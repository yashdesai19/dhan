// Log in (+ error state), Sign up, Forgot password, Reset link sent, Create first account.
// Mock/local only: no auth service is called (spec §0).
import { useEffect, useState } from 'react';
import { Linking, StyleSheet, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';

import {
  Banner,
  Button,
  CheckboxBox,
  EmptyState,
  Icon,
  Logo,
  Screen,
  StickyFooter,
  Text,
  TextButton,
  TextField,
  TopBar,
  Touchable,
} from '@/components';
import { isApiMode, MOCK_PASSWORD } from '@/data/repositories';

// The demo build pre-fills its sample account; a real account starts blank.
const demo = <T,>(value: T, blank: T): T => (isApiMode ? blank : value);
// How long the server pauses sign-in after too many wrong passwords (the demo pauses for 5)
const PAUSE_MINUTES = isApiMode ? 15 : 5;
import { useAccounts, useRequestReset, useSignIn, useSignUp, useUpsertAccount } from '@/data/queries';
import { useSessionStore } from '@/store/session';
import { iconSize, layout, space, useColors } from '@/theme';
import type { AccountType } from '@/types/domain';
import { groupIN } from '@/utils/format';
import { AccountTypeGrid } from '@/features/accounts/AccountTypeGrid';

const WORDS = ['No', 'One', 'Two', 'Three'];

function PasswordEye({ visible, onToggle }: { visible: boolean; onToggle: () => void }) {
  return (
    <Touchable
      accessibilityLabel={visible ? 'Hide password' : 'Show password'}
      onPress={onToggle}
      style={styles.eye}
    >
      <Icon name="eye" size={iconSize.xl} color="muted" />
    </Touchable>
  );
}

function Divider() {
  const c = useColors();
  return (
    <View style={styles.or}>
      <View style={[styles.orLine, { backgroundColor: c.line }]} />
      <Text variant="meta" color="muted">
        or
      </Text>
      <View style={[styles.orLine, { backgroundColor: c.line }]} />
    </View>
  );
}

export function LoginScreen() {
  const router = useRouter();
  const signIn = useSignIn();
  const startSession = useSessionStore((s) => s.signIn);
  const [email, setEmail] = useState(demo('yash@example.com', ''));
  const [password, setPassword] = useState(demo(MOCK_PASSWORD, ''));
  const [show, setShow] = useState(false);
  const [attemptsLeft, setAttemptsLeft] = useState<number | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);

  const submit = () => {
    setEmailError(null);
    signIn.mutate(
      { email, password },
      {
        onSuccess: () => {
          setAttemptsLeft(null);
          startSession();
          router.replace('/(tabs)');
        },
        onError: (e) => {
          const n = Number(e.message);
          if (Number.isFinite(n)) setAttemptsLeft(n);
          else setEmailError(e.message);
        },
      },
    );
  };

  const pwError = attemptsLeft !== null ? 'That password doesn’t match. Try again or reset it.' : null;
  return (
    <Screen top="stack" gutter={layout.gutterAuth} gap={space[20]} keyboard>
      <View style={styles.heroTop}>
        <Logo size={52} radius={15} />
        <Text variant="displayXl" accessibilityRole="header">
          Welcome back
        </Text>
        <Text variant="bodyLg" color="muted">
          Log in to see where your money stands.
        </Text>
      </View>
      {attemptsLeft !== null ? (
        <Banner icon="alert" tone="error">
          {attemptsLeft > 0
            ? `${WORDS[attemptsLeft] ?? attemptsLeft} attempt${attemptsLeft === 1 ? '' : 's'} left before we pause sign-in for ${PAUSE_MINUTES} minutes.`
            : `Sign-in is paused for ${PAUSE_MINUTES} minutes. Reset your password to get back in now.`}
        </Banner>
      ) : null}
      <TextField
        label="Email"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoComplete="email"
        textContentType="emailAddress"
        error={emailError}
      />
      <TextField
        label="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry={!show}
        autoCapitalize="none"
        autoComplete="password"
        textContentType="password"
        error={pwError}
        returnKeyType="go"
        onSubmitEditing={submit}
        trailing={<PasswordEye visible={show} onToggle={() => setShow(!show)} />}
      />
      <View style={styles.forgot}>
        <TextButton label="Forgot password?" size="sm" onPress={() => router.push('/forgot-password')} />
      </View>
      <Button label="Log in" onPress={submit} loading={signIn.isPending} />
      <Divider />
      <Button
        label="Continue with Google"
        kind="secondary"
        accessibilityHint="Not available in this preview"
      />
      <Button
        label="Continue with Apple"
        kind="secondary"
        accessibilityHint="Not available in this preview"
      />
      <View style={styles.inline}>
        <Text variant="body" color="muted">
          New to DHAN?
        </Text>
        <TextButton label="Create an account" onPress={() => router.push('/sign-up')} />
      </View>
    </Screen>
  );
}

function strength(pw: string): number {
  return [pw.length >= 8, /\d/.test(pw), /[^A-Za-z0-9]/.test(pw), /[A-Z]/.test(pw)].filter(Boolean).length;
}

export function SignUpScreen() {
  const c = useColors();
  const router = useRouter();
  const signUp = useSignUp();
  const [name, setName] = useState(demo('Yash Desai', ''));
  const [email, setEmail] = useState(demo('yash@example.com', ''));
  const [password, setPassword] = useState(demo('dhan-2026-secure', ''));
  const [agree, setAgree] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const score = strength(password);
  const label = score >= 3 ? 'Strong password' : score === 2 ? 'Fair password' : 'Weak password';

  const submit = () => {
    setError(null);
    if (!agree) {
      setError('Please agree to the Terms to continue.');
      return;
    }
    signUp.mutate(
      { name, email, password },
      { onSuccess: () => router.push('/create-first-account'), onError: (e) => setError(e.message) },
    );
  };

  return (
    <Screen top="stack" gutter={layout.gutterAuth} gap={space[20]} keyboard>
      <TopBar onBack={() => (router.canGoBack() ? router.back() : router.replace('/onboarding'))} />
      <View style={styles.gap10}>
        <Text variant="display" accessibilityRole="header">
          Create your account
        </Text>
        <Text variant="bodyLg" color="muted">
          Takes under a minute. No bank login needed.
        </Text>
      </View>
      <TextField
        label="Full name"
        value={name}
        onChangeText={setName}
        autoComplete="name"
        textContentType="name"
        autoCapitalize="words"
      />
      <TextField
        label="Email"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoComplete="email"
      />
      <View style={styles.gap8}>
        <TextField
          label="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
        />
        <View style={styles.meter} accessible accessibilityLabel={label}>
          {[0, 1, 2, 3].map((i) => (
            <View
              key={i}
              style={[
                styles.meterBar,
                { backgroundColor: i < score ? (score >= 3 ? c.primary : c.warn) : c.track },
              ]}
            />
          ))}
        </View>
        <Text variant="meta" weight="medium" color={score >= 3 ? 'primary' : 'warnText'}>
          {label}
        </Text>
      </View>
      <Touchable
        accessibilityRole="checkbox"
        accessibilityState={{ checked: agree }}
        accessibilityLabel="I agree to the Terms and Privacy Policy"
        onPress={() => setAgree(!agree)}
        style={styles.terms}
      >
        <CheckboxBox checked={agree} size={22} radius={6} />
        <Text variant="small" color="muted" style={styles.flex}>
          I agree to the{' '}
          <Text variant="small" color="primary">
            Terms
          </Text>{' '}
          and{' '}
          <Text variant="small" color="primary">
            Privacy Policy
          </Text>
          .
        </Text>
      </Touchable>
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
      <Button label="Create account" onPress={submit} loading={signUp.isPending} />
      <View style={styles.inline}>
        <Text variant="body" color="muted">
          Already have an account?
        </Text>
        <TextButton label="Log in" onPress={() => router.replace('/login')} />
      </View>
    </Screen>
  );
}

export function ForgotPasswordScreen() {
  const router = useRouter();
  const reset = useRequestReset();
  const [email, setEmail] = useState('yash@example.com');
  const [error, setError] = useState<string | null>(null);
  return (
    <Screen top="stack" gutter={layout.gutterAuth} gap={space[24]} keyboard>
      <TopBar />
      <View style={styles.gap10}>
        <Text variant="display" accessibilityRole="header">
          Reset your password
        </Text>
        <Text variant="bodyLg" color="muted">
          Enter the email you signed up with. We’ll send a link to set a new password.
        </Text>
      </View>
      <TextField
        label="Email"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoFocus
        error={error}
      />
      <Button
        label="Send reset link"
        loading={reset.isPending}
        onPress={() =>
          reset.mutate(email, {
            onSuccess: () => router.push({ pathname: '/forgot-password-sent', params: { email } }),
            onError: (e) => setError(e.message),
          })
        }
      />
    </Screen>
  );
}

export function ForgotSentScreen() {
  const router = useRouter();
  const { email = 'yash@example.com' } = useLocalSearchParams<{ email: string }>();
  const resend = useRequestReset();
  const [secs, setSecs] = useState(42);
  useEffect(() => {
    if (secs <= 0) return;
    const t = setTimeout(() => setSecs(secs - 1), 1000);
    return () => clearTimeout(t);
  }, [secs]);
  return (
    <Screen top="stack" gutter={layout.gutterAuth} scroll={false} gap={0}>
      <TopBar />
      <View style={styles.centerFill}>
        <EmptyState
          icon="mail"
          title="Check your inbox"
          body={
            isApiMode
              ? `If ${email} has a DHAN account, we sent it a reset code. It expires in 30 minutes.`
              : `We sent a reset link to ${email}. It expires in 30 minutes.`
          }
        />
      </View>
      <View style={styles.gap10}>
        <Button
          label="Open email app"
          onPress={() => void Linking.openURL('mailto:').catch(() => undefined)}
        />
        {isApiMode ? (
          <Button label="I have a code" kind="secondary" onPress={() => router.push('/reset-password')} />
        ) : null}
        <Button label="Back to log in" kind="secondary" onPress={() => router.replace('/login')} />
        <View style={styles.center}>
          {secs > 0 ? (
            <Text variant="small" color="muted" style={styles.resend}>
              {`Didn’t get it? Resend in 0:${String(secs).padStart(2, '0')}`}
            </Text>
          ) : (
            <TextButton
              label="Resend link"
              size="sm"
              onPress={() => {
                setSecs(42);
                resend.mutate(email);
              }}
            />
          )}
        </View>
      </View>
    </Screen>
  );
}

export function CreateFirstAccountScreen() {
  const router = useRouter();
  const accounts = useAccounts().data ?? [];
  const upsert = useUpsertAccount();
  const startSession = useSessionStore((s) => s.signIn);
  const [type, setType] = useState<AccountType>('bank');
  const [name, setName] = useState(demo('HDFC Bank', ''));
  const [balance, setBalance] = useState(demo('₹86,450', '₹0'));
  const [error, setError] = useState<string | null>(null);

  const enter = () => {
    startSession();
    router.replace('/(tabs)');
  };
  const submit = () => {
    const value = Number(balance.replace(/[^\d-]/g, ''));
    if (!name.trim()) return setError('Give the account a name.');
    const existing = accounts.find((a) => a.name.toLowerCase() === name.trim().toLowerCase());
    upsert.mutate(
      existing
        ? { ...existing, type, balance: value }
        : {
            name,
            type,
            subtitle: type === 'cash' ? 'In hand' : 'Savings',
            balance: value,
            includeInTotal: true,
          },
      { onSuccess: enter, onError: (e) => setError(e.message) },
    );
  };

  return (
    <Screen
      top="stack"
      gutter={layout.gutterAuth}
      gap={space[20]}
      bottom="footer"
      keyboard
      overlay={
        <StickyFooter>
          <Button label="Continue" onPress={submit} loading={upsert.isPending} disabled={!name.trim()} />
        </StickyFooter>
      }
    >
      <View style={styles.header}>
        <Logo size={32} radius={9} />
        <TextButton label="Skip for now" color="muted" onPress={enter} />
      </View>
      <View style={styles.gap10}>
        <Text variant="display" accessibilityRole="header">
          Add your first account
        </Text>
        <Text variant="bodyLg" color="muted">
          Where do you keep most of your money? Start with one, add the rest anytime.
        </Text>
      </View>
      <AccountTypeGrid value={type} onChange={setType} />
      <TextField label="Account name" value={name} onChangeText={setName} error={error} />
      <TextField
        label="Current balance"
        value={balance}
        onChangeText={(v) => setBalance(`₹${groupIN(Number(v.replace(/[^\d]/g, '') || '0'))}`)}
        keyboardType="number-pad"
        hint="Check your bank app for today’s balance."
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  heroTop: { gap: space[18], paddingTop: space[24] },
  eye: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center', marginRight: -space[10] },
  forgot: { alignItems: 'flex-end', marginTop: -space[12] },
  or: { flexDirection: 'row', alignItems: 'center', gap: space[12] },
  orLine: { flex: 1, height: 1 },
  inline: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: space[6],
    flexWrap: 'wrap',
  },
  gap10: { gap: space[10] },
  gap8: { gap: space[8] },
  meter: { flexDirection: 'row', gap: space[4] },
  meterBar: { flex: 1, height: 4, borderRadius: 2 },
  terms: { flexDirection: 'row', gap: space[12], alignItems: 'flex-start', minHeight: 44 },
  flex: { flex: 1 },
  centerFill: { flex: 1, justifyContent: 'center' },
  center: { alignItems: 'center' },
  resend: { paddingTop: space[6], minHeight: 44, textAlignVertical: 'center' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
});
