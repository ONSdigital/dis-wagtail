import js from '@eslint/js';
import wagtailConfig from '@wagtail/eslint-config-wagtail';
import globals from 'globals';

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
        ],
    },

    js.configs.recommended,
    {
        settings: {
            react: { version: '999.999.999' },
        },
    },
    ...wagtailConfig,

    {
        files: ['**/*.js'],

        languageOptions: {
            ecmaVersion: 2026,
            sourceType: 'module',
            globals: {
                ...globals.browser,
                ...globals.node,
            },
        },
    },
];
