# Design System and Overrides

The site front-end code extends the [ONS Design system](https://service-manual.ons.gov.uk/design-system/).
We extend the [base template](https://service-manual.ons.gov.uk/design-system/foundations/base-page-template) and
make use of design system utility classes, colours and typography.

## Overrides

Until the new styles needed for the beta site are ready to be used in the design system, we are using some temporary overrides to HTML markup and styling.

### Markup overrides

The base page template (`cms/jinja2/templates/base_page.html`) has some important changes to the `pageContent` block in order to
add the full width section for the new header areas - including relocating the `<main>` tag so that the new header area is nested inside it.

### Styling overrides

In some cases we needed to extend or override design system styling. These changes can be found in `cms/static_src/sass/components/design_system_overrides`.

## New markup and styling

### Markup for new components

Note that new markup can be found in the page templates for the topic, bulletin and information pages.
These can be found in the `cms/jinja2/templates/pages` folder. Where new components are part of re-orderable streamfield blocks,
they can be found in the `cms/jinja2/templates/components/streamfield` folder.

### Styling for new components

Styling for new components can be found in `cms/static_src/sass/components/`.

## Incorporation of new components into the design system

The customisations described above are in the process of being incorporated into the design system,
so that they can be used without the need to duplicate and / or override code.
