import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { cn } from '@/lib/utils';

export function ThemeToggle() {
  const { theme, setTheme, mounted } = useTheme();

  if (!mounted) return null;

  const isLight = theme === 'light';

  const handleToggle = () => {
    setTheme(isLight ? 'dark' : 'light');
  };

  return (
    <button
      onClick={handleToggle}
      className={cn(
        'relative flex items-center w-16 h-8 rounded-full p-1 transition-colors duration-300 ease-in-out',
        'bg-muted hover:bg-muted/80'
      )}
      aria-label={`Switch to ${isLight ? 'dark' : 'light'} mode`}
    >
      <Sun
        size={14}
        className={cn(
          'absolute left-1.5 top-1/2 -translate-y-1/2 transition-opacity duration-300',
          isLight ? 'opacity-100 text-amber-500' : 'opacity-40 text-muted-foreground'
        )}
      />
      <div
        className={cn(
          'h-6 w-6 rounded-full bg-primary shadow-md transition-transform duration-300 ease-in-out',
          isLight ? 'translate-x-8' : 'translate-x-0'
        )}
      />
      <Moon
        size={14}
        className={cn(
          'absolute right-1.5 top-1/2 -translate-y-1/2 transition-opacity duration-300',
          isLight ? 'opacity-40 text-muted-foreground' : 'opacity-100 text-blue-300'
        )}
      />
    </button>
  );
}
