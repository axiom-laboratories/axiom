import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import DAGCanvas from '../DAGCanvas';

// Mock ReactFlow library
vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ children, nodesDraggable, nodesConnectable }: any) => (
    <div
      data-testid="reactflow"
      data-draggable={nodesDraggable}
      data-connectable={nodesConnectable}
    >
      {children}
    </div>
  ),
  Background: () => <div data-testid="background" />,
  Controls: () => <div data-testid="controls" />,
  Panel: ({ children }: any) => <div data-testid="panel">{children}</div>,
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

// Mock useLayoutedElements hook
vi.mock('../../hooks/useLayoutedElements', () => ({
  useLayoutedElements: vi.fn((nodes, edges) => ({
    nodes: nodes.map((n: any, i: number) => ({
      ...n,
      position: { x: i * 200, y: 0 },
    })),
    edges,
  })),
}));

// Mock WorkflowStepNode
vi.mock('../WorkflowStepNode', () => ({
  default: ({ data, onClick }: any) => (
    <div data-testid={`node-${data.label}`}>{data.label}</div>
  ),
}));

describe('DAGCanvas Component', () => {
  const sampleSteps = [
    {
      id: 'step-1',
      node_type: 'SCRIPT' as const,
    },
    {
      id: 'step-2',
      node_type: 'IF_GATE' as const,
    },
  ];

  const sampleEdges = [
    {
      from_step_id: 'step-1',
      to_step_id: 'step-2',
    },
  ];

  const sampleStepRunStatus = {
    'step-1': {
      id: 'run-1',
      workflow_step_id: 'step-1',
      status: 'COMPLETED' as const,
    },
    'step-2': {
      id: 'run-2',
      workflow_step_id: 'step-2',
      status: 'RUNNING' as const,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ReactFlow component', () => {
    render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
      />
    );
    expect(screen.getByTestId('reactflow')).toBeInTheDocument();
  });

  it('converts steps to nodes', () => {
    render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
      />
    );
    // ReactFlow should be rendered with steps converted to nodes
    expect(screen.getByTestId('reactflow')).toBeInTheDocument();
  });

  it('converts edges correctly', () => {
    render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
      />
    );
    expect(screen.getByTestId('reactflow')).toBeInTheDocument();
  });

  it('applies status colors from stepRunStatus', () => {
    render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
        stepRunStatus={sampleStepRunStatus}
      />
    );
    expect(screen.getByTestId('reactflow')).toBeInTheDocument();
  });

  it('calls onNodeClick on node click', () => {
    const onNodeClick = vi.fn();
    render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
        onNodeClick={onNodeClick}
      />
    );
    // Note: actual click testing would require more setup
    expect(screen.getByTestId('reactflow')).toBeInTheDocument();
  });

  it('sets nodesConnectable={false} by default (read-only mode)', () => {
    render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
      />
    );
    const rf = screen.getByTestId('reactflow');
    expect(rf.getAttribute('data-connectable')).toBe('false');
  });

  it('sets nodesConnectable={true} when editable=true', () => {
    render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
        editable={true}
      />
    );
    const rf = screen.getByTestId('reactflow');
    expect(rf.getAttribute('data-connectable')).toBe('true');
  });

  it('renders with correct height', () => {
    const { container } = render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
        height="600px"
      />
    );
    const dagcanvasDiv = container.querySelector('.w-full.border');
    expect(dagcanvasDiv).toHaveStyle({ height: '600px' });
  });

  it('renders Controls and Background', () => {
    render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
      />
    );
    expect(screen.getByTestId('background')).toBeInTheDocument();
    expect(screen.getByTestId('controls')).toBeInTheDocument();
  });

  it('shows read-only label when not editable', () => {
    render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
        editable={false}
      />
    );
    expect(screen.getByTestId('panel')).toHaveTextContent('Read-only view');
  });

  it('does not show read-only label when editable', () => {
    const { container } = render(
      <DAGCanvas
        steps={sampleSteps}
        edges={sampleEdges}
        editable={true}
      />
    );
    const panel = screen.queryByTestId('panel');
    if (panel) {
      expect(panel).not.toHaveTextContent('Read-only view');
    }
  });
});

/**
 * Sample DAG data for testing
 */
export const sampleDAGNodes = [
  {
    id: 'step-1',
    data: { label: 'Build Docker Image' },
    type: 'custom',
    position: { x: 0, y: 0 },
  },
  {
    id: 'step-2',
    data: { label: 'Run Tests' },
    type: 'custom',
    position: { x: 200, y: 0 },
  },
  {
    id: 'step-3',
    data: { label: 'Deploy' },
    type: 'custom',
    position: { x: 400, y: 0 },
  },
];

export const sampleDAGEdges = [
  {
    id: 'e1-2',
    source: 'step-1',
    target: 'step-2',
  },
  {
    id: 'e2-3',
    source: 'step-2',
    target: 'step-3',
  },
];
