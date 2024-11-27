// .stylelintrc.js
function autoFixFunc(node, validation, root, config) {
  const { value, prop } = node

  if (prop === 'color') {
    switch (value) {
      case '#fff':
        // auto-fix by returned value
        return '$color-white'

      case 'red':
        // auto-fix by PostCSS AST tranformation
        node.value = '$color-red'

      default:
        // optional, you can throw your own error message if the value is not stated or handled, ex: color: blue
        throw `Property ${prop} with value ${value} can't be autofixed!`
        // or an Error object
        throw new Error(`Property ${prop} with value ${value} can't be autofixed!`)
        // or a falsy value to use the default error message
        throw null;
    }
  }
}

module.exports = {
// "See https://github.com/wagtail/stylelint-config-wagtail for rules." //,
     "extends": ["@wagtail/stylelint-config-wagtail", "stylelint-config-standard"],
     "rules": {
     "no-invalid-double-slash-comments": null,
     "scale-unlimited/declaration-strict-value": [
      ["/color$/"], {
      autoFixFunc: autoFixFunc,
      disableFix: true,
    }],
  },
}

