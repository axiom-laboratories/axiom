import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDAGValidation } from '../useDAGValidation';

interface Node {
  id: string;
  type: string;
}

interface Edge {
  source: string;
  target: string;
}

describe('useDAGValidation Hook', () => {
  it('Test 1: returns validation object with isValid, hasCycle, maxDepth', () => {
    const nodes: Node[] = [
      { id: 'A', type: 'SCRIPT' },
      { id: 'B', type: 'SCRIPT' },
    ];
    const edges: Edge[] = [{ source: 'A', target: 'B' }];

    const { result } = renderHook(() => useDAGValidation(nodes, edges));

    expect(result.current.validation).toBeDefined();
    expect(result.current.isValid).toBeDefined();
    expect(result.current.hasCycle).toBeDefined();
    expect(result.current.maxDepth).toBeDefined();
  });

  it('Test 2: on nodes/edges change, validation is recomputed', () => {
    const nodes1: Node[] = [
      { id: 'A', type: 'SCRIPT' },
      { id: 'B', type: 'SCRIPT' },
    ];
    const edges1: Edge[] = [{ source: 'A', target: 'B' }];

    const { result, rerender } = renderHook(
      ({ nodes, edges }) => useDAGValidation(nodes, edges),
      { initialProps: { nodes: nodes1, edges: edges1 } }
    );

    const firstResult = result.current.maxDepth;

    // Change nodes/edges
    const nodes2: Node[] = [
      { id: 'A', type: 'SCRIPT' },
      { id: 'B', type: 'SCRIPT' },
      { id: 'C', type: 'SCRIPT' },
    ];
    const edges2: Edge[] = [
      { source: 'A', target: 'B' },
      { source: 'B', target: 'C' },
    ];

    rerender({ nodes: nodes2, edges: edges2 });

    // Should have updated
    expect(result.current.maxDepth).toBeGreaterThanOrEqual(firstResult);
  });

  it('Test 3: if hasCycle, isValid=false with error banner', () => {
    const nodes: Node[] = [
      { id: 'A', type: 'SCRIPT' },
      { id: 'B', type: 'SCRIPT' },
      { id: 'C', type: 'SCRIPT' },
    ];
    const edges: Edge[] = [
      { source: 'A', target: 'B' },
      { source: 'B', target: 'C' },
      { source: 'C', target: 'A' }, // Cycle
    ];

    const { result } = renderHook(() => useDAGValidation(nodes, edges));

    expect(result.current.hasCycle).toBe(true);
    expect(result.current.isValid).toBe(false);
  });

  it('Test 4: if maxDepth >= 25 && <= 30, isValid=true but warning should show', () => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Build chain of 26 nodes
    for (let i = 0; i < 26; i++) {
      nodes.push({ id: `node_${i}`, type: 'SCRIPT' });
      if (i > 0) {
        edges.push({ source: `node_${i - 1}`, target: `node_${i}` });
      }
    }

    const { result } = renderHook(() => useDAGValidation(nodes, edges));

    expect(result.current.isValid).toBe(true);
    expect(result.current.maxDepth).toBe(26);
  });

  it('Test 5: if maxDepth > 30, isValid=false and error should show', () => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Build chain of 31 nodes
    for (let i = 0; i < 31; i++) {
      nodes.push({ id: `node_${i}`, type: 'SCRIPT' });
      if (i > 0) {
        edges.push({ source: `node_${i - 1}`, target: `node_${i}` });
      }
    }

    const { result } = renderHook(() => useDAGValidation(nodes, edges));

    expect(result.current.isValid).toBe(false);
    expect(result.current.maxDepth).toBe(31);
  });

  it('Test 6: adding an edge that creates a cycle updates validation to hasCycle=true', () => {
    const nodes: Node[] = [
      { id: 'A', type: 'SCRIPT' },
      { id: 'B', type: 'SCRIPT' },
      { id: 'C', type: 'SCRIPT' },
    ];
    const edges1: Edge[] = [
      { source: 'A', target: 'B' },
      { source: 'B', target: 'C' },
    ];

    const { result, rerender } = renderHook(
      ({ nodes, edges }) => useDAGValidation(nodes, edges),
      { initialProps: { nodes, edges: edges1 } }
    );

    expect(result.current.hasCycle).toBe(false);

    // Add edge that creates cycle
    const edges2: Edge[] = [
      { source: 'A', target: 'B' },
      { source: 'B', target: 'C' },
      { source: 'C', target: 'A' },
    ];

    rerender({ nodes, edges: edges2 });

    expect(result.current.hasCycle).toBe(true);
  });

  it('Test 7: removing the cycle-creating edge makes hasCycle false', () => {
    const nodes: Node[] = [
      { id: 'A', type: 'SCRIPT' },
      { id: 'B', type: 'SCRIPT' },
      { id: 'C', type: 'SCRIPT' },
    ];
    const edges1: Edge[] = [
      { source: 'A', target: 'B' },
      { source: 'B', target: 'C' },
      { source: 'C', target: 'A' }, // Cycle
    ];

    const { result, rerender } = renderHook(
      ({ nodes, edges }) => useDAGValidation(nodes, edges),
      { initialProps: { nodes, edges: edges1 } }
    );

    expect(result.current.hasCycle).toBe(true);

    // Remove cycle-creating edge
    const edges2: Edge[] = [
      { source: 'A', target: 'B' },
      { source: 'B', target: 'C' },
    ];

    rerender({ nodes, edges: edges2 });

    expect(result.current.hasCycle).toBe(false);
  });

  it('Test 8: multiple rapid node/edge changes don\'t cause React errors', () => {
    const nodes: Node[] = [
      { id: 'A', type: 'SCRIPT' },
      { id: 'B', type: 'SCRIPT' },
    ];
    let edges: Edge[] = [{ source: 'A', target: 'B' }];

    const { result, rerender } = renderHook(
      ({ nodes, edges }) => useDAGValidation(nodes, edges),
      { initialProps: { nodes, edges } }
    );

    // Simulate rapid changes
    for (let i = 0; i < 10; i++) {
      edges = [...edges];
      rerender({ nodes, edges });
    }

    // Should still have valid result
    expect(result.current.validation).toBeDefined();
    expect(result.current.isValid).toBeDefined();
  });
});
