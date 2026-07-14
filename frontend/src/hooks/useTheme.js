import { useThemeStore } from '../stores/useThemeStore';
import { useEffect } from 'react';

const updateDomTheme = (theme) => {
    const root = document.documentElement;
    
    // 立即更新，不使用 requestAnimationFrame
    if (theme === 'dark') {
        root.setAttribute('data-theme', 'dark');
    } else {
        root.removeAttribute('data-theme');
    }
};

export const useTheme = () => {
    const { theme, setTheme } = useThemeStore();

    useEffect(() => {
        updateDomTheme(theme);
    }, [theme]);

    const toggleTheme = () => {
        const newTheme = theme === 'light' ? 'dark' : 'light';

        // 直接切换，不使用动画
        // 这样可以获得最流畅的体验
        setTheme(newTheme);
        updateDomTheme(newTheme);
    };

    return { theme, toggleTheme };
};
