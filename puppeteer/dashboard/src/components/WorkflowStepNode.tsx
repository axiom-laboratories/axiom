import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle } from 'lucide-react';
import {
  getStatusColor,
  getStatusVariant,
} from '@/utils/workflowStatusUtils';

export interface WorkflowStepNodeData {
  label: string;
  nodeType:
    | 'SCRIPT'
    | 'IF_GATE'
    | 'AND_JOIN'
    | 'OR_GATE'
    | 'PARALLEL'
    | 'SIGNAL_WAIT';
  status?:
    | 'PENDING'
    | 'RUNNING'
    | 'COMPLETED'
    | 'FAILED'
    | 'SKIPPED'
    | 'CANCELLED';
  // Edit mode data
  scheduled_job_id?: string | null;
  isEditing?: boolean;
}

interface WorkflowStepNodeProps {
  data: WorkflowStepNodeData;
  isConnecting?: boolean;
  isSelected?: boolean;
}

const WorkflowStepNode: React.FC<WorkflowStepNodeProps> = ({
  data,
  isConnecting,
  isSelected,
}) => {
  const statusColor = data.status ? getStatusColor(data.status) : '#999';
  const statusVariant = data.status ? getStatusVariant(data.status) : 'outline';
  const isPulsing = data.status === 'RUNNING';

  // Shape rendering helper
  const renderNodeShape = () => {
    const baseClasses = `
      flex flex-col items-center justify-center px-3 py-2
      border-2 rounded text-center min-w-[120px]
      transition-all duration-200
      ${isPulsing ? 'animate-pulse' : ''}
      ${isSelected ? 'ring-2 ring-offset-2' : ''}
      ${data.isEditing && data.nodeType === 'SCRIPT' && !data.scheduled_job_id ? 'cursor-pointer' : ''}
    `;

    const shapeClasses: Record<string, string> = {
      SCRIPT: 'rounded-md', // rectangle
      IF_GATE: 'transform rotate-45 rounded-sm', // diamond (rotated square)
      AND_JOIN: 'rounded-lg', // hexagon approximation with border
      OR_GATE: 'rounded-full', // circle
      PARALLEL: 'rounded-lg', // rounded rectangle (fork-like)
      SIGNAL_WAIT: 'rounded-full', // circle with hourglass/clock icon
    };

    const isUnlinked = data.isEditing && data.nodeType === 'SCRIPT' && !data.scheduled_job_id;

    return (
      <div
        className={`relative ${baseClasses} ${shapeClasses[data.nodeType] || 'rounded-md'}`}
        style={{
          borderColor: statusColor,
          backgroundColor: `${statusColor}15`, // 15% opacity background
          minHeight: '60px',
        }}
      >
        <Handle type="target" position={Position.Left} />

        <div className="text-xs font-semibold truncate max-w-[100px]">
          {data.label}
        </div>

        {data.status && (
          <Badge
            variant={statusVariant}
            className="mt-1 text-[10px] whitespace-nowrap"
          >
            {data.status}
          </Badge>
        )}

        {/* Unlinked indicator for SCRIPT nodes in edit mode */}
        {isUnlinked && (
          <div className="absolute -top-2 -right-2 bg-amber-100 text-amber-800 rounded-full px-2 py-1 text-xs flex items-center gap-1 shadow-md">
            <AlertTriangle size={12} />
            Unlinked
          </div>
        )}

        <Handle type="source" position={Position.Right} />
      </div>
    );
  };

  return renderNodeShape();
};

export default WorkflowStepNode;
