/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          green: '#10B981',    // Emerald/Energy
          blue: '#3B82F6',     // Tech/Info
          red: '#EF4444',      // Critical/Alert
          amber: '#F59E0B',    // Warning
          cyber: '#06B6D4',    // Cyan cyber attack
          dark: '#030712',     // Deep Space black
          panel: '#0B0F19',    // Tesla/Nasa panel grey-blue
          card: 'rgba(17, 24, 39, 0.65)',
        }
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-green': '0 0 15px rgba(16, 185, 129, 0.25)',
        'glow-blue': '0 0 15px rgba(59, 130, 246, 0.25)',
        'glow-red': '0 0 15px rgba(239, 68, 68, 0.3)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
      },
      backdropFilter: {
        'glass': 'blur(12px)',
      }
    },
  },
  plugins: [],
}
