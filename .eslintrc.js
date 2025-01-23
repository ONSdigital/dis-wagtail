module.exports = {
  root: true,
  // See https://github.com/wagtail/eslint-config-wagtail for rules.
  extends: ['@wagtail/eslint-config-wagtail', 'plugin:@typescript-eslint/recommended'],
  env: {
    browser: true,
    commonjs: true,
    es6: true,
    jest: true,
  },
  settings: {
    // Manually set the version to disable automated detection of the "react" dependency.
    react: { version: '999.999.999' },
  },
};
