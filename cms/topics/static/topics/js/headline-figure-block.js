class HeadlineFigureBlock extends window.wagtailStreamField.blocks.StructBlockDefinition {
  constructor(name, childBlockDefs, meta) {
    super(name, childBlockDefs, meta);

    // preserve the original setState
    const { prototype } = this.childBlockDefs[0].widget.widgetClass;
    prototype.originalSetState = prototype.setState;

    // patch setState to add additional data attributes
    /* eslint-disable func-names */
    prototype.setState = function(newState) {
      if (newState && newState.figure_id) {
        this.input.setAttribute("data-figure-id", newState.figure_id);
        this.input.setAttribute("data-figure-title", newState.figure_title);
      } else {
        this.input.setAttribute("data-figure-id", "");
        this.input.setAttribute("data-figure-title", "");
      }

      this.originalSetState(newState);
    }
  }

  render(placeholder, prefix, initialState, initialError) {
    // initialize our StructBlock
    const block = super.render(placeholder, prefix, initialState, initialError);
    const {figure, series} = initialState;

    const figureTitle = document.createElement("DIV");
    block.container[0].appendChild(figureTitle);

    const associatedFigure = series?.figures.find((fig) => fig.figure_id === figure);

    // listen to changes to the series input and update the figure block value
    const seriesInput = document.getElementById(prefix + "-series");
    const figureInput = document.getElementById(prefix + "-figure");

    const renderTitleLabelInElement = (title) => {
      const label = document.createElement("B");
      label.innerText = "Figure:";
      const titleSpan = document.createElement("SPAN");
      titleSpan.innerText = title;
      figureTitle.replaceChildren(label, " ", titleSpan)
    }

    if (associatedFigure) {
      renderTitleLabelInElement(associatedFigure.title);
    }

    const container = document.querySelector(`[data-contentpath="figure"]:has(#${prefix}-figure)`);
    seriesInput.addEventListener("change", () => {
      figureInput.value = seriesInput.getAttribute("data-figure-id");
      renderTitleLabelInElement(seriesInput.getAttribute("data-figure-title"));
    });

    figureInput.type = "hidden";
    container.style.display = "none";

    return block;
  }
}


window.telepath.register("cms.topics.widgets.TopicHeadlineFigureBlock", HeadlineFigureBlock);
