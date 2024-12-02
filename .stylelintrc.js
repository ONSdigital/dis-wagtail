module.exports = {
  // See https://github.com/wagtail/stylelint-config-wagtail for rules.
  extends: '@wagtail/stylelint-config-wagtail',
  // overrides to the wagtail config
  rules: {
    // Allow union class names in selectors e.g. &__header
    'scss/selector-no-union-class-name': null,
    // Override some wagtail specific rules relating to design tokens
    'scale-unlimited/declaration-strict-value': [
      ['color', 'fill', 'stroke', '/-color/'],
      {
        // The following are as per the wagtail config but need to be reset here
        ignoreValues: [
          'currentColor',
          'inherit',
          'initial',
          'none',
          'unset',
          'transparent',
          'Canvas',
          'CanvasText',
          'LinkText',
          'VisitedText',
          'ActiveText',
          'ButtonFace',
          'ButtonText',
          'ButtonBorder',
          'Field',
          'FieldText',
          'Highlight',
          'HighlightText',
          'SelectedItem',
          'SelectedItemText',
          'Mark',
          'MarkText',
          'GrayText',
          'AccentColor',
          'AccentColorText',
        ],
      },
    ],
    // Ensure that @include statements are at the top of the declaration block but not nested ones such as the media-query include
    'order/order': [{ name: 'include', type: 'at-rule', hasBlock: false }, 'declarations'],
    // Allow positioning with physical properties as right to left languages are not supported
    'property-disallowed-list': [
      // The following rules are as per the wagtail config
      '/forced-color-adjust/',
      'text-transform',
    ],
    // Allow physical values for clear, float and text-align, as right to left languages are not supported
    'declaration-property-value-allowed-list': {},
  },
};
