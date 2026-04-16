import { useState, useCallback } from 'react';

export interface Node {
  id: string;
  data: { label: string; scheduled_job_id?: string };
  position: { x: number; y: number };
  type: string;
  selected?: boolean;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  selected?: boolean;
}

export interface UseWorkflowEditReturn {
  nodes: Node[];
  edges: Edge[];
  isEditing: boolean;
  setIsEditing: (editing: boolean) => void;
  handleNodesChange: (changes: any[]) => void;
  handleEdgesChange: (changes: any[]) => void;
  handleConnect: (connection: any) => void;
  handleDrop: (payload: { type: string; nodeId: string; position: { x: number; y: number } }) => void;
  getUnlinkedScriptNodes: () => Node[];
  canSave: () => boolean;
}

/**
 * Hook for managing workflow edit state
 * Handles node/edge mutations, drop interactions, and validation
 */
export function useWorkflowEdit(
  initialNodes: Node[],
  initialEdges: Edge[]
): UseWorkflowEditReturn {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [isEditing, setIsEditing] = useState(false);

  const handleNodesChange = useCallback((changes: any[]) => {
    setNodes((prevNodes) => {
      let updatedNodes = [...prevNodes];
      changes.forEach((change) => {
        if (change.type === 'position') {
          updatedNodes = updatedNodes.map((node) =>
            node.id === change.id
              ? { ...node, position: change.position || node.position }
              : node
          );
        } else if (change.type === 'select') {
          updatedNodes = updatedNodes.map((node) =>
            node.id === change.id
              ? { ...node, selected: change.selected }
              : node
          );
        } else if (change.type === 'remove') {
          updatedNodes = updatedNodes.filter((node) => node.id !== change.id);
        }
      });
      return updatedNodes;
    });
  }, []);

  const handleEdgesChange = useCallback((changes: any[]) => {
    setEdges((prevEdges) => {
      let updatedEdges = [...prevEdges];
      changes.forEach((change) => {
        if (change.type === 'select') {
          updatedEdges = updatedEdges.map((edge) =>
            edge.id === change.id
              ? { ...edge, selected: change.selected }
              : edge
          );
        } else if (change.type === 'remove') {
          updatedEdges = updatedEdges.filter((edge) => edge.id !== change.id);
        }
      });
      return updatedEdges;
    });
  }, []);

  const handleConnect = useCallback((connection: any) => {
    const newEdgeId = `e${Date.now()}`;
    const newEdge: Edge = {
      id: newEdgeId,
      source: connection.source,
      target: connection.target,
    };
    setEdges((prevEdges) => [...prevEdges, newEdge]);
  }, []);

  const handleDrop = useCallback(
    (payload: { type: string; nodeId: string; position: { x: number; y: number } }) => {
      const newNode: Node = {
        id: payload.nodeId,
        type: payload.type,
        data: { label: `${payload.type} Node` },
        position: payload.position,
      };
      setNodes((prevNodes) => [...prevNodes, newNode]);
    },
    []
  );

  const getUnlinkedScriptNodes = useCallback((): Node[] => {
    return nodes.filter(
      (node) => node.type === 'SCRIPT' && !node.data.scheduled_job_id
    );
  }, [nodes]);

  const canSave = useCallback((): boolean => {
    return getUnlinkedScriptNodes().length === 0;
  }, [getUnlinkedScriptNodes]);

  return {
    nodes,
    edges,
    isEditing,
    setIsEditing,
    handleNodesChange,
    handleEdgesChange,
    handleConnect,
    handleDrop,
    getUnlinkedScriptNodes,
    canSave,
  };
}
