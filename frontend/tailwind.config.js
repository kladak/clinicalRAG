export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#0A1628',
        teal: '#0AAFA0',
        cream: '#F7F8FA',
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'monospace'],
        serif: ['"Source Serif 4"', 'serif'],
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
