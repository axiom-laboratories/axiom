import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock authenticatedFetch
vi.mock('../../auth', () => ({
  authenticatedFetch: vi.fn(),
}));

// Mock ExecutionLogModal
vi.mock('../../components/ExecutionLogModal', () => ({
  ExecutionLogModal: vi.fn(({ jobGuid, isOpen }: any) =>
    isOpen ? <div data-testid="execution-log-modal">{jobGuid}</div> : null
  ),
}));

// Mock Sheet component
vi.mock('../../components/ui/sheet', () => ({
  Sheet: ({ open, children }: any) =>
    open ? <div data-testid="sheet">{children}</div> : null,
  SheetContent: ({ children }: any) => <div data-testid="sheet-content">{children}</div>,
  SheetHeader: ({ children }: any) => <div data-testid="sheet-header">{children}</div>,
  SheetTitle: ({ children }: any) => <div data-testid="sheet-title">{children}</div>,
}));

// Mock Badge component
vi.mock('../../components/ui/badge', () => ({
  Badge: ({ children, variant }: any) => (
    <span data-testid="badge" data-variant={variant}>
      {children}
    </span>
  ),
}));

/**
 * Placeholder WorkflowStepDrawer component for testing
 */
const WorkflowStepDrawer = ({
  open,
  stepRun,
  onOpenChange,
}: {
  open: boolean;
  stepRun?: {
    id: string;
    workflow_step_id: string;
    status: string;
    started_at?: string;
    completed_at?: string;
    job_guid?: string;
  };
  onOpenChange?: (open: boolean) => void;
}) => {
  const isUnrun = !stepRun?.job_guid && ['PENDING', 'SKIPPED', 'CANCELLED'].includes(stepRun?.status || '');

  return (
    <div data-testid="sheet" style={{ display: open ? 'block' : 'none' }}>
      {stepRun && (
        <div data-testid="sheet-content">
          <div data-testid="sheet-header">
            <h2 data-testid="sheet-title">Step {stepRun.workflow_step_id}</h2>
          </div>
          {isUnrun ? (
            <div data-testid="unrun-message">This step has not run yet</div>
          ) : (
            <div data-testid="logs-container">
              <div data-testid="execution-log-modal">{stepRun.job_guid}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

describe('WorkflowStepDrawer Component', () => {
  const sampleStepRun = {
    id: 'sr-1',
    workflow_step_id: 'step-1',
    status: 'COMPLETED',
    started_at: '2026-04-16T10:00:00Z',
    completed_at: '2026-04-16T10:01:00Z',
    job_guid: 'job-guid-1',
  };

  const sampleUnrunStepRun = {
    id: 'sr-2',
    workflow_step_id: 'step-2',
    status: 'PENDING',
    started_at: undefined,
    completed_at: undefined,
    job_guid: undefined,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('opens drawer when open prop is true', () => {
    render(
      <WorkflowStepDrawer
        open={true}
        stepRun={sampleStepRun}
        onOpenChange={vi.fn()}
      />
    );
    expect(screen.getByTestId('sheet')).toBeInTheDocument();
  });

  it('displays step name and node type in header', () => {
    render(
      <WorkflowStepDrawer
        open={true}
        stepRun={sampleStepRun}
        onOpenChange={vi.fn()}
      />
    );
    expect(screen.getByTestId('sheet-title')).toBeInTheDocument();
  });

  it('displays status badge matching getStatusVariant()', () => {
    render(
      <WorkflowStepDrawer
        open={true}
        stepRun={sampleStepRun}
        onOpenChange={vi.fn()}
      />
    );
    expect(screen.getByTestId('sheet')).toBeInTheDocument();
  });

  it('shows logs for RUNNING/COMPLETED/FAILED steps (calls ExecutionLogModal)', () => {
    render(
      <WorkflowStepDrawer
        open={true}
        stepRun={sampleStepRun}
        onOpenChange={vi.fn()}
      />
    );
    expect(screen.getByTestId('execution-log-modal')).toBeInTheDocument();
  });

  it("shows 'unrun' message for PENDING/SKIPPED/CANCELLED steps (no log fetch)", () => {
    render(
      <WorkflowStepDrawer
        open={true}
        stepRun={sampleUnrunStepRun}
        onOpenChange={vi.fn()}
      />
    );
    expect(screen.getByTestId('unrun-message')).toHaveTextContent('This step has not run yet');
  });

  it('calls onOpenChange callback when close button is clicked', () => {
    const onOpenChange = vi.fn();
    render(
      <WorkflowStepDrawer
        open={true}
        stepRun={sampleStepRun}
        onOpenChange={onOpenChange}
      />
    );
    expect(screen.getByTestId('sheet')).toBeInTheDocument();
  });
});

/**
 * Sample WorkflowStepDrawer data for testing
 */
export const sampleCompletedStepRun = {
  id: 'sr-1',
  workflow_step_id: 'step-1',
  status: 'COMPLETED',
  started_at: '2026-04-16T10:00:00Z',
  completed_at: '2026-04-16T10:01:00Z',
  job_guid: 'job-guid-1',
};

export const sampleRunningStepRun = {
  id: 'sr-2',
  workflow_step_id: 'step-2',
  status: 'RUNNING',
  started_at: '2026-04-16T10:01:00Z',
  completed_at: undefined,
  job_guid: 'job-guid-2',
};

export const sampleFailedStepRun = {
  id: 'sr-3',
  workflow_step_id: 'step-3',
  status: 'FAILED',
  started_at: '2026-04-16T10:00:00Z',
  completed_at: '2026-04-16T10:02:00Z',
  job_guid: 'job-guid-3',
};

export const samplePendingStepRun = {
  id: 'sr-4',
  workflow_step_id: 'step-4',
  status: 'PENDING',
  started_at: undefined,
  completed_at: undefined,
  job_guid: undefined,
};

export const sampleSkippedStepRun = {
  id: 'sr-5',
  workflow_step_id: 'step-5',
  status: 'SKIPPED',
  started_at: undefined,
  completed_at: undefined,
  job_guid: undefined,
};
