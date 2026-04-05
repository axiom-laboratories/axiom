import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BuildConfirmationDialog from '../BuildConfirmationDialog';

const mockTemplate = {
  id: 'starter-1',
  friendly_name: 'Data Science Starter',
  description: 'Python data science packages',
  base_image: 'debian:12',
  blueprint: {
    packages: [
      { name: 'numpy', ecosystem: 'PYPI', version_constraint: '>=1.20' },
      { name: 'pandas', ecosystem: 'PYPI', version_constraint: '>=1.3' },
      { name: 'git', ecosystem: 'APT', version_constraint: '>=2.30' }
    ]
  }
};

describe('BuildConfirmationDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dialog with template name when open', () => {
    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={vi.fn()}
      />
    );

    expect(screen.getByText(/Ready to Build Data Science Starter\?/)).toBeInTheDocument();
  });

  it('does not render dialog when isOpen is false', () => {
    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={false}
        onClose={vi.fn()}
        onBuild={vi.fn()}
      />
    );

    expect(screen.queryByText(/Ready to Build/)).not.toBeInTheDocument();
  });

  it('displays template description', () => {
    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={vi.fn()}
      />
    );

    expect(screen.getByText('Python data science packages')).toBeInTheDocument();
  });

  it('displays base OS image', () => {
    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={vi.fn()}
      />
    );

    expect(screen.getByText(/Base OS:/)).toBeInTheDocument();
    expect(screen.getByText('debian:12')).toBeInTheDocument();
  });

  it('displays package count by ecosystem', () => {
    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={vi.fn()}
      />
    );

    // The component renders count and ecosystem separately
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('PYPI')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('APT')).toBeInTheDocument();
  });

  it('displays estimated build time range', () => {
    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={vi.fn()}
      />
    );

    expect(screen.getByText(/Est\. Build Time:/)).toBeInTheDocument();
    // With 2 PYPI (30s each) + 1 APT (5s) + 10s overhead = 75s = 1-2 minutes
    expect(screen.getByText(/\d+–\d+ minutes/)).toBeInTheDocument();
  });

  it('renders Build and Cancel buttons', () => {
    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={vi.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /Build/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
  });

  it('calls onClose when Cancel button is clicked', () => {
    const onClose = vi.fn();
    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={onClose}
        onBuild={vi.fn()}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('calls onBuild when Build button is clicked', async () => {
    const onBuild = vi.fn().mockResolvedValue(undefined);
    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={onBuild}
      />
    );

    const buildButton = screen.getByRole('button', { name: /Build/i });
    fireEvent.click(buildButton);

    await waitFor(() => {
      expect(onBuild).toHaveBeenCalled();
    });
  });

  it('disables buttons while building', async () => {
    let resolveOnBuild: () => void;
    const buildPromise = new Promise<void>((resolve) => {
      resolveOnBuild = resolve;
    });
    const onBuild = vi.fn(() => buildPromise);

    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={onBuild}
      />
    );

    const buildButton = screen.getByRole('button', { name: /Build/i });
    fireEvent.click(buildButton);

    await waitFor(() => {
      expect(buildButton).toBeDisabled();
    });

    resolveOnBuild!();

    await waitFor(() => {
      expect(buildButton).not.toBeDisabled();
    });
  });

  it('shows loading state while building', async () => {
    let resolveOnBuild: () => void;
    const buildPromise = new Promise<void>((resolve) => {
      resolveOnBuild = resolve;
    });
    const onBuild = vi.fn(() => buildPromise);

    render(
      <BuildConfirmationDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={onBuild}
      />
    );

    const buildButton = screen.getByRole('button', { name: /Build/i });
    fireEvent.click(buildButton);

    await waitFor(() => {
      expect(screen.getByText(/Building\.\.\./)).toBeInTheDocument();
    });

    resolveOnBuild!();
  });

  it('handles template with no packages', () => {
    const templateNoPackages = {
      ...mockTemplate,
      blueprint: { packages: [] }
    };

    render(
      <BuildConfirmationDialog
        template={templateNoPackages}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={vi.fn()}
      />
    );

    expect(screen.getByText(/No packages selected/)).toBeInTheDocument();
  });

  it('handles template with no blueprint', () => {
    const templateNoBlueprint = {
      id: 'starter-2',
      friendly_name: 'Minimal Starter',
      base_image: 'alpine:latest'
    };

    render(
      <BuildConfirmationDialog
        template={templateNoBlueprint as any}
        isOpen={true}
        onClose={vi.fn()}
        onBuild={vi.fn()}
      />
    );

    expect(screen.getByText(/No packages selected/)).toBeInTheDocument();
  });
});
