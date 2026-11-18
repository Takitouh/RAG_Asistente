/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        uts: {
          green: {
            50: '#f0fdf4',
            100: '#dcfce7',
            500: '#16a34a',
            600: '#15803d',
            700: '#166534',
            800: '#14532d',
            900: '#0f3d20',
          },
          gold: {
            400: '#facc15',
            500: '#eab308',
            600: '#ca8a04',
          }
        }
      }
    },
  },
  plugins: [],
}
