class detailsToggle {
  static selector() {
    return 'details';
  }

  constructor(node) {
    node.removeAttribute('open');
  }
}

export default detailsToggle;
