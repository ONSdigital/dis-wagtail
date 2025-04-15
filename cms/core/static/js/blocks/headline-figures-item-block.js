class HeadlineFiguresItemBlock extends window.wagtailStreamField.blocks.StructBlockDefinition {
  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);

    const figureInput = document.getElementById(prefix + "-figure_id");
    const container = document.querySelector(`[data-contentpath="figure_id"]:has(#${prefix}-figure_id)`);

    figureInput.type = "hidden";
    container.style.display = "none";

    return block;
  }
}


window.telepath.register("cms.core.widgets.HeadlineFiguresItemBlock", HeadlineFiguresItemBlock);
