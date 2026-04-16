import { useMemo } from 'react';
import { Node, Edge } from '@xyflow/react';
import dagre from '@dagrejs/dagre';

interface UseLayoutedElementsReturn {
  nodes: Node[];
  edges: Edge[];
}

/**
 * Hook to compute node positions using dagre hierarchical layout algorithm.
 * Memoizes the layout computation to prevent flickering on status updates.
 *
 * @param nodes - Array of ReactFlow nodes with positions to be computed
 * @param edges - Array of ReactFlow edges
 * @param direction - Layout direction: 'LR' (left-to-right) or 'TB' (top-to-bottom)
 * @returns Object with positioned nodes and unchanged edges
 */
export function useLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: 'LR' | 'TB' = 'LR'
): UseLayoutedElementsReturn {
  return useMemo(() => {
    // Create a new dagre graph
    const g = new dagre.graphlib.Graph({ compound: true });

    // Set graph direction (LR = left-to-right per CONTEXT.md locked decision)
    g.setGraph({
      rankdir: direction === 'LR' ? 'LR' : 'TB',
    });

    // Set default edge label
    g.setDefaultEdgeLabel(() => ({}));

    // Add all nodes to graph with default dimensions
    nodes.forEach((node) => {
      // Node width/height in pixels; adjust as needed for different shapes
      g.setNode(node.id, { width: 140, height: 70 });
    });

    // Add all edges to graph
    edges.forEach((edge) => {
      g.setEdge(edge.source, edge.target);
    });

    // Compute layout positions using Sugiyama algorithm
    dagre.layout(g);

    // Extract computed positions and update node positions
    const layoutedNodes = nodes.map((node) => {
      const nodeWithPosition = g.node(node.id);
      return {
        ...node,
        position: {
          x: nodeWithPosition.x - (nodeWithPosition.width || 70) / 2,
          y: nodeWithPosition.y - (nodeWithPosition.height || 35) / 2,
        },
      };
    });

    return {
      nodes: layoutedNodes,
      edges,
    };
  }, [nodes, edges, direction]);
  // Dependency array ensures memoization invalidates only when inputs change
}
