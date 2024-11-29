// eslint-disable-next-line
class ImageChooserModal extends window.ImageChooserModal {
  getURLParams(opts) {
    const urlParams = super.getURLParams(opts);
    // eslint-disable-next-line
    urlParams.from_url = window.location.pathname;
    return urlParams;
  }
}

// eslint-disable-next-line
window.ImageChooserModal = ImageChooserModal;
