import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Avatar,
  IconButton,
  ListCard,
  Screen,
  SelectRow,
  Text,
  TextButton,
  TextField,
  TopBar,
} from '@/components';
import { useUpdateProfile, useUser } from '@/data/queries';
import { useToastStore } from '@/store/ui';
import { space } from '@/theme';
import { monthShortYear } from '@/utils/dates';
import { initials } from '@/utils/format';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function ProfileScreen() {
  const router = useRouter();
  const user = useUser().data;
  const update = useUpdateProfile();
  const show = useToastStore((s) => s.show);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (!user) return;
    setName(user.name);
    setEmail(user.email);
    setPhone(user.phone);
  }, [user]);

  const nameError = touched && !name.trim() ? 'Enter your name.' : null;
  const emailError =
    touched && !EMAIL.test(email.trim()) ? 'Enter a valid email, like name@example.com.' : null;
  const save = () => {
    setTouched(true);
    if (!name.trim() || !EMAIL.test(email.trim())) return;
    update.mutate(
      { name: name.trim(), email: email.trim(), phone: phone.trim() },
      {
        onSuccess: () => {
          router.back();
          show({ message: 'Profile saved' });
        },
      },
    );
  };

  return (
    <Screen keyboard gap={space[20]}>
      <TopBar title="Profile" trailing={<TextButton label="Save" onPress={save} />} />
      <View style={styles.head}>
        <View>
          <Avatar initials={name.trim() ? initials(name) : (user?.initials ?? '')} size="large" />
          <View style={styles.camera}>
            <IconButton icon="camera" accessibilityLabel="Change photo" />
          </View>
        </View>
        <Text variant="meta" color="muted">
          {user ? `Member since ${monthShortYear(user.memberSince)}` : ''}
        </Text>
      </View>
      <View style={styles.fields}>
        <TextField
          label="Full name"
          value={name}
          onChangeText={setName}
          error={nameError}
          autoComplete="name"
          textContentType="name"
        />
        <TextField
          label="Email"
          value={email}
          onChangeText={setEmail}
          error={emailError}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
          textContentType="emailAddress"
        />
        <TextField
          label="Phone"
          value={phone}
          onChangeText={setPhone}
          keyboardType="phone-pad"
          hint="Used only for sign-in codes."
          autoComplete="tel"
          textContentType="telephoneNumber"
        />
      </View>
      <ListCard>
        <SelectRow icon="rupee" label="Currency" value="₹ INR" />
        <SelectRow icon="calendar" label="Month starts on" value="1st" />
      </ListCard>
      <View style={styles.center}>
        <TextButton label="Delete my account" color="expense" />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  head: { alignItems: 'center', gap: space[10] },
  camera: { position: 'absolute', right: -space[6], bottom: -space[6] },
  fields: { gap: space[14] },
  center: { alignItems: 'center' },
});
