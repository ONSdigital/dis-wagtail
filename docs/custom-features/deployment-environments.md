# Deployment Environments

In the interest of security, the application is deployed to 2 separate environments: The "internal" and "external" environments.

The `IS_EXTERNAL_ENV` environment variable (and setting) is used to switch the app to the "external" environment.

## "Internal" environment

The internal is private and only accessible to ONS staff.

The Wagtail admin is only accessible on the "internal" environment.

Management commands, database migrations, and other [scheduled jobs](./scheduled-jobs.md) are only executed in the internal environment.

## External

The "external" environment is the one used by the public.

Writeable database access is restricted to a limited set of tables. This is enforced both at the database level and using database router (see `cms.core.db_router.ExternalEnvRouter`).

The URLs and apps required for the Wagtail admin are disabled. This includes the middleware required for authentication.

Only a subset of media stored in S3 are accessible to the external env. Notably the `images/*` prefix needed for Wagtail's rendition generation.

Certain static files (for example those related to the Wagtail admin) are inaccessible in the external environment. This is configured using `cms.core.whitenoise.CMSWhiteNoiseMiddleware`.
