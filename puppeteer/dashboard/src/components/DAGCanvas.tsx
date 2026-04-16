import React, { useCallback } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  Panel,
  NodeChange,
  EdgeChange,
  Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import WorkflowStepNode from './WorkflowStepNode';
import { useLayoutedElements } from '@/hooks/useLayoutedElements';

// Type definitions for workflow-related responses
interface WorkflowStepResponse {
  id: string;
  node_type:
    | 'SCRIPT'
    | 'IF_GATE'
    | 'AND_JOIN'
    | 'OR_GATE'
    | 'PARALLEL'
    | 'SIGNAL_WAIT';
}

interface WorkflowEdgeResponse {
  from_step_id: string;
  to_step_id: string;
}

interface WorkflowStepRunResponse {
  id: string;
  workflow_step_id: string;
  status:
    | 'PENDING'
    | 'RUNNING'
    | 'COMPLETED'
    | 'FAILED'
    | 'SKIPPED'
    | 'CANCELLED';
}

interface DAGCanvasProps {
  steps: WorkflowStepResponse[];
  edges: WorkflowEdgeResponse[];
  stepRunStatus?: Record<string, WorkflowStepRunResponse>; // Map step_id → run status
  onNodeClick?: (stepId: string) => void;
  direction?: 'LR' | 'TB';
  editable?: boolean; // For Phase 151: set to true to enable editing
  height?: string; // Default '500px' for list views, '600px' for detail views
  // Edit mode handlers (optional, only used when editable=true)
  onNodesChange?: (changes: NodeChange[]) => void;
  onEdgesChange?: (changes: EdgeChange[]) => void;
  onConnect?: (connection: Connection) => void;
  onDrop?: (event: DragEvent) => void;
  onDragOver?: (event: DragEvent) => void;
}

const DAGCanvas: React.FC<DAGCanvasProps> = ({
  steps,
  edges,
  stepRunStatus = {},
  onNodeClick,
  direction = 'LR',
  editable = false,
  height = '500px',
  onNodesChange,
  onEdgesChange,
  onConnect,
  onDrop,
  onDragOver,
}) => {
  // Convert Workflow steps to ReactFlow nodes
  const nodesList: Node[] = steps.map((step) => ({
    id: step.id,
    data: {
      label: step.id,
      nodeType: step.node_type,
      status: stepRunStatus[step.id]?.status,
    },
    position: { x: 0, y: 0 }, // Will be computed by layout hook
  }));

  // Convert Workflow edges to ReactFlow edges
  const edgesList: Edge[] = edges.map((edge) => ({
    id: `${edge.from_step_id}-${edge.to_step_id}`,
    source: edge.from_step_id,
    target: edge.to_step_id,
  }));

  // Compute layout using dagre
  const { nodes: layoutedNodes, edges: layoutedEdges } = useLayoutedElements(
    nodesList,
    edgesList,
    direction
  );

  const handleNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      onDragOver?.(e as any);
    },
    [onDragOver]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      onDrop?.(e as any);
    },
    [onDrop]
  );

  return (
    <div
      className="w-full border border-border rounded-lg bg-card"
      style={{ height }}
      onDragOver={editable ? handleDragOver : undefined}
      onDrop={editable ? handleDrop : undefined}
    >
      <ReactFlow
        nodes={layoutedNodes}
        edges={layoutedEdges}
        nodeTypes={{ default: WorkflowStepNode }}
        onNodeClick={handleNodeClick}
        onNodesChange={editable ? onNodesChange : undefined}
        onEdgesChange={editable ? onEdgesChange : undefined}
        onConnect={editable ? onConnect : undefined}
        nodesConnectable={editable}
        nodesDraggable={editable}
        fitView
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls position="top-left" />
        {!editable && (
          <Panel position="top-center" className="text-xs text-muted-foreground">
            Read-only view
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
};

export default DAGCanvas;
