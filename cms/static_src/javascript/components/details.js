class detailsToggle {
  static selector() {
    return 'details';
  }

  constructor(node) {
    // get all <details> elements
    const allDetails = document.querySelectorAll('details');

    // collapse all <details> by default
    allDetails.forEach((detail) => {
        detail.removeAttribute('open');
    });
  }
}

export default detailsToggle;