/* eslint-disable class-methods-use-this */
/* eslint-disable max-classes-per-file */

class PreviousVersionBlock {
  constructor(blockDef, placeholder, prefix, initialState) {
    this.blockDef = blockDef;
    this.element = document.createElement('div');

    placeholder.replaceWith(this.element);

    this.renderContent(initialState);
  }

  renderContent(state) {
    if (state) {
      this.element.innerHTML = `
                <a class="button button-small button-secondary" target="_blank" href="../revisions/${state}/view/">Preview revision</a>
            `;
    } else {
      this.element.innerHTML = `
                <p>The previous version will be automatically chosen when this page is saved.</p>
            `;
    }
  }

  setState(state) {
    this.renderContent(state);
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  setError(_errorList) { }

  getState() {
    return null;
  }

  getValue() {
    return null;
  }

  focus() { }
}

class PreviousVersionBlockDefinition extends window.wagtailStreamField.blocks.FieldBlockDefinition {
  render(placeholder, prefix, initialState) {
    return new PreviousVersionBlock(this, placeholder, prefix, initialState);
  }
}

window.telepath.register("cms.core.blocks.panels.PreviousVersionBlock", PreviousVersionBlockDefinition);
