# ONS — Continuous Integration

## Code styleguide

This project’s code formatting is enforced with [Prettier](https://prettier.io/) for supported languages, [ruff](https://github.com/astral-sh/ruff) for Python, and [djhtml](https://github.com/rtts/djhtml) for templates. Make sure to have all integrated with your editor to auto-format when saving files, or to manually run them before committing (`npm run format` for Prettier).

## Automatic linting locally

You can also run the linting tests automatically before committing. This is optional. It uses pre-commit, which is installed by default in the vagrant box, and a .pre-commit-config.yml file is included for the project.

To use when making commits on your host machine you must install pre-commit, either create a virtualenv to use with the project or to install globally see instructions at (https://pre-commit.com/#install).

Pre-commit will not run by default. To set it up, run `pre-commit install` inside the Vagrant box, or on the host if you have installed pre-commit there.

The `detect-secrets` pre-commit hook requires a baseline secrets file to be included. If you need to, you can update this file, e.g. when adding dummy secrets for unit tests:

```bash
$ detect-secrets scan > .secrets.baseline
```
