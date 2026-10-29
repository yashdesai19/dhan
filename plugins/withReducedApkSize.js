const { withGradleProperties } = require('@expo/config-plugins');

/**
 * Expo Config Plugin to optimize Android APK size down to ~20-25MB.
 * Targets arm64-v8a (which powers 99%+ of modern physical Android devices).
 * Removes unused x86, x86_64, and armeabi-v7a native C++ libraries.
 */
module.exports = function withReducedApkSize(config) {
  return withGradleProperties(config, (config) => {
    config.modResults = config.modResults.filter(
      (item) => item.key !== 'reactNativeArchitectures'
    );
    config.modResults.push({
      type: 'property',
      key: 'reactNativeArchitectures',
      value: 'arm64-v8a',
    });
    return config;
  });
};

