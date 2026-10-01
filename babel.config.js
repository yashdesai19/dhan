module.exports = function (api) {
  api.cache(true);
  // babel-preset-expo adds the Reanimated/Worklets plugin automatically (SDK 54).
  return { presets: ['babel-preset-expo'] };
};
