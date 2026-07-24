# Page Privacy in Wagtail

Wagtail has out of the box page privacy settings, which allow you to restrict access to published pages by password or login/group access rules,
see [Wagtail Docs: Privacy](https://docs.wagtail.org/en/stable/advanced_topics/privacy.html).

However, the way these settings are applied at a page level makes them unsuitable for our use.

This is because the privacy setting for a page is entirely separate to the page revision history, and applies without a save or publish action on the page. If
you edit a page in draft and change its privacy settings, that change is applied as soon as you click save _on the privacy settings change_, without requiring a
draft save or publish of the page itself. We require changes to a page to go through an approval workflow, which this effectively bypasses, allowing a single
user to immediately restrict access to a page with no draft approval process. This is especially problematic because page privacy settings are inherited by all
descendants of a page, so, for example, making a topic page private would instantly render all it's descendants articles and methodology pages inaccessible
too.

Disabling page privacy is not currently easily supported by Wagtail, see this issue: <https://github.com/wagtail/wagtail/issues/11640>

This means it will require custom code to fully disable page privacy settings in the CMS, which is under investigation.

## Code Practice

Developers should still ensure that queries are filtered with `.public()`, or pages are checked for privacy settings with
`page.get_view_restrictions().exists()` where the page(s) are expected to be publicly visible for forward compatibility, in case we ever do use privacy settings
in the future.

## Search Integration

Page privacy settings also have implications for our integration with public search indexing. We must only index pages which are publicly accessible, so private
pages need to be excluded from being sent to the search index. However, because privacy settings are independant of the page revision history and publishing,
privacy settings can be changed without triggering the signals we use to update search. Also we cannot tell from a page's revision history whether it was
previously private or not, to handle the case of a live page being made private or public, which would require a search index update for all descendants of that
page.

As we intend to disable page privacy settings entirely, we are leaving search integration with only simple checks for if a page currently has privacy settings,
as a belt and braces measure, but if we were to support privacy settings in future this would need to be revisited to properly support the cases of changing
privacy settings for a page and it's descendants.

## Feature flags

Page privacy feature needs more analysis in the future, as what we have implemented is more to fix the current completely broken functionality. Hence the page privacy controls are disabled now along with setting page privacy itself.

Privacy behaviour is controlled by two settings (both default to `false` and are set via environment variables):

- `CMS_PAGE_PRIVACY_CONTROLS_ENABLED` - allows editors with publish permissions to set page view restrictions
  (`can_set_view_restrictions` in `cms/core/permission_testers.py`), and registers the `/auth/frontend-login` route
  (`frontend_login_redirect`), which sends users of login/group-restricted pages to Florence SSO when Cognito is
  enabled, or to Wagtail's built-in `/_util/login/` view otherwise. `WAGTAIL_FRONTEND_LOGIN_URL` is only defined when
  this flag (and Cognito) is on; when undefined, Wagtail falls back to its built-in login view, so pre-existing view
  restrictions still resolve to a working (if Cognito-less) login rather than a 404.
- `CMS_COLLECTION_PRIVACY_CONTROLS_ENABLED` - registers the `/documents/authenticate_with_password/<restriction_id>`
  route, the password form target for Wagtail `CollectionViewRestriction`s on documents. Only superusers can create
  private collections; this flag can be extended in future as collection privacy support grows.

Note that the flags gate the admin controls and support routes, not enforcement: restrictions already in the database
are always enforced by Wagtail's serve hooks.

## Statistical Article Page Privacy

Statistical article pages (editions) are served through their parent series' routable sub-routes (`/<series>/`,
`/<series>/editions/<slug>/`, related data, version and download routes). Wagtail's own view-restriction hook only
checks the page matched by URL routing - the series - so restrictions on an edition were previously never evaluated
and private editions were publicly visible through the series routes.

This is fixed by `serve_page_with_view_restrictions` (`cms/core/utils.py`), which replays Wagtail's `on_serve_page`
hook chain against the edition actually being rendered before delegating to it. All `ArticleSeriesPage` sub-routes
serve editions through this helper, so password/login/group restrictions on an edition now behave exactly as they do
when the edition is routed directly, including returning the user to the originally requested sub-route URL after
authenticating. See `ArticleSeriesPagePrivacyTestCase` in `cms/articles/tests/test_series_models.py`.

### When is `serve_page_with_view_restrictions` needed?

Only when a routable page's sub-route hands off to a _different_ page object than the one Wagtail actually routed
to and restriction-checked. `ArticleSeriesPage`'s sub-routes call `edition.serve(...)` on a child
`StatisticalArticlePage`, so the child's own restrictions must be checked separately - Wagtail only checked the
series.

`InformationPage` and `MethodologyPage` do _not_ need it. Their only sub-routes come from `DataDownloadMixin`
(`download-table/<id>/`, `download-chart/<id>/`, `cms/data_downloads/mixins.py`), and both operate entirely on
`self` - they read a block out of the same page's `content` StreamField and stream a CSV, with no other page
involved. Wagtail already checked that same page's restrictions when it routed to it, so there's no gap. The same
applies to `StatisticalArticlePage`'s own `download_chart`/`download_table` and `previous_version` (which renders a
revision of itself, not another page).

The rule for any future routable page: if a `@path` method builds its response from `self`, the existing
`on_serve_page` check already covers it. Only wrap the call in `serve_page_with_view_restrictions` if the method
delegates to a _different_ page's `serve()` or view methods.

## Layered restrictions require multiple verification steps

Page view restrictions are inherited: a page must satisfy its own restriction _and_ every restriction on its
ancestors. If a parent page is restricted one way and a child page is restricted a different way, the visitor has to
clear both, one at a time, in a fixed order (ancestor first).

For example, if a topic page is set to "Private, accessible to any logged-in users" and one of its articles is
additionally set to "Password protected":

1. An anonymous visitor requesting the article is first redirected to log in (the topic page's restriction is
   checked first, since it's the ancestor).
2. Once logged in, they're returned to the article - but now they hit the article's own password restriction, and
   must enter the password too.
3. Only after both checks pass do they see the article.

This is expected Wagtail behaviour (each page's `get_view_restrictions()` includes its own and all ancestor
restrictions, and they're all enforced), not a bug - but it means editors should be deliberate about combining
different restriction types up and down a page tree, since visitors will need to pass through every layer in turn
rather than a single combined check.
