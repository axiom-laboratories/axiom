import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import GuidedDispatchCard from '../../components/GuidedDispatchCard';

// Mock authenticatedFetch to prevent network calls
vi.mock('../../auth', () => ({
    authenticatedFetch: vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }),
}));

describe('GuidedDispatchCard', () => {

    // JOB-01: guided form stubs

    it('renders runtime selector, script textarea, node dropdown, target tag chip input, and capability chip input', () => {
        throw new Error('not implemented');
    });

    it('Dispatch button is disabled when no targeting field is provided', () => {
        throw new Error('not implemented');
    });

    it('Dispatch button is enabled when a target tag is added and both signature fields are non-empty', () => {
        throw new Error('not implemented');
    });

    it('calls POST /jobs with correctly structured payload on dispatch', () => {
        throw new Error('not implemented');
    });

    it('shows amber warning and clears signature fields when script content changes after signature is entered', () => {
        throw new Error('not implemented');
    });

    // JOB-02: JSON preview stubs

    it('JSON preview accordion is collapsed by default', () => {
        throw new Error('not implemented');
    });

    it('JSON preview shows generated payload that updates live as form fields change', () => {
        throw new Error('not implemented');
    });

    // JOB-03: advanced mode stubs

    it('ADV button shows confirmation dialog before switching to Advanced mode', () => {
        throw new Error('not implemented');
    });

    it('confirming Advanced mode pre-fills JSON editor with serialised guided form values', () => {
        throw new Error('not implemented');
    });

    it('Dispatch button is disabled in Advanced mode when JSON is invalid', () => {
        throw new Error('not implemented');
    });

    it('Reset button in Advanced mode shows confirmation dialog and returns to blank guided form', () => {
        throw new Error('not implemented');
    });

});
