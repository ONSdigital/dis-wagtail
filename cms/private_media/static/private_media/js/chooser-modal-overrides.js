class ImageChooserModal extends window.ImageChooserModal {
  // eslint-disable-next-line
  getURLParams(opts) {
    const urlParams = super.getURLParams(opts);
    urlParams.from_url = window.location.pathname;
    return urlParams;
  }
}

window.ImageChooserModal = ImageChooserModal;


class DocumentChooserModal extends window.DocumentChooserModal {
  getURLParams(opts) {
    const urlParams = super.getURLParams(opts);
    urlParams.from_url = window.location.pathname;
    return urlParams;
  }
}

window.DocumentChooserModal = DocumentChooserModal;
