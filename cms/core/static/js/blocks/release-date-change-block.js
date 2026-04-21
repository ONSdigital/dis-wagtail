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

    const previousDateDiv = document.querySelector(
      `div[data-contentpath="previous_date"]:has(label[for="${prefix}-previous_date"])`,
    );
    const previousDateLabel = previousDateDiv.querySelector(`label[for="${prefix}-previous_date"]`);
    const previousDateInput = document.getElementById(`${prefix}-previous_date`);

    if (previousDateInput.value === '') {
      if (this.previous_date) {
        previousDateInput.value = this.previous_date;
      }
    }

    previousDateInput.readOnly = true; // disable text input
    previousDateInput.style.pointerEvents = 'none'; // disable date picker
    previousDateLabel.style.pointerEvents = 'none'; // disable date picker

    return block;
  }
}

window.telepath.register(
  'cms.release_calendar.blocks.ReleaseDateChangeBlock',
  ReleaseDateChangeBlockDefinition,
);
