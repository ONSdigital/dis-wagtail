class TopicHeadlineFigureBlock extends window.wagtailStreamField.blocks.StructBlockDefinition {
  constructor(name, childBlockDefs, meta) {
    super(name, childBlockDefs, meta);

    // preserve the original setState
    const { prototype } = this.childBlockDefs[0].widget.widgetClass;
    prototype.originalSetState = prototype.setState;

    // patch setState to add additional data attributes
    /* eslint-disable func-names */
    prototype.setState = function (newState) {
      if (newState && newState.figure_id) {
        this.input.setAttribute('data-figure-id', newState.figure_id);
        this.input.setAttribute('data-figure-title', newState.figure_title);
      } else {
        this.input.setAttribute('data-figure-id', '');
        this.input.setAttribute('data-figure-title', '');
      }

      this.originalSetState(newState);
    };
  }

  render(placeholder, prefix, initialState, initialError) {
    // initialize our StructBlock
    const block = super.render(placeholder, prefix, initialState, initialError);
    const { figure_id: figureId, series } = initialState;

    const figureTitle = document.createElement('DIV');
    block.container[0].appendChild(figureTitle);

    const associatedFigure = series?.figures?.find((fig) => fig.figure_id === figureId);

    // listen to changes to the series input and update the figure block value
    const seriesInput = document.getElementById(prefix + '-series');
    const figureInput = document.getElementById(prefix + '-figure_id');

    const renderTitleLabelInElement = (title, id) => {
      const label = document.createElement('B');
      label.innerText = 'Figure:';
      const titleSpan = document.createElement('SPAN');
      const idValue = document.createElement('CODE');
      titleSpan.innerText = title;
      idValue.innerText = id;
      figureTitle.replaceChildren(label, ' ', titleSpan, ' ', idValue);
    };

    if (associatedFigure) {
      renderTitleLabelInElement(associatedFigure.title, figureId);
    }

    const container = document.querySelector(
      `[data-contentpath="figure_id"]:has(#${prefix}-figure_id)`,
    );
    seriesInput.addEventListener('change', () => {
      const newFigureId = seriesInput.getAttribute('data-figure-id');
      figureInput.value = newFigureId;
      renderTitleLabelInElement(seriesInput.getAttribute('data-figure-title'), newFigureId);
    });

    figureInput.type = 'hidden';
    container.style.display = 'none';

    return block;
  }
}

window.telepath.register('cms.topics.widgets.TopicHeadlineFigureBlock', TopicHeadlineFigureBlock);
