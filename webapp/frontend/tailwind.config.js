/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'tenet-bg':      { DEFAULT: '#1a1a1e', light: '#f0f0f2' },
        'tenet-teal':    { DEFAULT: '#2DD4BF', light: '#0d9488' },
        'tenet-purple':  { DEFAULT: '#7c3aed', light: '#6d28d9' },
        'tenet-pink':    { DEFAULT: '#ec4899', light: '#db2777' },
        'tenet-surface': { DEFAULT: '#111114', light: '#ffffff' },
        'tenet-border':  { DEFAULT: '#1e1e24', light: '#d1d5db' },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
