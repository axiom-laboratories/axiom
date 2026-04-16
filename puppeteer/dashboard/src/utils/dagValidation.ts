/**
 * DAG Validation Utility — Cycle Detection & Depth Calculation
 *
 * Provides real-time validation for Workflow DAGs:
 * - DFS-based cycle detection
 * - Maximum depth calculation
 * - Depth limit enforcement (default max 30 levels)
 */

export interface ValidationResult {
  isValid: boolean;
  hasCycle: boolean;
  cycleNodes?: string[];
  maxDepth: number;
  depthExceeded: boolean;
}

export interface Node {
  id: string;
  type: string;
}

export interface Edge {
  source: string;
  target: string;
}

/**
 * Validates a DAG for cycles and depth constraints
 * @param nodes - Array of nodes with id and type
 * @param edges - Array of edges with source and target
 * @param maxDepth - Maximum allowed depth (default 30)
 * @returns ValidationResult with cycle detection and depth status
 */
export function validateDAG(
  nodes: Node[],
  edges: Edge[],
  maxDepth: number = 30
): ValidationResult {
  // Build node map for quick lookup
  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  // Build adjacency list (only include edges where both nodes exist)
  const adjacencyList = new Map<string, string[]>();
  nodes.forEach(node => {
    adjacencyList.set(node.id, []);
  });

  edges.forEach(edge => {
    // Only add edge if both source and target nodes exist
    if (nodeMap.has(edge.source) && nodeMap.has(edge.target)) {
      const targets = adjacencyList.get(edge.source);
      if (targets) {
        targets.push(edge.target);
      }
    }
  });

  // Cycle detection using DFS
  const visited = new Set<string>();
  const recStack = new Set<string>();
  const path: string[] = [];
  let cycleNodes: string[] | undefined;

  for (const nodeId of nodeMap.keys()) {
    if (!visited.has(nodeId)) {
      const cycle = dfsCycleDetection(nodeId, adjacencyList, visited, recStack, path);
      if (cycle) {
        cycleNodes = cycle;
        break;
      }
    }
  }

  // Depth calculation using memoized DFS
  const depthCache = new Map<string, number>();
  let maxCalculatedDepth = 0;

  for (const nodeId of nodeMap.keys()) {
    const depth = calculateDepth(nodeId, adjacencyList, depthCache);
    maxCalculatedDepth = Math.max(maxCalculatedDepth, depth);
  }

  // For single nodes or disconnected components, depth should be at least 1
  if (nodes.length > 0 && maxCalculatedDepth === 0) {
    maxCalculatedDepth = 1;
  }

  const depthExceeded = maxCalculatedDepth > maxDepth;
  const isValid = !cycleNodes && !depthExceeded;

  return {
    isValid,
    hasCycle: !!cycleNodes,
    cycleNodes,
    maxDepth: maxCalculatedDepth,
    depthExceeded,
  };
}

/**
 * DFS-based cycle detection using recursion stack
 */
function dfsCycleDetection(
  nodeId: string,
  adjacencyList: Map<string, string[]>,
  visited: Set<string>,
  recStack: Set<string>,
  path: string[]
): string[] | null {
  visited.add(nodeId);
  recStack.add(nodeId);
  path.push(nodeId);

  const neighbors = adjacencyList.get(nodeId) || [];
  for (const neighbor of neighbors) {
    if (!visited.has(neighbor)) {
      const cycle = dfsCycleDetection(neighbor, adjacencyList, visited, recStack, path);
      if (cycle) {
        return cycle;
      }
    } else if (recStack.has(neighbor)) {
      // Found a back edge (cycle) - extract the cycle from the path
      const cycleStart = path.indexOf(neighbor);
      if (cycleStart !== -1) {
        return path.slice(cycleStart).concat([neighbor]);
      }
      return [neighbor, nodeId];
    }
  }

  path.pop();
  recStack.delete(nodeId);
  return null;
}

/**
 * Calculate maximum depth from a given node using memoization
 * Handles cycles by not recursing into already-visiting nodes
 */
function calculateDepth(
  nodeId: string,
  adjacencyList: Map<string, string[]>,
  cache: Map<string, number>,
  visiting: Set<string> = new Set()
): number {
  if (cache.has(nodeId)) {
    return cache.get(nodeId)!;
  }

  // If already visiting this node, we've found a cycle - don't recurse
  if (visiting.has(nodeId)) {
    return 1;
  }

  visiting.add(nodeId);
  const neighbors = adjacencyList.get(nodeId) || [];
  let maxChildDepth = 0;

  for (const neighbor of neighbors) {
    const childDepth = calculateDepth(neighbor, adjacencyList, cache, visiting);
    maxChildDepth = Math.max(maxChildDepth, childDepth);
  }

  visiting.delete(nodeId);
  const depth = 1 + maxChildDepth;
  cache.set(nodeId, depth);
  return depth;
}
