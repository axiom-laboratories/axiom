import React from 'react';
import { toast } from 'sonner';
import { Loader2, ChevronRight } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetClose,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { useStepLogs } from '@/hooks/useStepLogs';
import { getStatusVariant } from '@/utils/workflowStatusUtils';

/**
 * Interfaces for workflow step data
 */
interface WorkflowStepResponse {
  id: string;
  label: string;
  node_type:
    | 'SCRIPT'
    | 'IF_GATE'
    | 'AND_JOIN'
    | 'OR_GATE'
    | 'PARALLEL'
    | 'SIGNAL_WAIT';
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
  started_at?: string;
  completed_at?: string;
  job_guid?: string;
  step_detail?: WorkflowStepResponse;
}

interface WorkflowStepDrawerProps {
  step?: WorkflowStepRunResponse;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Right-side drawer component for viewing step execution logs and details.
 *
 * Features:
 * - Display step name, node type badge, status badge, timestamps
 * - For RUNNING/COMPLETED/FAILED steps: fetch and display logs
 * - For PENDING/SKIPPED/CANCELLED steps: show "not run yet" message
 * - Read-only in Phase 150 (no action buttons)
 * - Uses shadcn Sheet component for smooth slide-in from right
 *
 * @example
 * const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
 * const selectedStep = step_runs?.find(s => s.id === selectedStepId);
 *
 * <WorkflowStepDrawer
 *   step={selectedStep}
 *   isOpen={!!selectedStepId}
 *   onClose={() => setSelectedStepId(null)}
 * />
 */
export const WorkflowStepDrawer: React.FC<WorkflowStepDrawerProps> = ({
  step,
  isOpen,
  onClose,
}) => {
  // Fetch logs for run steps (RUNNING/COMPLETED/FAILED)
  const { data: logs, isLoading, error } = useStepLogs(
    step?.status && ['RUNNING', 'COMPLETED', 'FAILED'].includes(step.status)
      ? step.job_guid
      : null
  );

  // Show error toast if log fetch fails
  React.useEffect(() => {
    if (error) {
      toast.error('Failed to load step logs');
    }
  }, [error]);

  if (!step) {
    return null;
  }

  const stepName = step.step_detail?.label || step.workflow_step_id || 'Unknown';
  const nodeType = step.step_detail?.node_type || 'SCRIPT';
  const status = step.status;
  const isRunStep = ['RUNNING', 'COMPLETED', 'FAILED'].includes(status);

  // Calculate duration if both timestamps exist
  const duration =
    step.started_at && step.completed_at
      ? ((new Date(step.completed_at).getTime() -
          new Date(step.started_at).getTime()) /
          1000).toFixed(2)
      : null;

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="w-[95vw] max-w-2xl flex flex-col overflow-hidden">
        <SheetHeader className="border-b border-border pb-4 shrink-0">
          <div className="flex items-center gap-2 mb-2">
            <SheetTitle className="text-lg font-bold">{stepName}</SheetTitle>
            <Badge variant="outline" className="text-xs">
              {nodeType}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={getStatusVariant(status)}>
              {status}
            </Badge>
          </div>
          <SheetClose />
        </SheetHeader>

        {/* Metadata section */}
        <div className="border-b border-border py-4 shrink-0">
          <div className="grid grid-cols-2 gap-4 text-sm">
            {step.started_at && (
              <div>
                <p className="text-xs font-semibold text-muted-foreground">
                  STARTED
                </p>
                <p className="text-foreground">
                  {new Date(step.started_at).toLocaleString()}
                </p>
              </div>
            )}
            {step.completed_at && (
              <div>
                <p className="text-xs font-semibold text-muted-foreground">
                  COMPLETED
                </p>
                <p className="text-foreground">
                  {new Date(step.completed_at).toLocaleString()}
                </p>
              </div>
            )}
            {duration && (
              <div>
                <p className="text-xs font-semibold text-muted-foreground">
                  DURATION
                </p>
                <p className="text-foreground">{duration}s</p>
              </div>
            )}
          </div>
        </div>

        {/* Log content section */}
        <div className="flex-1 overflow-auto">
          {isRunStep ? (
            // Render logs for RUNNING/COMPLETED/FAILED steps
            <>
              {isLoading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : logs ? (
                <div className="space-y-4 p-4">
                  {logs.stdout && (
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground mb-2">
                        STDOUT
                      </p>
                      <pre className="bg-black/50 text-foreground/90 p-3 rounded text-xs overflow-auto max-h-64 border border-border">
                        {logs.stdout}
                      </pre>
                    </div>
                  )}
                  {logs.stderr && (
                    <div>
                      <p className="text-xs font-semibold text-amber-600 mb-2">
                        STDERR
                      </p>
                      <pre className="bg-black/50 text-amber-200 p-3 rounded text-xs overflow-auto max-h-64 border border-amber-900/30">
                        {logs.stderr}
                      </pre>
                    </div>
                  )}
                  {!logs.stdout && !logs.stderr && (
                    <div className="text-center py-8 text-muted-foreground">
                      <p className="text-sm">No output captured for this step</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p className="text-sm">No logs available yet</p>
                </div>
              )}
            </>
          ) : (
            // Render "not run yet" message for PENDING/SKIPPED/CANCELLED steps
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-4 px-4">
                <ChevronRight className="h-12 w-12 text-muted-foreground/40 mx-auto" />
                <div>
                  <p className="text-sm font-medium text-foreground mb-1">
                    {status === 'PENDING'
                      ? 'This step has not run yet'
                      : status === 'SKIPPED'
                        ? 'This step was skipped'
                        : 'This step was cancelled'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {status === 'PENDING'
                      ? 'Check back when the workflow run completes'
                      : 'No execution logs available'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};
