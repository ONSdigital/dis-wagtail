class HeadlineFiguresItemBlock extends window.wagtailStreamField.blocks.StructBlockDefinition {
  constructor(name, childBlockDefs, meta) {
    super(name, childBlockDefs, meta);

    try {
      const usedFigures = document.getElementById('figures-used-by-ancestor');
      this.usedFigures = JSON.parse(usedFigures.innerText) || [];
    } catch (e) {
      this.usedFigures = [];
    }
  }

  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);
    const isUsed = this.usedFigures.includes(initialState.figure_id);

    const figureInput = document.getElementById(prefix + '-figure_id');
    const container = document.querySelector(
      `[data-contentpath="figure_id"]:has(#${prefix}-figure_id)`,
    );

    figureInput.type = 'hidden';
    container.style.display = 'none';

    if (figureInput.value) {
      const figureIdLabel = document.createElement('div');
      figureIdLabel.className = 'w-field';
      figureIdLabel.innerHTML = `<span class="w-field__label"><b>Figure ID:</b> ${figureInput.value}</span>`;
      container.parentElement.appendChild(figureIdLabel);
    }

    const shortPrefix = prefix.substr(0, prefix.length - 5);
    const parent = `[name="${shortPrefix}id"]+section`;
    const copySelector = "[data-streamfield-action='DUPLICATE']";
    const copyButton = document.querySelector(`${parent} ${copySelector}`);
    copyButton.remove();

    if (isUsed) {
      // This figure is used by a topic, we need to prevent deletion
      const helpText = document.querySelector(`${parent} .help`);
      const deleteSelector = "[data-streamfield-action='DELETE']";
      helpText.innerHTML =
        '<b>This figure is currently referenced by a published page and cannot be deleted.</b>';
      const deleteButton = document.querySelector(`${parent} ${deleteSelector}`);
      deleteButton.remove();
    }

    return block;
  }
}

window.telepath.register('cms.core.widgets.HeadlineFiguresItemBlock', HeadlineFiguresItemBlock);
