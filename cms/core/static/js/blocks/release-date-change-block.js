class ReleaseDateChangeBlockDefinition extends window.wagtailStreamField.blocks
  .StructBlockDefinition {
  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);

    const parent = `[data-streamfield-child]:has([id^="${prefix}"])`;

    if (initialState.frozen) {
      const helpText = document.querySelector(`${parent} .help`);
      helpText.innerHTML = '<b>This date change log is published and cannot be deleted.</b>';

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

    const versionId = getFieldContainer('version_id');
    versionId.style.display = 'none';

    return block;
  }
}

window.telepath.register(
  'cms.release_calendar.blocks.ReleaseDateChangeBlock',
  ReleaseDateChangeBlockDefinition,
);
