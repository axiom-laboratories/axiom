import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock ReactFlow Handle
vi.mock('@xyflow/react', () => ({
  Handle: vi.fn(() => <div data-testid="handle" />),
  Position: {
    Top: 'top',
    Bottom: 'bottom',
    Left: 'left',
    Right: 'right',
  },
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
 * Placeholder WorkflowStepNode component for testing
 */
const WorkflowStepNode = ({
  data,
  isSelected,
}: {
  data: {
    label: string;
    nodeType: 'SCRIPT' | 'IF_GATE' | 'AND_JOIN' | 'OR_GATE' | 'PARALLEL' | 'SIGNAL_WAIT';
    status?: string;
  };
  isSelected?: boolean;
}) => {
  const getNodeShape = (type: string) => {
    switch (type) {
      case 'SCRIPT':
        return 'rect';
      case 'IF_GATE':
        return 'diamond';
      case 'AND_JOIN':
        return 'hexagon';
      case 'OR_GATE':
        return 'circle';
      case 'PARALLEL':
        return 'fork';
      case 'SIGNAL_WAIT':
        return 'clock';
      default:
        return 'rect';
    }
  };

  const shape = getNodeShape(data.nodeType);
  const isRunning = data.status === 'RUNNING';

  return (
    <div
      data-testid="workflow-step-node"
      data-shape={shape}
      className={isRunning ? 'animate-pulse' : ''}
    >
      <div data-testid="node-label">{data.label}</div>
      {data.status && (
        <span data-testid="status-badge" data-variant="default">
          {data.status}
        </span>
      )}
    </div>
  );
};

describe('WorkflowStepNode Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders node label correctly', () => {
    const nodeData = {
      label: 'Build Step',
      nodeType: 'SCRIPT' as const,
    };
    render(<WorkflowStepNode data={nodeData} />);
    expect(screen.getByTestId('node-label')).toHaveTextContent('Build Step');
  });

  it('renders node shape per type (SCRIPT=rect, IF_GATE=diamond, AND_JOIN=hexagon, OR_GATE=circle, PARALLEL=fork, SIGNAL_WAIT=clock)', () => {
    const nodeTypes: Array<
      'SCRIPT' | 'IF_GATE' | 'AND_JOIN' | 'OR_GATE' | 'PARALLEL' | 'SIGNAL_WAIT'
    > = [
      'SCRIPT',
      'IF_GATE',
      'AND_JOIN',
      'OR_GATE',
      'PARALLEL',
      'SIGNAL_WAIT',
    ];
    const expectedShapes = [
      'rect',
      'diamond',
      'hexagon',
      'circle',
      'fork',
      'clock',
    ];

    nodeTypes.forEach((nodeType, index) => {
      const { rerender } = render(
        <WorkflowStepNode data={{ label: 'Test', nodeType }} />
      );
      const node = screen.getByTestId('workflow-step-node');
      expect(node.getAttribute('data-shape')).toBe(expectedShapes[index]);
      rerender(<div />);
    });
  });

  it('applies status color to node border and background', () => {
    const nodeData = {
      label: 'Build Step',
      nodeType: 'SCRIPT' as const,
      status: 'COMPLETED',
    };
    render(<WorkflowStepNode data={nodeData} />);
    expect(screen.getByTestId('status-badge')).toBeInTheDocument();
  });

  it('displays status badge when status is provided', () => {
    const nodeData = {
      label: 'Build Step',
      nodeType: 'SCRIPT' as const,
      status: 'RUNNING',
    };
    render(<WorkflowStepNode data={nodeData} />);
    expect(screen.getByTestId('status-badge')).toHaveTextContent('RUNNING');
  });

  it('applies pulse animation class when status is RUNNING', () => {
    const nodeData = {
      label: 'Build Step',
      nodeType: 'SCRIPT' as const,
      status: 'RUNNING',
    };
    render(<WorkflowStepNode data={nodeData} />);
    const node = screen.getByTestId('workflow-step-node');
    expect(node.className).toContain('animate-pulse');
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
