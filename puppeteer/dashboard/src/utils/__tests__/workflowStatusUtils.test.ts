import { describe, it, expect } from 'vitest';
import {
  getStatusVariant,
  getStatusColor,
  statusColorMap,
  statusVariantMap,
} from '../workflowStatusUtils';

describe('workflowStatusUtils', () => {
  describe('getStatusVariant()', () => {
    it('getStatusVariant(PENDING) returns "outline"', () => {
      expect(getStatusVariant('PENDING')).toBe('outline');
    });

    it('getStatusVariant(RUNNING) returns "default"', () => {
      expect(getStatusVariant('RUNNING')).toBe('default');
    });

    it('getStatusVariant(COMPLETED) returns "secondary"', () => {
      expect(getStatusVariant('COMPLETED')).toBe('secondary');
    });

    it('getStatusVariant(FAILED) returns "destructive"', () => {
      expect(getStatusVariant('FAILED')).toBe('destructive');
    });

    it('getStatusVariant(PARTIAL) returns "outline"', () => {
      expect(getStatusVariant('PARTIAL')).toBe('outline');
    });

    it('getStatusVariant(CANCELLED) returns "outline"', () => {
      expect(getStatusVariant('CANCELLED')).toBe('outline');
    });

    it('getStatusVariant(SKIPPED) returns "outline"', () => {
      expect(getStatusVariant('SKIPPED')).toBe('outline');
    });

    it('getStatusVariant(undefined) returns "outline"', () => {
      expect(getStatusVariant(undefined)).toBe('outline');
    });

    it('getStatusVariant(empty string) returns "outline"', () => {
      expect(getStatusVariant('')).toBe('outline');
    });

    it('case-insensitive: getStatusVariant("running") returns "default"', () => {
      expect(getStatusVariant('running')).toBe('default');
    });
  });

  describe('getStatusColor()', () => {
    it('getStatusColor(RUNNING) returns blue hex code', () => {
      expect(getStatusColor('RUNNING')).toBe('#3b82f6');
    });

    it('getStatusColor(COMPLETED) returns green hex code', () => {
      expect(getStatusColor('COMPLETED')).toBe('#10b981');
    });

    it('getStatusColor(FAILED) returns red hex code', () => {
      expect(getStatusColor('FAILED')).toBe('#ef4444');
    });

    it('getStatusColor(PENDING) returns grey hex code', () => {
      expect(getStatusColor('PENDING')).toBe('#888888');
    });

    it('getStatusColor(SKIPPED) returns grey hex code', () => {
      expect(getStatusColor('SKIPPED')).toBe('#888888');
    });

    it('getStatusColor(CANCELLED) returns grey hex code', () => {
      expect(getStatusColor('CANCELLED')).toBe('#888888');
    });

    it('getStatusColor(PARTIAL) returns amber hex code', () => {
      expect(getStatusColor('PARTIAL')).toBe('#f59e0b');
    });

    it('getStatusColor(undefined) returns fallback grey hex code', () => {
      expect(getStatusColor(undefined)).toBe('#888888');
    });

    it('case-insensitive: getStatusColor("completed") returns green', () => {
      expect(getStatusColor('completed')).toBe('#10b981');
    });
  });

  describe('statusColorMap constant', () => {
    it('statusColorMap contains all status keys', () => {
      expect(statusColorMap).toHaveProperty('RUNNING');
      expect(statusColorMap).toHaveProperty('COMPLETED');
      expect(statusColorMap).toHaveProperty('FAILED');
      expect(statusColorMap).toHaveProperty('PENDING');
      expect(statusColorMap).toHaveProperty('SKIPPED');
      expect(statusColorMap).toHaveProperty('CANCELLED');
      expect(statusColorMap).toHaveProperty('PARTIAL');
    });

    it('statusColorMap returns correct color values', () => {
      expect(statusColorMap['RUNNING']).toBe('#3b82f6');
      expect(statusColorMap['COMPLETED']).toBe('#10b981');
      expect(statusColorMap['FAILED']).toBe('#ef4444');
    });
  });

  describe('statusVariantMap constant', () => {
    it('statusVariantMap contains all status keys', () => {
      expect(statusVariantMap).toHaveProperty('RUNNING');
      expect(statusVariantMap).toHaveProperty('COMPLETED');
      expect(statusVariantMap).toHaveProperty('FAILED');
      expect(statusVariantMap).toHaveProperty('PENDING');
      expect(statusVariantMap).toHaveProperty('SKIPPED');
      expect(statusVariantMap).toHaveProperty('CANCELLED');
      expect(statusVariantMap).toHaveProperty('PARTIAL');
    });

    it('statusVariantMap returns correct variant values', () => {
      expect(statusVariantMap['RUNNING']).toBe('default');
      expect(statusVariantMap['COMPLETED']).toBe('secondary');
      expect(statusVariantMap['FAILED']).toBe('destructive');
      expect(statusVariantMap['PENDING']).toBe('outline');
    });
  });
});
