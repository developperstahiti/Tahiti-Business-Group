/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans:  ['Arial', 'Helvetica', 'sans-serif'],
        serif: ['Arial', 'Helvetica', 'sans-serif'],
      },
      colors: {
        primary: '#1a6cf1',
        accent: '#059669',
      },
    },
  },
  plugins: [],
}
