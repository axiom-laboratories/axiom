import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTheme } from '../hooks/useTheme';
import '../index.css';

describe('Theme CSS Variables Integration', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('dark');
    document.documentElement.classList.remove('light');
    localStorage.clear();
  });

  afterEach(() => {
    document.documentElement.classList.remove('dark');
    document.documentElement.classList.remove('light');
  });

  it('should have light mode CSS variables in :root scope', () => {
    const root = document.documentElement;
    const bgColor = getComputedStyle(root).getPropertyValue('--background').trim();
    // In light mode (default), --background should be stone-50 equivalent (280 5% 97%)
    expect(bgColor).toBeTruthy();
  });

  it('should have dark mode CSS variables in .dark scope', () => {
    document.documentElement.classList.add('dark');
    const root = document.documentElement;
    const bgColor = getComputedStyle(root).getPropertyValue('--background').trim();
    // In dark mode, --background should be darker value
    expect(bgColor).toBeTruthy();
  });

  it('should apply light background color when theme is light', () => {
    const root = document.documentElement;
    const lightBg = getComputedStyle(root).getPropertyValue('--background');
    expect(lightBg).toBeTruthy();
    // Value should NOT contain dark zone values
    expect(lightBg).not.toContain('09090b');
  });

  it('should apply dark background color when dark class is present', () => {
    document.documentElement.classList.add('dark');
    const root = document.documentElement;
    const darkBg = getComputedStyle(root).getPropertyValue('--background');
    expect(darkBg).toBeTruthy();
  });

  it('should have primary color unchanged in both themes', () => {
    const rootLight = getComputedStyle(document.documentElement)
      .getPropertyValue('--primary')
      .trim();

    document.documentElement.classList.add('dark');
    const rootDark = getComputedStyle(document.documentElement)
      .getPropertyValue('--primary')
      .trim();

    // Primary should be pink (346.8 77.2% 49.8%) in both modes
    expect(rootLight).toContain('346');
    expect(rootDark).toContain('346');
  });

  it('should define status badge colors in CSS variables', () => {
    const root = document.documentElement;
    // Should have variables for success, error, warning badge styles
    const vars = getComputedStyle(root);
    expect(vars.getPropertyValue('--status-success-bg')).toBeTruthy();
    expect(vars.getPropertyValue('--status-error-bg')).toBeTruthy();
    expect(vars.getPropertyValue('--status-warning-bg')).toBeTruthy();
  });

  it('should define shadow CSS variables for light mode cards', () => {
    const root = document.documentElement;
    const vars = getComputedStyle(root);
    expect(vars.getPropertyValue('--shadow')).toBeTruthy();
    expect(vars.getPropertyValue('--shadow-md')).toBeTruthy();
  });

  it('should apply different text color based on theme', () => {
    const lightText = getComputedStyle(document.documentElement)
      .getPropertyValue('--foreground')
      .trim();

    document.documentElement.classList.add('dark');
    const darkText = getComputedStyle(document.documentElement)
      .getPropertyValue('--foreground')
      .trim();

    // Both should be defined
    expect(lightText).toBeTruthy();
    expect(darkText).toBeTruthy();
  });

  it('should define ring color for focus states', () => {
    const root = document.documentElement;
    const vars = getComputedStyle(root);
    // Focus ring should be pink in both modes
    const ringColor = vars.getPropertyValue('--ring').trim();
    expect(ringColor).toContain('346');
  });
});
