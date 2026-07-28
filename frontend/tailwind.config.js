/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          green:  "#A8FF6F",
          teal:   "#1D9E75",
          coral:  "#E24B4A",
          amber:  "#FAC775",
          purple: "#7850DC",
          dark:   "#12122A",
          card:   "#1E1E3F",
        },
        ink: {
          DEFAULT: '#0E2A2E',
          light: '#16403F',
          deep: '#081A1C',
        },
        paper: '#FBF7EE',
        coral: {
          DEFAULT: '#F0604A',
          dark: '#D14A36',
          light: '#FF8A73',
        },
        gold: {
          DEFAULT: '#F4B942',
          light: '#FCD87E',
        },
        mint: {
          DEFAULT: '#2FB8A6',
          dark: '#1E8C7D',
          light: '#8FE0D4',
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Nunito", "system-ui", "sans-serif"],
      },
      borderRadius: {
        blob: '42% 58% 63% 37% / 41% 45% 55% 59%',
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "float": "float 3s ease-in-out infinite",
        "spin-slow": "spin 8s linear infinite",
        "vm-float": "float 5s ease-in-out infinite",
      },
      keyframes: {
        float: {
          "0%,100%": { transform: "translateY(0px)" },
          "50%":     { transform: "translateY(-10px)" },
        },
        morph: {
          '0%, 100%': { opacity: 1 },
          '33%': { opacity: 0 },
        },
        drift: {
          '0%': { transform: 'translateX(0) rotate(0deg)' },
          '100%': { transform: 'translateX(-50%) rotate(360deg)' },
        },
      },
    },
  },
  plugins: [],
}
