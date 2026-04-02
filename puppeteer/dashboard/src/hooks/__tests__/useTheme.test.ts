import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTheme } from '../useTheme';

describe('useTheme hook', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
    document.documentElement.classList.remove('light');
  });

  it('should default to dark theme when localStorage is empty', () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe('dark');
  });

  it('should read theme from localStorage.mop_theme on init', () => {
    localStorage.setItem('mop_theme', 'light');
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe('light');
  });

  it('should persist theme to localStorage on setTheme', () => {
    const { result } = renderHook(() => useTheme());
    act(() => {
      result.current.setTheme('light');
    });
    expect(localStorage.getItem('mop_theme')).toBe('light');
  });

  it('should add dark class to document.documentElement when theme is dark', () => {
    const { result } = renderHook(() => useTheme());
    act(() => {
      result.current.setTheme('dark');
    });
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('should remove dark class when theme is light', () => {
    document.documentElement.classList.add('dark');
    const { result } = renderHook(() => useTheme());
    act(() => {
      result.current.setTheme('light');
    });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('should handle multiple rapid setTheme calls correctly', () => {
    const { result } = renderHook(() => useTheme());
    act(() => {
      result.current.setTheme('light');
      result.current.setTheme('dark');
      result.current.setTheme('light');
    });
    expect(result.current.theme).toBe('light');
    expect(localStorage.getItem('mop_theme')).toBe('light');
  });

  it('should default to dark when window is undefined (SSR safety)', () => {
    const originalWindow = globalThis.window;
    try {
      // Simulate SSR environment
      Object.defineProperty(globalThis, 'window', {
        value: undefined,
        writable: true,
      });
      const { result } = renderHook(() => useTheme());
      expect(result.current.theme).toBe('dark');
    } finally {
      Object.defineProperty(globalThis, 'window', {
        value: originalWindow,
        writable: true,
      });
    }
  });
});
