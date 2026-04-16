import React, { useCallback } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  Panel,
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
}

const DAGCanvas: React.FC<DAGCanvasProps> = ({
  steps,
  edges,
  stepRunStatus = {},
  onNodeClick,
  direction = 'LR',
  editable = false,
  height = '500px',
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

  return (
    <div
      className="w-full border border-border rounded-lg bg-card"
      style={{ height }}
    >
      <ReactFlow
        nodes={layoutedNodes}
        edges={layoutedEdges}
        nodeTypes={{ default: WorkflowStepNode }}
        onNodeClick={handleNodeClick}
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
