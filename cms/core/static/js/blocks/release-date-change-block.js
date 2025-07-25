/* global ReadonlyStructBlockDefinition */
class ReleaseDateChangeBlockDefinition extends ReadonlyStructBlockDefinition {
  frozenHelpText = '<b>This release date change is published and cannot be deleted.</b>';

  constructor(name, childBlockDefs, meta) {
    super(name, childBlockDefs, meta);

    try {
      const previousReleaseDateJson = document.getElementById('previous-release-date');
      this.previous_date = JSON.parse(previousReleaseDateJson.innerText);
    } catch (e) {
      this.previous_date = null;
    }
  }

  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);

    if (this.previous_date) {
      const previousDateInput = document.querySelector(
        `input[type="text"]#${prefix}-previous_date`,
      );
      if (previousDateInput.value === '') {
        previousDateInput.value = this.previous_date || '';
      }
      // previousDateInput.disabled = true;
      // previousDateInput.readOnly = true;
    }

    return block;
  }
}

window.telepath.register(
  'cms.release_calendar.blocks.ReleaseDateChangeBlock',
  ReleaseDateChangeBlockDefinition,
);
