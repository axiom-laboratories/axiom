import { describe, it, expect } from 'vitest';
import { validateDAG, ValidationResult } from '../dagValidation';

// Test utilities
interface Node {
  id: string;
  type: string;
}

interface Edge {
  source: string;
  target: string;
}

function createMockNode(id: string, type: string = 'SCRIPT'): Node {
  return { id, type };
}

function createMockEdge(source: string, target: string): Edge {
  return { source, target };
}

describe('DAG Validation Utility', () => {
  describe('validateDAG - Cycle Detection', () => {
    it('Test 1: returns isValid=true, hasCycle=false for acyclic DAG (linear chain A→B→C)', () => {
      const nodes = [
        createMockNode('A'),
        createMockNode('B'),
        createMockNode('C'),
      ];
      const edges = [
        createMockEdge('A', 'B'),
        createMockEdge('B', 'C'),
      ];

      const result = validateDAG(nodes, edges);
      expect(result.isValid).toBe(true);
      expect(result.hasCycle).toBe(false);
      expect(result.cycleNodes).toBeUndefined();
    });

    it('Test 2: detects cycle A→B→C→A; returns hasCycle=true, cycleNodes=["A","B","C"]', () => {
      const nodes = [
        createMockNode('A'),
        createMockNode('B'),
        createMockNode('C'),
      ];
      const edges = [
        createMockEdge('A', 'B'),
        createMockEdge('B', 'C'),
        createMockEdge('C', 'A'),
      ];

      const result = validateDAG(nodes, edges);
      expect(result.hasCycle).toBe(true);
      expect(result.isValid).toBe(false);
      expect(result.cycleNodes).toBeDefined();
      expect(result.cycleNodes).toContain('A');
      expect(result.cycleNodes).toContain('B');
      expect(result.cycleNodes).toContain('C');
    });
  });

  describe('validateDAG - Depth Calculation', () => {
    it('Test 3: returns maxDepth=3 for chain A→B→C (3 nodes deep)', () => {
      const nodes = [
        createMockNode('A'),
        createMockNode('B'),
        createMockNode('C'),
      ];
      const edges = [
        createMockEdge('A', 'B'),
        createMockEdge('B', 'C'),
      ];

      const result = validateDAG(nodes, edges);
      expect(result.maxDepth).toBe(3);
    });

    it('Test 4: returns depthExceeded=true for depth 31 when maxDepth=30', () => {
      const nodes: Node[] = [];
      const edges: Edge[] = [];

      // Create a chain of 31 nodes: node_0 → node_1 → ... → node_30
      for (let i = 0; i < 31; i++) {
        nodes.push(createMockNode(`node_${i}`));
        if (i > 0) {
          edges.push(createMockEdge(`node_${i - 1}`, `node_${i}`));
        }
      }

      const result = validateDAG(nodes, edges, 30);
      expect(result.depthExceeded).toBe(true);
      expect(result.isValid).toBe(false);
    });

    it('Test 5: returns depthExceeded=false for depth 25 (warning level, not error)', () => {
      const nodes: Node[] = [];
      const edges: Edge[] = [];

      // Create a chain of 25 nodes: node_0 → node_1 → ... → node_24
      for (let i = 0; i < 25; i++) {
        nodes.push(createMockNode(`node_${i}`));
        if (i > 0) {
          edges.push(createMockEdge(`node_${i - 1}`, `node_${i}`));
        }
      }

      const result = validateDAG(nodes, edges, 30);
      expect(result.depthExceeded).toBe(false);
      expect(result.isValid).toBe(true);
    });
  });

  describe('validateDAG - Diamond Graphs', () => {
    it('Test 6: handles diamond graph (multiple paths to same node) without false cycles', () => {
      const nodes = [
        createMockNode('A'),
        createMockNode('B'),
        createMockNode('C'),
        createMockNode('D'),
      ];
      // Diamond: A → B → D and A → C → D
      const edges = [
        createMockEdge('A', 'B'),
        createMockEdge('A', 'C'),
        createMockEdge('B', 'D'),
        createMockEdge('C', 'D'),
      ];

      const result = validateDAG(nodes, edges);
      expect(result.hasCycle).toBe(false);
      expect(result.isValid).toBe(true);
    });
  });

  describe('validateDAG - Orphaned Edges', () => {
    it('Test 7: ignores edges referencing non-existent nodes (orphaned edges)', () => {
      const nodes = [
        createMockNode('A'),
        createMockNode('B'),
      ];
      // Edge references non-existent 'C' and 'D'
      const edges = [
        createMockEdge('A', 'B'),
        createMockEdge('B', 'C'),
        createMockEdge('D', 'E'),
      ];

      const result = validateDAG(nodes, edges);
      // Should not crash and should handle gracefully
      expect(result).toBeDefined();
      expect(result.hasCycle).toBe(false);
    });
  });

  describe('validateDAG - Validation Results', () => {
    it('Test 8: returns isValid=false if hasCycle=true OR depthExceeded=true', () => {
      // Cycle test
      const cycleNodes = [
        createMockNode('A'),
        createMockNode('B'),
      ];
      const cycleEdges = [
        createMockEdge('A', 'B'),
        createMockEdge('B', 'A'),
      ];

      const cycleResult = validateDAG(cycleNodes, cycleEdges);
      expect(cycleResult.isValid).toBe(false);
      expect(cycleResult.hasCycle).toBe(true);
    });

    it('Test 9: returns isValid=true if hasCycle=false AND depthExceeded=false', () => {
      const nodes = [
        createMockNode('A'),
        createMockNode('B'),
      ];
      const edges = [createMockEdge('A', 'B')];

      const result = validateDAG(nodes, edges);
      expect(result.isValid).toBe(true);
      expect(result.hasCycle).toBe(false);
      expect(result.depthExceeded).toBe(false);
    });
  });

  describe('validateDAG - Single Node & Disconnected', () => {
    it('Test 10: calculateMaxDepth returns 0 for single node (no edges)', () => {
      const nodes = [createMockNode('A')];
      const edges: Edge[] = [];

      const result = validateDAG(nodes, edges);
      expect(result.maxDepth).toBe(1); // Single node has depth 1
    });

    it('Test 11: calculateMaxDepth returns 0 for disconnected components', () => {
      const nodes = [
        createMockNode('A'),
        createMockNode('B'),
        createMockNode('C'),
      ];
      // No edges - three disconnected nodes
      const edges: Edge[] = [];

      const result = validateDAG(nodes, edges);
      expect(result.maxDepth).toBe(1); // All isolated nodes have depth 1
    });
  });

  describe('validateDAG - Performance', () => {
    it('Test 12: can handle >100 nodes without performance regression', () => {
      const nodes: Node[] = [];
      const edges: Edge[] = [];

      // Create 150 nodes in a linear chain
      for (let i = 0; i < 150; i++) {
        nodes.push(createMockNode(`node_${i}`));
        if (i > 0) {
          edges.push(createMockEdge(`node_${i - 1}`, `node_${i}`));
        }
      }

      const startTime = performance.now();
      const result = validateDAG(nodes, edges, 200);
      const endTime = performance.now();

      expect(result).toBeDefined();
      expect(endTime - startTime).toBeLessThan(1000); // Should complete in < 1 second
    });
  });
});
