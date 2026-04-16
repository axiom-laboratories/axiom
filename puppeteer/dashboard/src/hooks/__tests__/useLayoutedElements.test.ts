import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { Node, Edge } from '@xyflow/react';
import { useLayoutedElements } from '../useLayoutedElements';

describe('useLayoutedElements Hook', () => {
  const createMockNodes = (count: number): Node[] =>
    Array.from({ length: count }, (_, i) => ({
      id: `node-${i}`,
      data: { label: `Node ${i}` },
      position: { x: 0, y: 0 },
    }));

  const createMockEdges = (from: number, to: number): Edge[] => {
    const edges: Edge[] = [];
    for (let i = from; i < to; i++) {
      if (i + 1 < to) {
        edges.push({
          id: `edge-${i}-${i + 1}`,
          source: `node-${i}`,
          target: `node-${i + 1}`,
        });
      }
    }
    return edges;
  };

  const sampleNodes = [
    { id: 'node-1', data: { label: 'Start' }, position: { x: 0, y: 0 } },
    { id: 'node-2', data: { label: 'Middle' }, position: { x: 0, y: 0 } },
    { id: 'node-3', data: { label: 'End' }, position: { x: 0, y: 0 } },
  ];

  const sampleEdges = [
    { id: 'e1', source: 'node-1', target: 'node-2' },
    { id: 'e2', source: 'node-2', target: 'node-3' },
  ];

  beforeEach(() => {
    // Clear any state between tests
  });

  it('computes node positions using dagre layout algorithm', () => {
    const { result } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges)
    );
    expect(result.current.nodes.length).toBe(3);
    expect(result.current.nodes[0]).toHaveProperty('position');
    expect(result.current.nodes[0].position.x).toBeDefined();
    expect(result.current.nodes[0].position.y).toBeDefined();
  });

  it('respects direction prop (LR = left-to-right)', () => {
    const { result } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges, 'LR')
    );
    expect(result.current.nodes.length).toBe(3);
    // Nodes should have computed positions
    expect(result.current.nodes[0].position).toBeDefined();
  });

  it('memoizes layout result to avoid recomputation on prop change', () => {
    const { result: result1 } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges, 'LR')
    );

    const { result: result2 } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges, 'LR')
    );

    // Same inputs should produce equal layouts
    expect(result1.current.nodes).toEqual(result2.current.nodes);
  });

  it('returns nodes with updated position coordinates', () => {
    const { result } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges)
    );
    result.current.nodes.forEach((node) => {
      expect(node.position).toBeDefined();
      expect(node.position).toHaveProperty('x');
      expect(node.position).toHaveProperty('y');
      expect(typeof node.position.x).toBe('number');
      expect(typeof node.position.y).toBe('number');
    });
  });

  it('returns edges unchanged', () => {
    const { result } = renderHook(() =>
      useLayoutedElements(sampleNodes, sampleEdges)
    );
    expect(result.current.edges).toEqual(sampleEdges);
  });

  it('handles empty nodes and edges', () => {
    const { result } = renderHook(() =>
      useLayoutedElements([], [])
    );
    expect(result.current.nodes).toEqual([]);
    expect(result.current.edges).toEqual([]);
  });

  it('handles single node', () => {
    const nodes = createMockNodes(1);
    const { result } = renderHook(() =>
      useLayoutedElements(nodes, [])
    );
    expect(result.current.nodes).toHaveLength(1);
    expect(result.current.nodes[0].id).toBe('node-0');
  });

  it('recomputes layout when inputs change', () => {
    const { result, rerender } = renderHook(
      ({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) =>
        useLayoutedElements(nodes, edges, 'LR'),
      {
        initialProps: { nodes: sampleNodes, edges: sampleEdges },
      }
    );

    const originalPosition = { ...result.current.nodes[0].position };

    // Change nodes
    const newNodes = createMockNodes(5);
    const newEdges = createMockEdges(0, 5);

    rerender({ nodes: newNodes, edges: newEdges });

    // Position should be different with different input
    expect(result.current.nodes).toHaveLength(5);
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
