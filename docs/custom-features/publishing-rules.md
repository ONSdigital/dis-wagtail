# Publishing rules

All pages must go through the publishing workflow in order to be published.
Only pages that are not part of a bundle can be manually published.

We achieve that by extending the core page permission tester logic for `can_publish` and `can_publish_subpage`.
See `BasePagePermissionTester` in `cms/core/permission_testers.py`.

Additionally, our workflows module tidies up the page action menu based on the stage of the workflow and the
various conditions around it. See `cms/workflows/wagtail_hooks.py`


## Local development

To bypass the workflow enforcement locally, set `ALLOW_DIRECT_PUBLISHING_IN_DEVELOPMENT = True`
in your `cms/settings/local.py` settings file.
