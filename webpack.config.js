/* eslint-disable @typescript-eslint/no-var-requires */
const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const sass = require('sass');
const ESLintPlugin = require('eslint-webpack-plugin');
const StylelintPlugin = require('stylelint-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

const projectRoot = 'cms';

const options = {
  entry: {
    main: `./${projectRoot}/static_src/javascript/main.js`,
    auth: `./${projectRoot}/static_src/javascript/auth.js`,
  },
  resolve: {
    extensions: ['.ts', '.js'],
  },
  output: {
    path: path.resolve(`./${projectRoot}/static_compiled/`),
    // based on entry name, e.g. main.js
    filename: 'js/[name].js', // based on entry name, e.g. main.js
  },
  plugins: [
    new CopyPlugin({
      patterns: [
        {
          // Copy images to be referenced directly by Django to the "images" subfolder in static files.
          // Ignore CSS background images as these are handled separately below
          from: 'images',
          context: path.resolve(`./${projectRoot}/static_src/`),
          to: path.resolve(`./${projectRoot}/static_compiled/images`),
          globOptions: {
            ignore: ['cssBackgrounds/*'],
          },
        },
      ],
    }),
    new MiniCssExtractPlugin({
      filename: 'css/[name].css',
    }),
    new ESLintPlugin({
      failOnError: false,
      lintDirtyModulesOnly: true,
      emitWarning: true,
    }),
    new StylelintPlugin({
      failOnError: false,
      lintDirtyModulesOnly: true,
      emitWarning: true,
      extensions: ['scss'],
    }),
    //  Automatically remove all unused webpack assets on rebuild
    new CleanWebpackPlugin(),
  ],
  module: {
    rules: [
      {
        test: /\.(js|ts)$/,
        exclude: /node_modules/,
        use: {
          loader: 'ts-loader',
          options: { compilerOptions: { noEmit: false } },
        },
      },
      {
        test: /\.(scss|css)$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
            options: {
              esModule: false,
            },
          },
          {
            loader: 'css-loader',
            options: {
              sourceMap: true,
            },
          },
          {
            loader: 'postcss-loader',
            options: {
              sourceMap: true,
              postcssOptions: {
                plugins: [
                  'autoprefixer',
                  'postcss-custom-properties',
                  ['cssnano', { preset: 'default' }],
                ],
              },
            },
          },
          {
            loader: 'sass-loader',
            options: {
              sourceMap: true,
              implementation: sass,
              sassOptions: {
                outputStyle: 'compressed',
                includePaths: [path.resolve(`${projectRoot}/static_src/sass`)],
              },
            },
          },
        ],
      },
      {
        // Copies font files referenced by CSS/JS to the fonts
        // directory.
        // Only files located in the static_src/fonts directory can be
        // referenced in CSS/JS. Trying to reference a font outside of
        // this directory will result in a build error. Make sure to
        // store all fonts in this directory.
        test: /\.(woff|woff2)$/,
        include: path.resolve(`./${projectRoot}/static_src/fonts/`),
        type: 'asset/resource',
        generator: {
          filename: 'fonts/[name][ext]',
        },
      },
      {
        // Handles CSS background images in the cssBackgrounds folder
        // Files smaller than 1024 bytes are automatically encoded in
        // the CSS - see `_test-background-images.scss`. Otherwise, the
        // image is copied to the images/cssBackgrounds directory.
        test: /\.(svg|jpg|png)$/,
        include: path.resolve(`./${projectRoot}/static_src/images/cssBackgrounds/`),
        type: 'asset',
        parser: {
          dataUrlCondition: {
            maxSize: 1024,
          },
        },
        generator: {
          filename: 'images/cssBackgrounds/[name][ext]',
        },
      },
    ],
  },
  // externals are loaded via base.html and not included in the webpack bundle.
  externals: {
    // gettext: 'gettext',
  },
};

/*
  If a project requires internationalisation, then include `gettext` in base.html
    via the Django JSi18n helper, and uncomment it from the 'externals' object above.
*/

const webpackConfig = (environment, argv) => {
  const isProduction = argv.mode === 'production';

  options.mode = isProduction ? 'production' : 'development';

  if (!isProduction) {
    // https://webpack.js.org/configuration/stats/
    const stats = {
      // Tells stats whether to add the build date and the build time information.
      builtAt: false,
      // Add chunk information (setting this to `false` allows for a less verbose output)
      chunks: false,
      // Add the hash of the compilation
      hash: false,
      // `webpack --colors` equivalent
      colors: true,
      // Add information about the reasons why modules are included
      reasons: false,
      // Add webpack version information
      version: false,
      // Add built modules information
      modules: false,
      // Show performance hint when file size exceeds `performance.maxAssetSize`
      performance: false,
      // Add children information
      children: false,
      // Add asset Information.
      assets: false,
    };

    options.stats = stats;

    // Create JS source maps in the dev mode
    // See https://webpack.js.org/configuration/devtool/ for more options
    options.devtool = 'inline-source-map';

    // See https://webpack.js.org/configuration/dev-server/.
    options.devServer = {
      // Enable gzip compression for everything served.
      compress: true,
      static: false,
      host: '0.0.0.0',
      // When set to 'auto' this option always allows localhost, host, and client.webSocketURL.hostname
      allowedHosts: 'auto',
      port: 3000,
      proxy: [
        {
          context: () => true,
          target: `http://localhost:${process.env.WEB_PORT || 8000}`,
        },
      ],
      client: {
        // Shows a full-screen overlay in the browser when there are compiler errors.
        overlay: {
          warnings: false,
          errors: true,
        },
        logging: 'error',
      },
      devMiddleware: {
        index: true,
        publicPath: '/static/',
        writeToDisk: true,
        stats,
      },
    };
  }

  return options;
};

module.exports = webpackConfig;
