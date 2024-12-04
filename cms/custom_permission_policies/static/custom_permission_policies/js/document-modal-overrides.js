// eslint-disable-next-line
class DocumentChooserModal extends window.DocumentChooserModal {
  getURLParams(opts) {
    const urlParams = super.getURLParams(opts);
    // eslint-disable-next-line
    urlParams.from_url = window.location.pathname;
    return urlParams;
  }
}

// eslint-disable-next-line
window.DocumentChooserModal = DocumentChooserModal;
