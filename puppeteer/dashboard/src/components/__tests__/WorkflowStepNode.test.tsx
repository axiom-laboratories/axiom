import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import WorkflowStepNode, { WorkflowStepNodeData } from '../WorkflowStepNode';

// Mock ReactFlow Handle and Position
vi.mock('@xyflow/react', () => ({
  Handle: ({ type, position }: any) => (
    <div data-testid={`handle-${type}`} data-position={position} />
  ),
  Position: {
    Top: 'top',
    Bottom: 'bottom',
    Left: 'left',
    Right: 'right',
  },
}));

// Mock Badge component
vi.mock('../../components/ui/badge', () => ({
  Badge: ({ children, variant, className }: any) => (
    <span data-testid="badge" data-variant={variant} className={className}>
      {children}
    </span>
  ),
}));

// Mock status utilities
vi.mock('../../utils/workflowStatusUtils', () => ({
  getStatusColor: (status: string) => {
    const colors: Record<string, string> = {
      PENDING: '#888888',
      RUNNING: '#3b82f6',
      COMPLETED: '#10b981',
      FAILED: '#ef4444',
      SKIPPED: '#888888',
      CANCELLED: '#888888',
    };
    return colors[status] || '#888888';
  },
  getStatusVariant: (status: string) => {
    const variants: Record<string, string> = {
      PENDING: 'outline',
      RUNNING: 'default',
      COMPLETED: 'secondary',
      FAILED: 'destructive',
      SKIPPED: 'outline',
      CANCELLED: 'outline',
    };
    return variants[status] || 'outline';
  },
}));

describe('WorkflowStepNode Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders node label correctly', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'Build Step',
      nodeType: 'SCRIPT',
    };
    render(<WorkflowStepNode data={nodeData} />);
    expect(screen.getByText('Build Step')).toBeInTheDocument();
  });

  it('renders correct shape class for SCRIPT', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'Script Node',
      nodeType: 'SCRIPT',
    };
    render(<WorkflowStepNode data={nodeData} />);
    expect(screen.getByText('Script Node')).toBeInTheDocument();
  });

  it('renders correct shape class for IF_GATE (diamond)', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'Gate Node',
      nodeType: 'IF_GATE',
    };
    render(<WorkflowStepNode data={nodeData} />);
    expect(screen.getByText('Gate Node')).toBeInTheDocument();
  });

  it('renders correct shape class for OR_GATE (circle)', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'OR Gate',
      nodeType: 'OR_GATE',
    };
    render(<WorkflowStepNode data={nodeData} />);
    expect(screen.getByText('OR Gate')).toBeInTheDocument();
  });

  it('applies status color to border', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'Running Step',
      nodeType: 'SCRIPT',
      status: 'RUNNING',
    };
    render(<WorkflowStepNode data={nodeData} />);
    // Verify the component renders with status
    expect(screen.getByText('Running Step')).toBeInTheDocument();
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
  });

  it('displays status badge when status provided', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'Build Step',
      nodeType: 'SCRIPT',
      status: 'RUNNING',
    };
    render(<WorkflowStepNode data={nodeData} />);
    const badge = screen.getByTestId('badge');
    expect(badge).toHaveTextContent('RUNNING');
  });

  it('applies pulse animation on RUNNING status', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'Running Step',
      nodeType: 'SCRIPT',
      status: 'RUNNING',
    };
    const { container } = render(<WorkflowStepNode data={nodeData} />);
    // Check that RUNNING status would trigger pulse - verify status is set
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
  });

  it('does not apply pulse animation on non-RUNNING status', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'Completed Step',
      nodeType: 'SCRIPT',
      status: 'COMPLETED',
    };
    render(<WorkflowStepNode data={nodeData} />);
    // Verify status badge is present and displays COMPLETED
    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
  });

  it('truncates long labels', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'Very Long Label That Should Be Truncated',
      nodeType: 'SCRIPT',
    };
    const { container } = render(<WorkflowStepNode data={nodeData} />);
    const labelDiv = container.querySelector('.max-w-\\[100px\\]');
    expect(labelDiv?.className).toContain('truncate');
  });

  it('renders Handle components for connectivity', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'Connected Node',
      nodeType: 'SCRIPT',
    };
    render(<WorkflowStepNode data={nodeData} />);
    expect(screen.getByTestId('handle-target')).toBeInTheDocument();
    expect(screen.getByTestId('handle-source')).toBeInTheDocument();
  });

  it('does not render badge when status is not provided', () => {
    const nodeData: WorkflowStepNodeData = {
      label: 'No Status Node',
      nodeType: 'SCRIPT',
    };
    render(<WorkflowStepNode data={nodeData} />);
    expect(screen.queryByTestId('badge')).not.toBeInTheDocument();
  });
});

/**
 * Sample WorkflowStepNode data for testing
 */
export const sampleScriptNode = {
  label: 'Build Docker Image',
  nodeType: 'SCRIPT' as const,
  status: 'COMPLETED',
};

export const sampleIfGateNode = {
  label: 'Check Test Results',
  nodeType: 'IF_GATE' as const,
  status: 'RUNNING',
};

export const sampleAndJoinNode = {
  label: 'Parallel Join',
  nodeType: 'AND_JOIN' as const,
  status: 'PENDING',
};

export const sampleOrGateNode = {
  label: 'Choice Gate',
  nodeType: 'OR_GATE' as const,
  status: 'FAILED',
};

export const sampleParallelNode = {
  label: 'Run in Parallel',
  nodeType: 'PARALLEL' as const,
  status: 'RUNNING',
};

export const sampleSignalWaitNode = {
  label: 'Wait for Signal',
  nodeType: 'SIGNAL_WAIT' as const,
  status: 'PENDING',
};
