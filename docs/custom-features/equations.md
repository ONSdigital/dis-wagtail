# Equations

The equation block (`cms/core/blocks/equation.py`) uses [wagtail-polymath](https://github.com/wagtail-nest/wagtail-polymath)
to render maths with [MathJax 4](https://docs.mathjax.org/en/latest/), in the Wagtail admin preview and on the front end.

Editors can enter TeX (`$$...$$` for display, `\(...\)` for inline) or AsciiMath (`` `...` ``).
On save, the equation is also rendered to SVG with matplotlib, which is shown when JavaScript is disabled.

## Where MathJax comes from

MathJax is served from the ONS CDN, not a third-party CDN, so our CSP only needs to allow `cdn.ons.gov.uk`.
The vendored files live in [cdn.ons.gov.uk-vendor](https://github.com/ONSdigital/cdn.ons.gov.uk-vendor) under
`vendor/mathjax/<version>/`, with the MathJax New Computer Modern font inside it at `fonts/mathjax-newcm-font/`.

`WAGTAIL_POLYMATH` in `cms/settings/base.py` sets the library URL and its Subresource Integrity hash.

## Our MathJax config

`cms/core/static/js/mathjax-config.js` adjusts the config that wagtail-polymath sets. It:

- loads fonts from the ONS CDN (`[mathjax]/fonts`) instead of jsdelivr, MathJax 4's default
- turns off MathJax's speech and braille and turns on assistive MathML for screen readers.
  MathJax 4 generates speech and braille in a `blob:` web worker, which our CSP blocks

It must run after polymath's config and before the deferred MathJax library. On the front end it is loaded
in `cms/jinja2/templates/partials/content_scripts.html`. In the admin it is added to the equation widget's media.

## Upgrading MathJax

1. Vendor the new MathJax version and its matching font package in `cdn.ons.gov.uk-vendor`, and wait for it to
   be published.
2. Update the URL and `sri` in `WAGTAIL_POLYMATH`. The hash must match the file served by the ONS CDN.
3. Check the front end and admin preview in the browser: equations render, fonts load from the ONS CDN, and
   there are no CSP errors in the console.
