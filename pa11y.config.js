module.exports = {
  standard: 'WCAG2AA',
  runners: ['axe'],
  ignore: [
    // Ignored because there are too many errors reported.
    'color-contrast',
    // Ignored because this check mandates captions in a specific way which we don’t want to support.
    'video-captions'
  ]
}
