import js from '@eslint/js';
import wagtailConfig from '@wagtail/eslint-config-wagtail';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default [
  {
    ignores: [
      'node_modules/**',
      'coverage/**',
      'cms/jinja2/',
      'cms/static_compiled/',
      'static/',
      'venv/**',
      '.mypy_cache/**',
      '.venv/**',
      '.coverage',
      '**/vendor/*',
      '!.stylelintrc.js',
    ],
  },

  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...wagtailConfig,

  {
    files: ['**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx'],

    languageOptions: {
      ecmaVersion: 2026,
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        ...globals.jest,
        ...globals.node,
      },
    },

    settings: {
      react: {
        version: 'detect',
      },
    },
  },
];
