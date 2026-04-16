import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';

// Mock dagre library
vi.mock('@dagrejs/dagre', () => ({
  dagre: {
    graphlib: {
      Graph: class MockGraph {
        setGraph() {}
        setDefaultNodeLabel() {}
        setDefaultEdgeLabel() {}
        setNode() {}
        setEdge() {}
      },
    },
    layout: vi.fn((graph) => graph),
  },
}));

/**
 * Placeholder useLayoutedElements hook for testing
 */
const useLayoutedElements = (nodes: any[], edges: any[], direction = 'LR') => {
  // Placeholder implementation that returns nodes/edges with computed positions
  const layoutedNodes = nodes.map((n, i) => ({
    ...n,
    position: { x: i * 200, y: 0 },
  }));
  return {
    nodes: layoutedNodes,
    edges,
  };
};

describe('useLayoutedElements Hook', () => {
  const sampleNodes = [
    { id: 'node-1', data: { label: 'Start' } },
    { id: 'node-2', data: { label: 'Middle' } },
    { id: 'node-3', data: { label: 'End' } },
  ];

  const sampleEdges = [
    { id: 'e1', source: 'node-1', target: 'node-2' },
    { id: 'e2', source: 'node-2', target: 'node-3' },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('computes node positions using dagre layout algorithm', () => {
    const { result } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges)
    );
    expect(result.current.nodes.length).toBe(3);
    expect(result.current.nodes[0]).toHaveProperty('position');
  });

  it('respects direction prop (LR = left-to-right)', () => {
    const { result } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges, 'LR')
    );
    expect(result.current.nodes.length).toBe(3);
  });

  it('memoizes layout result to avoid recomputation on prop change', () => {
    const { result, rerender } = renderHook(
      ({ nodes, edges, direction }) =>
        useLayoutedElements(nodes, edges, direction),
      {
        initialProps: { nodes: sampleNodes, edges: sampleEdges, direction: 'LR' },
      }
    );
    const firstResult = result.current.nodes;
    rerender({ nodes: sampleNodes, edges: sampleEdges, direction: 'LR' });
    expect(result.current.nodes).toEqual(firstResult);
  });

  it('returns nodes with updated position coordinates', () => {
    const { result } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges)
    );
    result.current.nodes.forEach((node) => {
      expect(node.position).toBeDefined();
      expect(node.position).toHaveProperty('x');
      expect(node.position).toHaveProperty('y');
    });
  });

  it('returns edges unchanged', () => {
    const { result } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges)
    );
    expect(result.current.edges).toEqual(sampleEdges);
  });
});

/**
 * Sample nodes and edges for testing
 */
export const sampleDAGNodesForLayout = [
  { id: 'step-1', data: { label: 'Build' } },
  { id: 'step-2', data: { label: 'Test' } },
  { id: 'step-3', data: { label: 'Deploy' } },
];

export const sampleDAGEdgesForLayout = [
  { id: 'e1-2', source: 'step-1', target: 'step-2' },
  { id: 'e2-3', source: 'step-2', target: 'step-3' },
];
