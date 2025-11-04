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

Disabling page privacy is not currently easily supported by Wagtail, see this issue: https://github.com/wagtail/wagtail/issues/11640

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

## Statistical Article Page Privacy Issue

We have also discovered a bug in the current handling of privacy settings on Statistical Article pages. Because the statistical article page can be served by
editions page handler, the hooks which check for page privacy do not correctly detect and block acccess when a statistical article page is private. This means
that if a statistical article page is set to private, the page is still visible publicly despite having privacy settings applied. If we were to support page
privacy features, this would need to be fixed.
