// See https://jestjs.io/docs/en/configuration.
module.exports = {
  testEnvironment: 'jsdom',
  testPathIgnorePatterns: [
    '/node_modules/',
    '/static_compiled/',
    '/venv/',
    '/docs/',
    '/.mypy_cache',
    '/.venv/',
  ],
  collectCoverageFrom: ['**/cms/static_src/javascript/**/*.{js,ts}'],
  moduleFileExtensions: ['js', 'ts', 'json', 'node'],
  transform: {
    '^.+\\.(js|ts)$': 'ts-jest',
  },
};
