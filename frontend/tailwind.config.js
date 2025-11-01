/* eslint-env node */
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {

        // bg-gradient-to-r from-indigo-500 to-cyan-500
        // bg-gradient-to-r from-cyan-500 to-teal-400
        // indigo-500: '#6366F1',
        // cyan-500: '#06B6D4',
        // teal-400: '#14B8A6',

        // 🎯 Primary (Brand)
        'custom-blue': '#2563EB',
        'custom-blue-hover': '#1D4ED8',
        'custom-blue-deep': '#1E40AF',
        'custom-blue-bg': '#EFF6FF',

        // Custom Green Colors
        'custom-green': '#059669',
        'custom-green-hover': '#047857',
        'custom-green-deep': '#0B815A',

        // ⚫ Grayscale
        'custom-text': '#1F2937',
        'custom-text-subtle': '#6B7280',
        'custom-border': '#E5E7EB',
        'custom-input-bg': '#F9FAFC',

        // 🟢 Semantic Colors
        'custom-disabled': '#9CA3AF',
        'custom-success': '#10B981',
        'custom-warning': '#F59E0B',
        'custom-error': '#EF4444',
        'custom-info': '#0EA5E9',

        // 🪄 Secondary Accents (New)
        'custom-accent-teal': '#0D9488',
        'custom-accent-indigo': '#6366F1',
        'custom-bg-soft': '#F8FAFC',

        // 🟣 ClinicalTrials.gov Label
        'label-ctgov-bg': '#FFF4E6',
        'label-ctgov-text': '#D97706',

        // 🟢 PubMed Label
        'label-pubmed-bg': '#ECFDF5',
        'label-pubmed-text': '#059669',

        // 🟪 Merged Label
        'label-merged-bg': '#F3E8FF',
        'label-merged-text': '#9333EA',

        // Additional Palette
        'custom-accent-yellow': '#FACC15',
        'custom-accent-cyan': '#06B6D4',
        'custom-accent-pink': '#EC4899',
        'custom-accent-purple': '#8B5CF6',
        'custom-accent-gray': '#9CA3AF',
        'custom-bg-light-gray': '#F3F4F6',
      },
      keyframes: {
        placeholderCycle: {
          '0%': { opacity: '1', transform: 'translateY(0)' },
          '10%': { opacity: '1', transform: 'translateY(-100%)' },
          '20%': { opacity: '1', transform: 'translateY(-200%)' },
          '30%': { opacity: '1', transform: 'translateY(-300%)' },
          '40%': { opacity: '1', transform: 'translateY(-400%)' },
          '100%': { opacity: '1', transform: 'translateY(-400%)' },
        },
      },
      animation: {
        'placeholder-cycle': 'placeholderCycle 10s infinite ease-in-out',
      },
    },
  },
  plugins: [
    require('tailwind-scrollbar'),
    // require('@tailwindcss/forms'),
    // require('@tailwindcss/container-queries'),
  ],
};
