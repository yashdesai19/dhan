import { useEffect, useState } from 'react';
import { Modal, StyleSheet, View } from 'react-native';
import * as Linking from 'expo-linking';
import Constants from 'expo-constants';

import { API_URL } from '@/data/api/config';
import { Button } from '@/components/ui/Button';
import { Icon } from '@/components/icons/Icon';
import { Pill } from '@/components/ui/Display';
import { Text } from '@/components/ui/Text';
import { radius, space, useColors } from '@/theme';

interface AppVersionResponse {
  latest_version: string;
  min_version?: string;
  download_url: string;
  release_notes?: string;
  force_update?: boolean;
}

/**
 * Compare two semver strings (e.g., '1.0.1' > '1.0.0').
 */
function isNewerVersion(latest: string, current: string): boolean {
  const parse = (v: string) =>
    v
      .replace(/^v/, '')
      .split('.')
      .map((n) => parseInt(n, 10) || 0);
  const [lMaj = 0, lMin = 0, lPat = 0] = parse(latest);
  const [cMaj = 0, cMin = 0, cPat = 0] = parse(current);
  if (lMaj !== cMaj) return lMaj > cMaj;
  if (lMin !== cMin) return lMin > cMin;
  return lPat > cPat;
}

export function AppUpdateModal() {
  const c = useColors();
  const [updateInfo, setUpdateInfo] = useState<AppVersionResponse | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let active = true;

    async function checkVersion() {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 6000);
        const res = await fetch(`${API_URL}/app-version`, { signal: controller.signal });
        clearTimeout(timer);
        if (!res.ok) return;

        const data: AppVersionResponse = await res.json();
        const currentVersion = Constants.expoConfig?.version ?? '1.0.0';

        if (active && data.latest_version && isNewerVersion(data.latest_version, currentVersion)) {
          setUpdateInfo(data);
          setVisible(true);
        }
      } catch {
        // Silently skip if network is unreachable or offline
      }
    }

    void checkVersion();
    return () => {
      active = false;
    };
  }, []);

  if (!visible || !updateInfo) return null;

  const currentVersion = Constants.expoConfig?.version ?? '1.0.0';

  const handleUpdate = () => {
    if (updateInfo.download_url) {
      void Linking.openURL(updateInfo.download_url);
    }
  };

  const handleDismiss = () => {
    if (!updateInfo.force_update) {
      setVisible(false);
    }
  };

  return (
    <Modal
      transparent
      animationType="fade"
      visible={visible}
      onRequestClose={handleDismiss}
    >
      <View style={styles.backdrop}>
        <View style={[styles.card, { backgroundColor: c.surface, borderColor: c.btnBorder }]}>
          <View style={[styles.iconCircle, { backgroundColor: c.primarySoft }]}>
            <Icon name="download" size={28} color="primary" />
          </View>

          <View style={styles.pillWrapper}>
            <Pill label={`v${updateInfo.latest_version} Available`} tone="solid" small />
          </View>

          <Text variant="heading" align="center" style={styles.title}>
            New Update Available! 🚀
          </Text>

          <Text variant="body" color="muted" align="center" style={styles.notes}>
            {updateInfo.release_notes || 'A fresh update of DHAN is available with latest improvements and bug fixes.'}
          </Text>

          <Text variant="meta" color="faint" align="center" style={styles.versionSub}>
            Current: v{currentVersion} → New: v{updateInfo.latest_version}
          </Text>

          <View style={styles.buttonCol}>
            <Button
              label="Update Now"
              kind="primary"
              icon="download"
              onPress={handleUpdate}
            />
            {!updateInfo.force_update && (
              <Button
                label="Maybe Later"
                kind="ghost"
                onPress={handleDismiss}
                style={styles.laterButton}
              />
            )}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: space[20],
  },
  card: {
    width: '100%',
    maxWidth: 340,
    borderRadius: radius.card,
    borderWidth: 1,
    padding: space[24],
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 10,
  },
  iconCircle: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: space[12],
  },
  pillWrapper: {
    marginBottom: space[8],
  },
  title: {
    marginBottom: space[4],
  },
  notes: {
    marginTop: space[4],
    marginBottom: space[8],
    lineHeight: 20,
  },
  versionSub: {
    marginBottom: space[20],
  },
  buttonCol: {
    width: '100%',
    gap: space[8],
  },
  laterButton: {
    marginTop: space[4],
  },
});
