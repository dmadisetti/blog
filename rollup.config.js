import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import babel from '@rollup/plugin-babel';
import terser from '@rollup/plugin-terser';
import replace from '@rollup/plugin-replace';

export default {
  input: 'src/index.jsx',
  output: {
    file: 'docs/javascripts/vim-navigation.js',
    format: 'iife',
    name: 'VimNavigation',
    sourcemap: true,
    globals: {
      'process': 'process'
    }
  },
  plugins: [
    replace({
      'process.env.NODE_ENV': JSON.stringify('production'),
      preventAssignment: true
    }),
    resolve({
      extensions: ['.js', '.jsx'],
      browser: true,
    }),
    babel({
      babelHelpers: 'bundled',
      presets: ['@babel/preset-react'],
      extensions: ['.js', '.jsx'],
      exclude: 'node_modules/**',
    }),
    commonjs(),
    terser({
      compress: {
        drop_console: false,
      },
    }),
  ],
};
