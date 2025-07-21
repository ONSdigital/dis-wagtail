/**
 * This adapter expects that the StructBlock is defined in Wagtail with a help
 * text and the following field:
 *
 * frozen = blocks.BooleanBlock(required=False, default=False)
 */

// eslint-disable-next-line @typescript-eslint/no-unused-vars
class ReadonlyStructBlockDefinition extends window.wagtailStreamField.blocks.StructBlockDefinition {
  frozenHelpText = '';

  hiddenFields = [];

  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);

    const parent = `[data-streamfield-child]:has([id^="${prefix}"])`;

    if (initialState.frozen) {
      const helpText = document.querySelector(`${parent} .help`);
      helpText.innerHTML = this.frozenHelpText;

      const getActionButton = (action) =>
        document.querySelector(`${parent} [data-streamfield-action="${action}"]`);

      const deleteButton = getActionButton('DELETE');
      deleteButton.style.display = 'none';
      const duplicateButton = getActionButton('DUPLICATE');
      duplicateButton.style.display = 'none';
    }

    const getFieldContainer = (field) =>
      document.querySelector(`${parent} [data-contentpath="${field}"]:has(#${prefix}-${field})`);

    const frozenCheckbox = getFieldContainer('frozen');
    frozenCheckbox.style.display = 'none';

    this.hiddenFields.forEach((field) => {
      const fieldContainer = getFieldContainer(field);
      fieldContainer.style.display = 'none';
    });

    return block;
  }
}
