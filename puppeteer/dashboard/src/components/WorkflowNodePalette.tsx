import React from 'react';
import {
  Play,
  GitBranch,
  GitMerge,
  Zap,
  Copy,
  PauseCircle,
} from 'lucide-react';

export interface WorkflowNodePaletteProps {
  onNodeAdd: (type: string) => void;
}

export const WorkflowNodePalette: React.FC<WorkflowNodePaletteProps> = ({
  onNodeAdd,
}) => {
  const nodeTypes = [
    {
      type: 'SCRIPT',
      label: 'SCRIPT',
      icon: Play,
      description: 'Execute a job',
    },
    {
      type: 'IF_GATE',
      label: 'IF_GATE',
      icon: GitBranch,
      description: 'Conditional branch',
    },
    {
      type: 'AND_JOIN',
      label: 'AND_JOIN',
      icon: GitMerge,
      description: 'Wait for all inputs',
    },
    {
      type: 'OR_GATE',
      label: 'OR_GATE',
      icon: Zap,
      description: 'Wait for any input',
    },
    {
      type: 'PARALLEL',
      label: 'PARALLEL',
      icon: Copy,
      description: 'Fan-out execution',
    },
    {
      type: 'SIGNAL_WAIT',
      label: 'SIGNAL_WAIT',
      icon: PauseCircle,
      description: 'Wait for signal',
    },
  ];

  const handleDragStart = (
    e: React.DragEvent<HTMLDivElement>,
    type: string
  ) => {
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('application/reactflow', type);
    }
    onNodeAdd(type);
  };

  return (
    <div
      data-testid="node-palette"
      className="w-32 bg-slate-50 border-r border-slate-200 p-3 overflow-y-auto"
    >
      <div className="space-y-2">
        {nodeTypes.map(({ type, label, icon: Icon }) => (
          <div
            key={type}
            draggable
            onDragStart={(e) => handleDragStart(e, type)}
            className="flex items-center gap-2 p-2 bg-white border border-slate-200 rounded cursor-move hover:bg-slate-100 hover:border-slate-300 transition"
          >
            <Icon className="w-4 h-4 text-slate-600" />
            <span className="text-xs font-medium text-slate-700">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
