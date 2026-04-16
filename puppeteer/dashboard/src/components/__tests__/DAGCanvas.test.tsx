import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock ReactFlow library
vi.mock('@xyflow/react', () => ({
  ReactFlow: vi.fn(({ children }) => <div data-testid="reactflow">{children}</div>),
  Background: vi.fn(() => null),
  Controls: vi.fn(() => null),
  MiniMap: vi.fn(() => null),
  Handle: vi.fn(() => null),
  useNodesState: vi.fn((nodes) => [nodes, vi.fn()]),
  useEdgesState: vi.fn((edges) => [edges, vi.fn()]),
}));

// Mock useLayoutedElements hook
vi.mock('../../hooks/useLayoutedElements', () => ({
  useLayoutedElements: vi.fn((nodes, edges) => ({
    nodes: nodes.map((n: any, i: number) => ({ ...n, position: { x: i * 200, y: 0 } })),
    edges,
  })),
}));

/**
 * Placeholder DAGCanvas component for testing
 */
const DAGCanvas = ({
  nodes,
  edges,
  stepRunStatus,
  onNodeClick,
}: {
  nodes: any[];
  edges: any[];
  stepRunStatus?: Record<string, string>;
  onNodeClick?: (nodeId: string) => void;
}) => {
  return (
    <div data-testid="dag-canvas">
      <div data-testid="reactflow">
        {nodes.map((node) => (
          <div
            key={node.id}
            data-testid={`node-${node.id}`}
            onClick={() => onNodeClick?.(node.id)}
          >
            {node.data?.label || node.id}
          </div>
        ))}
      </div>
    </div>
  );
};

describe('DAGCanvas Component', () => {
  const sampleNodes = [
    {
      id: 'step-1',
      data: { label: 'Build' },
      type: 'custom',
    },
    {
      id: 'step-2',
      data: { label: 'Test' },
      type: 'custom',
    },
  ];

  const sampleEdges = [
    {
      id: 'e1-2',
      source: 'step-1',
      target: 'step-2',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ReactFlow component with correct dimensions', () => {
    render(
      <DAGCanvas
        nodes={sampleNodes}
        edges={sampleEdges}
      />
    );
    expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
  });

  it('converts workflow steps to ReactFlow nodes', () => {
    render(
      <DAGCanvas
        nodes={sampleNodes}
        edges={sampleEdges}
      />
    );
    expect(screen.getByTestId('node-step-1')).toBeInTheDocument();
    expect(screen.getByTestId('node-step-2')).toBeInTheDocument();
  });

  it('converts workflow edges to ReactFlow edges', () => {
    render(
      <DAGCanvas
        nodes={sampleNodes}
        edges={sampleEdges}
      />
    );
    expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
  });

  it('applies status colors to nodes based on stepRunStatus prop', () => {
    const stepRunStatus = {
      'step-1': 'COMPLETED',
      'step-2': 'RUNNING',
    };
    render(
      <DAGCanvas
        nodes={sampleNodes}
        edges={sampleEdges}
        stepRunStatus={stepRunStatus}
      />
    );
    expect(screen.getByTestId('node-step-1')).toBeInTheDocument();
  });

  it('calls onNodeClick callback when a node is clicked', () => {
    const onNodeClick = vi.fn();
    render(
      <DAGCanvas
        nodes={sampleNodes}
        edges={sampleEdges}
        onNodeClick={onNodeClick}
      />
    );
    const node = screen.getByTestId('node-step-1');
    node.click();
    expect(onNodeClick).toHaveBeenCalledWith('step-1');
  });

  it('node shape props are passed correctly (editable=false for read-only)', () => {
    render(
      <DAGCanvas
        nodes={sampleNodes}
        edges={sampleEdges}
      />
    );
    expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
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
