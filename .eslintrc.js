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
};
