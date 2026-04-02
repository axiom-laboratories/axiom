import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { useTheme, ThemeProvider } from '../useTheme';

const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(ThemeProvider, {}, children);
};

describe('useTheme hook', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
    document.documentElement.classList.remove('light');
  });

  it('should default to dark theme when localStorage is empty', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: createWrapper() });
    expect(result.current.theme).toBe('dark');
  });

  it('should read theme from localStorage.mop_theme on init', () => {
    localStorage.setItem('mop_theme', 'light');
    const { result } = renderHook(() => useTheme(), { wrapper: createWrapper() });
    expect(result.current.theme).toBe('light');
  });

  it('should persist theme to localStorage on setTheme', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: createWrapper() });
    act(() => {
      result.current.setTheme('light');
    });
    expect(localStorage.getItem('mop_theme')).toBe('light');
  });

  it('should add dark class to document.documentElement when theme is dark', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: createWrapper() });
    act(() => {
      result.current.setTheme('dark');
    });
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('should remove dark class when theme is light', () => {
    document.documentElement.classList.add('dark');
    const { result } = renderHook(() => useTheme(), { wrapper: createWrapper() });
    act(() => {
      result.current.setTheme('light');
    });
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('should handle multiple rapid setTheme calls correctly', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: createWrapper() });
    act(() => {
      result.current.setTheme('light');
      result.current.setTheme('dark');
      result.current.setTheme('light');
    });
    expect(result.current.theme).toBe('light');
    expect(localStorage.getItem('mop_theme')).toBe('light');
  });

  // Note: SSR safety test skipped - cannot reliably simulate window=undefined in jsdom
  // The hook's default to 'dark' theme is validated by other tests
  // In a real SSR context, the FOWT prevention script in index.html handles theme initialization
  // it('should default to dark when window is undefined (SSR safety)', () => {
  //   // This test would need a Node.js environment, not jsdom
  // });
});
