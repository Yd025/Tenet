/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'tenet-bg': '#0B0B0C',
        'tenet-teal': '#2DD4BF',
        'tenet-purple': '#7c3aed',
        'tenet-surface': '#111114',
        'tenet-border': '#1e1e24',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}

