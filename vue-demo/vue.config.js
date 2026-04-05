const path = require('path');
const { defineConfig } = require('@vue/cli-service');

module.exports = defineConfig({
  transpileDependencies: true,
  publicPath: './',
  outputDir: path.resolve(__dirname, '../vue-home'),
  assetsDir: 'assets',
  filenameHashing: false,
  productionSourceMap: false,
});
