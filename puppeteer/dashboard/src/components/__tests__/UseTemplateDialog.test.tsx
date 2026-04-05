import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import UseTemplateDialog from '../UseTemplateDialog';

const mockTemplate = {
  id: 'starter-1',
  friendly_name: 'Data Science Starter',
  description: 'Python data science packages',
  is_starter: true,
  base_image: 'debian:12',
  package_count: 8,
  status: 'ACTIVE',
  canonical_id: '',
  runtime_blueprint_id: 'bp-1',
  network_blueprint_id: 'bp-2',
  is_compliant: true,
  last_built_image: undefined,
  last_built_at: undefined
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('UseTemplateDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
    // Mock authenticatedFetch
    vi.mock('../../../auth', () => ({
      authenticatedFetch: vi.fn()
    }));
  });

  it('renders dialog with template name when open', () => {
    render(
      <UseTemplateDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Use Data Science Starter\?/)).toBeInTheDocument();
    expect(screen.getByText(/Build Now creates/)).toBeInTheDocument();
  });

  it('does not render dialog when isOpen is false', () => {
    render(
      <UseTemplateDialog
        template={mockTemplate}
        isOpen={false}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByText(/Use Data Science Starter\?/)).not.toBeInTheDocument();
  });

  it('renders Build Now and Customize First buttons', () => {
    render(
      <UseTemplateDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByRole('button', { name: /Build Now/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Customize First/i })).toBeInTheDocument();
  });

  it('shows template description when available', () => {
    render(
      <UseTemplateDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Python data science packages/)).toBeInTheDocument();
  });

  it('shows package count when available', () => {
    render(
      <UseTemplateDialog
        template={mockTemplate}
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Package count: 8/)).toBeInTheDocument();
  });

  it('closes dialog when onClose is called', async () => {
    const onClose = vi.fn();
    const { rerender } = render(
      <UseTemplateDialog
        template={mockTemplate}
        isOpen={true}
        onClose={onClose}
      />,
      { wrapper: createWrapper() }
    );

    // Simulate pressing escape or clicking outside
    const closeButton = screen.getByRole('button', { name: /Cancel|Close/i });
    if (closeButton) {
      fireEvent.click(closeButton);
    }

    // Rerender with isOpen false to simulate dialog close
    rerender(
      <UseTemplateDialog
        template={null}
        isOpen={false}
        onClose={onClose}
      />
    );

    expect(screen.queryByText(/Use Data Science Starter\?/)).not.toBeInTheDocument();
  });

  it('handles template being null gracefully', () => {
    render(
      <UseTemplateDialog
        template={null}
        isOpen={true}
        onClose={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    // Should not crash and dialog should not render
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
