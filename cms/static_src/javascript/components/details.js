/* eslint-disable @typescript-eslint/no-extraneous-class */
class detailsToggle {
  static selector() {
    return 'details';
  }

  constructor(node) {
    node.removeAttribute('open');
  }
}

export default detailsToggle;
