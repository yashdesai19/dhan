import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { BottomSheetModalProvider } from '@gorhom/bottom-sheet';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { isRunningInExpoGo } from 'expo';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import * as SystemUI from 'expo-system-ui';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { setSessionExpiredHandler } from '@/data/api/client';
import { PERSIST_MAX_AGE_MS, bindAppFocus, createQueryClient } from '@/data/queries';
import { useSessionStore } from '@/store/session';
import { AppUpdateModal } from '@/components';
import { fontFiles, ThemeProvider, useTheme } from '@/theme';

void SplashScreen.preventAutoHideAsync();
if (!isRunningInExpoGo()) {
  try {
    SplashScreen.setOptions?.({ duration: 250, fade: true });
  } catch {}
}

// The last data the user saw, kept on the device: a cold start (and a sleeping server) shows it
// at once while fresh data loads. Signing out clears the cache, and with it this copy.
const queryPersister = createAsyncStoragePersister({ storage: AsyncStorage, key: 'dhan-query-cache' });

function ThemedStack() {
  const { scheme, colors } = useTheme();
  useEffect(() => {
    void SystemUI.setBackgroundColorAsync(colors.bg);
  }, [colors.bg]);
  return (
    <View style={[styles.fill, { backgroundColor: colors.bg }]}>
      <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}>
        <Stack.Screen name="index" options={{ animation: 'fade' }} />
        <Stack.Screen name="(auth)" options={{ animation: 'fade' }} />
        <Stack.Screen name="(app)" options={{ animation: 'fade' }} />
        <Stack.Screen
          name="lock"
          options={{ presentation: 'fullScreenModal', animation: 'fade', gestureEnabled: false }}
        />
      </Stack>
      <AppUpdateModal />
    </View>
  );
}

export default function RootLayout() {
  const [queryClient] = useState(createQueryClient);
  const [fontsLoaded, fontError] = useFonts(fontFiles);

  useEffect(() => bindAppFocus(), []);
  // When the session can't be renewed: forget the user's data and return to Log in
  useEffect(() => {
    setSessionExpiredHandler(() => {
      queryClient.clear();
      useSessionStore.getState().signOut();
    });
    return () => setSessionExpiredHandler(null);
  }, [queryClient]);

  useEffect(() => {
    if (fontsLoaded || fontError) void SplashScreen.hideAsync();
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) return null;

  return (
    <GestureHandlerRootView style={styles.fill}>
      <SafeAreaProvider>
        <PersistQueryClientProvider
          client={queryClient}
          persistOptions={{ persister: queryPersister, maxAge: PERSIST_MAX_AGE_MS }}
        >
          <ThemeProvider>
            <BottomSheetModalProvider>
              <ThemedStack />
            </BottomSheetModalProvider>
          </ThemeProvider>
        </PersistQueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({ fill: { flex: 1 } });
