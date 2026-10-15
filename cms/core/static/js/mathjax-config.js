// Adjusts the MathJax config set by wagtail-polymath. It must load after polymath's
// config script and before the deferred MathJax library.
window.MathJax = window.MathJax || {};

// MathJax 4 loads its fonts from jsdelivr by default. Use the copy vendored next to
// MathJax on the ONS CDN instead.
window.MathJax.loader = {
  ...window.MathJax.loader,
  paths: { ...window.MathJax.loader?.paths, fonts: '[mathjax]/fonts' },
};

// MathJax 4 generates speech and braille in a web worker created from a blob: URL,
// which our CSP blocks. Use assistive MathML for screen readers instead, as MathJax 2 did.
window.MathJax.options = {
  ...window.MathJax.options,
  menuOptions: { settings: { speech: false, braille: false, assistiveMml: true } },
};
