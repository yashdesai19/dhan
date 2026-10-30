import { useEffect, useState } from 'react';
import { ActivityIndicator, Modal, Platform, StyleSheet, View } from 'react-native';
import * as Linking from 'expo-linking';
import Constants from 'expo-constants';
import * as FileSystem from 'expo-file-system/legacy';
import * as IntentLauncher from 'expo-intent-launcher';
import * as Updates from 'expo-updates';

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
  const [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('');
  // 'ota': new app code published with `eas update`, applied in place with a restart.
  // 'apk': a new native build, which has to be downloaded and installed.
  const [kind, setKind] = useState<'ota' | 'apk'>('apk');

  useEffect(() => {
    let active = true;

    async function checkVersion() {
      try {
        if (Updates.isEnabled && !__DEV__) {
          const check = await Updates.checkForUpdateAsync();
          if (check.isAvailable) {
            if (!active) return;
            setKind('ota');
            setUpdateInfo({
              latest_version: Constants.expoConfig?.version ?? '1.0.0',
              download_url: '',
              release_notes: 'New improvements and fixes are ready. Tap Update to restart DHAN with them.',
            });
            setVisible(true);
            return;
          }
        }
      } catch {
        // No update server reachable: fall through to the APK version check
      }

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

  const handleUpdate = async () => {
    if (kind === 'ota') {
      try {
        setDownloading(true);
        setStatusText('Downloading update...');
        setProgress(0);
        await Updates.fetchUpdateAsync();
        setProgress(100);
        await Updates.reloadAsync();
      } catch (err) {
        console.warn('Update download failed:', err);
        setDownloading(false);
      }
      return;
    }
    if (!updateInfo.download_url) return;

    // On Android, download directly within the app and launch Package Installer
    if (Platform.OS === 'android') {
      try {
        setDownloading(true);
        setStatusText('Downloading update...');
        setProgress(0);

        const targetPath = `${FileSystem.cacheDirectory}dhan_update.apk`;

        // Clean up previous APK cache if it exists
        const fileInfo = await FileSystem.getInfoAsync(targetPath);
        if (fileInfo.exists) {
          await FileSystem.deleteAsync(targetPath, { idempotent: true });
        }

        const downloadResumable = FileSystem.createDownloadResumable(
          updateInfo.download_url,
          targetPath,
          {},
          (downloadProgress) => {
            const expected = downloadProgress.totalBytesExpectedToWrite;
            if (expected > 0) {
              const pct = Math.min(
                100,
                Math.round((downloadProgress.totalBytesWritten / expected) * 100)
              );
              setProgress(pct);
            }
          }
        );

        const result = await downloadResumable.downloadAsync();
        if (!result || !result.uri) {
          throw new Error('Download failed');
        }

        setStatusText('Opening installer...');
        setProgress(100);

        // Convert file URI to Android Content URI
        const contentUri = await FileSystem.getContentUriAsync(result.uri);

        // Prompt native Android package installer
        await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
          data: contentUri,
          type: 'application/vnd.android.package-archive',
          flags: 1, // Intent.FLAG_GRANT_READ_URI_PERMISSION
        });

        setDownloading(false);
      } catch (err) {
        console.warn('In-app installer error, falling back to browser:', err);
        setDownloading(false);
        // Fallback to browser download if permission or intent fails
        void Linking.openURL(updateInfo.download_url);
      }
    } else {
      // iOS / Web fallback
      void Linking.openURL(updateInfo.download_url);
    }
  };

  const handleDismiss = () => {
    if (!updateInfo.force_update && !downloading) {
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
            {downloading
              ? `${statusText} (${progress}%)`
              : updateInfo.release_notes || 'A fresh update of DHAN is available with latest improvements and bug fixes.'}
          </Text>

          {downloading ? (
            <View style={styles.progressContainer}>
              <View style={[styles.progressBarBg, { backgroundColor: c.track }]}>
                <View
                  style={[
                    styles.progressBarFill,
                    { backgroundColor: c.primary, width: `${progress}%` },
                  ]}
                />
              </View>
              <Text variant="meta" color="muted" align="center" style={styles.progressText}>
                {progress}% downloaded
              </Text>
            </View>
          ) : (
            <Text variant="meta" color="faint" align="center" style={styles.versionSub}>
              Current: v{currentVersion} → New: v{updateInfo.latest_version}
            </Text>
          )}

          <View style={styles.buttonCol}>
            {downloading ? (
              <Button
                label={`Downloading... ${progress}%`}
                kind="primary"
                disabled
                loading
              />
            ) : (
              <Button
                label="Update Now"
                kind="primary"
                icon="download"
                onPress={handleUpdate}
              />
            )}

            {!updateInfo.force_update && !downloading && (
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
  progressContainer: {
    width: '100%',
    marginVertical: space[16],
    alignItems: 'center',
  },
  progressBarBg: {
    width: '100%',
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  progressText: {
    marginTop: space[8],
  },
  buttonCol: {
    width: '100%',
    gap: space[8],
  },
  laterButton: {
    marginTop: space[4],
  },
});
