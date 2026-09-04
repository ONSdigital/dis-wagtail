/**
 * Hides the rendered_chart_image field on chart blocks. It is populated only by the chart
 * render pipeline and is never edited directly, so it should not be shown in the form.
 */
class ChartBlockDefinition extends window.wagtailStreamField.blocks.StructBlockDefinition {
  hiddenFields = ['rendered_chart_image'];

  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);

    const parent = `[data-streamfield-child]:has([id^="${prefix}"])`;

    this.hiddenFields.forEach((field) => {
      const fieldContainer = document.querySelector(
        `${parent} [data-contentpath="${field}"]:has(#${prefix}-${field})`,
      );
      if (fieldContainer) {
        fieldContainer.style.display = 'none';
      }
    });

    return block;
  }
}

window.telepath.register('cms.datavis.blocks.base.BaseChartBlock', ChartBlockDefinition);
