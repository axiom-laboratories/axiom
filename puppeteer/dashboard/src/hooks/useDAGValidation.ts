import { useState, useEffect } from 'react';
import { validateDAG, ValidationResult } from '../utils/dagValidation';

export interface Node {
  id: string;
  type: string;
}

export interface Edge {
  source: string;
  target: string;
}

export interface UseDAGValidationReturn {
  validation: ValidationResult;
  isValid: boolean;
  hasCycle: boolean;
  maxDepth: number;
}

/**
 * Reactive hook for DAG validation
 * Runs validation on every node/edge change and returns both the full result
 * and extracted convenience flags
 */
export function useDAGValidation(
  nodes: Node[],
  edges: Edge[]
): UseDAGValidationReturn {
  const [validation, setValidation] = useState<ValidationResult>({
    isValid: true,
    hasCycle: false,
    maxDepth: 0,
    depthExceeded: false,
  });

  useEffect(() => {
    // Validate on every node/edge change
    const result = validateDAG(nodes, edges);
    setValidation(result);
  }, [nodes, edges]);

  return {
    validation,
    isValid: validation.isValid,
    hasCycle: validation.hasCycle,
    maxDepth: validation.maxDepth,
  };
}
