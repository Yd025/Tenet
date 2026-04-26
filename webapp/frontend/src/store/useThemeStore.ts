import { create } from 'zustand';

interface ThemeStore {
  isDark: boolean;
  toggle: () => void;
}

export const useThemeStore = create<ThemeStore>((set, get) => ({
  isDark: true,
  toggle: () => {
    const next = !get().isDark;
    set({ isDark: next });
    document.body.classList.toggle('light', !next);
    document.body.classList.toggle('dark', next);
  },
}));

// Apply initial class
document.body.classList.add('dark');
