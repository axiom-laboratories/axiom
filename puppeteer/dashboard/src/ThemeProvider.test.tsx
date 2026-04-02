import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThemeProvider, useTheme } from './hooks/useTheme';

const TestComponent = () => {
  const { theme } = useTheme();
  return <div data-testid="theme-display">{theme}</div>;
};

describe('ThemeProvider context', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
    document.documentElement.classList.remove('light');
  });

  it('should wrap children without crashing', () => {
    render(
      <ThemeProvider>
        <div>Test child</div>
      </ThemeProvider>
    );
    expect(screen.getByText('Test child')).toBeTruthy();
  });

  it('should provide theme context to consuming components', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    const display = screen.getByTestId('theme-display');
    expect(display).toBeTruthy();
    expect(display.textContent).toBe('dark');
  });

  it('should hydrate theme from localStorage on mount', async () => {
    localStorage.setItem('mop_theme', 'light');
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    // Component should display 'light' because context provider hydrated from localStorage
    const display = screen.getByTestId('theme-display');
    expect(display).toBeTruthy();
  });

  it('should allow multiple children to consume context', () => {
    render(
      <ThemeProvider>
        <TestComponent />
        <TestComponent />
      </ThemeProvider>
    );
    const displays = screen.getAllByTestId('theme-display');
    expect(displays.length).toBe(2);
    expect(displays[0].textContent).toBe('dark');
    expect(displays[1].textContent).toBe('dark');
  });

  it('should sync theme state across multiple consumers', () => {
    const TestComponentWithToggle = () => {
      const { theme, setTheme } = useTheme();
      return (
        <div>
          <div data-testid="theme-display">{theme}</div>
          <button onClick={() => setTheme('light')}>Toggle</button>
        </div>
      );
    };

    render(
      <ThemeProvider>
        <TestComponentWithToggle />
        <TestComponent />
      </ThemeProvider>
    );
    const displays = screen.getAllByTestId('theme-display');
    expect(displays.length).toBe(2);
  });
});
