class HeadlineFigureBlock extends window.wagtailStreamField.blocks.StructBlockDefinition {
  render(placeholder, prefix, initialState, initialError) {
    // preserve the original setState
    this.childBlockDefs[0].widget.widgetClass.prototype.originalSetState = this.childBlockDefs[0].widget.widgetClass.prototype.setState;

    // patch setState to add an additional data attribute
    /* eslint-disable func-names */
    this.childBlockDefs[0].widget.widgetClass.prototype.setState = function(newState) {
      if (newState && newState.figure_id) {
        this.input.setAttribute("data-figure-id", newState.figure_id);
      }
      else {
        this.input.setAttribute("data-figure-id", "");
      }

      this.originalSetState(newState);
    }

    // initialize our StructBlock
    const block = super.render(placeholder, prefix, initialState, initialError);

    // listen to changes to the series input and update the figure block value
    const seriesInput = document.getElementById(prefix + "-series");
    const figureInput = document.getElementById(prefix + '-figure');
    seriesInput.addEventListener("change", () => {
      figureInput.value = seriesInput.getAttribute("data-figure-id");
    });

    return block;
  }
}


window.telepath.register("cms.topics.widgets.TopicHeadlineFigureBlock", HeadlineFigureBlock);
