class HeadlineFiguresItemBlock extends window.wagtailStreamField.blocks.StructBlockDefinition {
  constructor(name, childBlockDefs, meta) {
    super(name, childBlockDefs, meta);

    try {
      const usedFigures = document.getElementById("figures-used-by-ancestor");
      this.usedFigures = JSON.parse(usedFigures.innerText) || [];
    } catch (e) {
      this.usedFigures = [];
    }
  }

  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);
    const isUsed = this.usedFigures.includes(initialState.figure_id);

    const figureInput = document.getElementById(prefix + "-figure_id");
    const container = document.querySelector(`[data-contentpath="figure_id"]:has(#${prefix}-figure_id)`);

    figureInput.type = "hidden";
    container.style.display = "none";

    if (isUsed) {
      // This figure is used by a topic, we need to prevent deletion
      const shortPrefix = prefix.substr(0, prefix.length - 5);
      const parent = `[name="${shortPrefix}id"]+section`;
      const helpText = document.querySelector(`${parent} .help`);
      const deleteSelector = "[data-streamfield-action='DELETE']";
      helpText.innerHTML = "<b>This figure is currently referenced and cannot be deleted.</b>";
      const deleteButton = document.querySelector(`${parent} ${deleteSelector}`);
      deleteButton.style.display = "none";

      // The main delete button can delete all of the items, it needs to be hidden as well
      const mainDeleteButton = document.querySelector(`[name="headline_figures-0-id"]+section ${deleteSelector}]`);
      mainDeleteButton.style.display = "none";
    }

    return block;
  }
}


window.telepath.register("cms.core.widgets.HeadlineFiguresItemBlock", HeadlineFiguresItemBlock);
