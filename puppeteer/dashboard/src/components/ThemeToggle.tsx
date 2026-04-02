import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { cn } from '@/lib/utils';

export function ThemeToggle() {
  const { theme, setTheme, mounted } = useTheme();

  if (!mounted) return null; // Prevent hydration mismatch

  const isLight = theme === 'light';

  const handleToggle = () => {
    setTheme(isLight ? 'dark' : 'light');
  };

  return (
    <button
      onClick={handleToggle}
      className={cn(
        'flex items-center gap-1 rounded-full p-1 transition-colors duration-200',
        'bg-muted hover:bg-muted/80'
      )}
      aria-label={`Switch to ${isLight ? 'dark' : 'light'} mode`}
    >
      {/* Sun icon with rotation transform */}
      <Sun
        size={16}
        className={cn(
          'transition-transform duration-200',
          isLight && 'rotate-180'
        )}
      />
      {/* Slider dot */}
      <div
        className={cn(
          'h-5 w-5 rounded-full transition-transform duration-200',
          'bg-primary',
          isLight ? 'translate-x-4' : 'translate-x-0'
        )}
      />
      {/* Moon icon with rotation transform */}
      <Moon
        size={16}
        className={cn(
          'transition-transform duration-200',
          isLight && 'rotate-180'
        )}
      />
    </button>
  );
}
