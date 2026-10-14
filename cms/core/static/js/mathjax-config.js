// Adjusts the MathJax config set by wagtail-polymath. It must load after polymath's
// config script and before the deferred MathJax library.
window.MathJax = window.MathJax || {};

// MathJax 4 loads its fonts from jsdelivr by default. Use the copy vendored next to
// MathJax on the ONS CDN instead.
window.MathJax.loader = {
  ...window.MathJax.loader,
  paths: { ...window.MathJax.loader?.paths, fonts: '[mathjax]/fonts' },
};
