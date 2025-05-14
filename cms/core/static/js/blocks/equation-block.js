class EquationBlockDefinition extends window.wagtailStreamField.blocks.StructBlockDefinition {
  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);

    block.container[0].querySelector('[data-contentpath="svg"]').remove();

    return block;
  }
}

window.telepath.register('cms.core.blocks.equation.EquationBlock', EquationBlockDefinition);
