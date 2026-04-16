import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { authenticatedFetch } from '@/auth';
import DAGCanvas from '@/components/DAGCanvas';
import { getStatusVariant } from '@/utils/workflowStatusUtils';
import { useWebSocket } from '@/hooks/useWebSocket';

interface WorkflowStepResponse {
  id: string;
  node_type: string;
  scheduled_job_id?: string;
}

interface WorkflowEdgeResponse {
  from_step_id: string;
  to_step_id: string;
}

interface WorkflowStepRunResponse {
  id: string;
  workflow_step_id: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED' | 'CANCELLED';
  started_at?: string;
  completed_at?: string;
  job_guid?: string;
}

interface WorkflowRunResponse {
  id: string;
  workflow_id: string;
  status: 'RUNNING' | 'COMPLETED' | 'PARTIAL' | 'FAILED' | 'CANCELLED';
  started_at: string;
  completed_at?: string;
  step_runs: WorkflowStepRunResponse[];
  steps?: WorkflowStepResponse[];
  edges?: WorkflowEdgeResponse[];
}

export function WorkflowRunDetail() {
  const { id: workflowId, runId } = useParams<{ id: string; runId: string }>();
  const queryClient = useQueryClient();
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  if (!workflowId || !runId) {
    return <div className="text-destructive">Invalid workflow or run ID</div>;
  }

  // Fetch run details
  const { data: run, isLoading, error } = useQuery({
    queryKey: ['workflow-run', runId],
    queryFn: async () => {
      const res = await authenticatedFetch(`/api/workflows/${workflowId}/runs/${runId}`);
      if (!res.ok) throw new Error('Failed to fetch run');
      return res.json() as Promise<WorkflowRunResponse>;
    },
    refetchInterval: 5000, // Fallback polling for status updates
  });

  // Listen for WebSocket updates
  useEffect(() => {
    const handleMessage = (event: string, data: any) => {
      if (event === 'workflow_step_updated' && data.workflow_run_id === runId) {
        // Update step status in cache
        queryClient.setQueryData(
          ['workflow-run', runId],
          (oldRun: WorkflowRunResponse | undefined) => {
            if (!oldRun) return oldRun;
            return {
              ...oldRun,
              step_runs: oldRun.step_runs.map((sr) =>
                sr.id === data.id
                  ? {
                      ...sr,
                      status: data.status,
                      completed_at: data.completed_at,
                      started_at: data.started_at,
                    }
                  : sr
              ),
            };
          }
        );
      } else if (event === 'workflow_run_updated' && data.id === runId) {
        // Update run status in cache
        queryClient.setQueryData(
          ['workflow-run', runId],
          (oldRun: WorkflowRunResponse | undefined) => {
            if (!oldRun) return oldRun;
            return {
              ...oldRun,
              status: data.status,
              completed_at: data.completed_at,
            };
          }
        );
      }
    };

    useWebSocket(handleMessage);
  }, [runId, queryClient]);

  // Map step_runs to step IDs for DAG status overlay
  const stepRunStatus: Record<string, WorkflowStepRunResponse> = {};
  if (run?.step_runs) {
    run.step_runs.forEach((sr) => {
      stepRunStatus[sr.workflow_step_id] = sr;
    });
  }

  const handleNodeClick = (stepId: string) => {
    setSelectedStepId(stepId);
    // Drawer open will be handled in Plan 05 (WorkflowStepDrawer integration)
  };

  return (
    <div className="space-y-6">
      {isLoading && <p className="text-muted-foreground">Loading run details...</p>}
      {error && (
        <p className="text-destructive">
          Error: {error instanceof Error ? error.message : 'Unknown'}
        </p>
      )}

      {run && (
        <>
          {/* Run header with status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Run Details</span>
                <Badge variant={getStatusVariant(run.status)}>{run.status}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Started</p>
                  <p>{new Date(run.started_at).toLocaleString()}</p>
                </div>
                {run.completed_at && (
                  <>
                    <div>
                      <p className="text-muted-foreground">Completed</p>
                      <p>{new Date(run.completed_at).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Duration</p>
                      <p>
                        {(
                          (new Date(run.completed_at).getTime() -
                            new Date(run.started_at).getTime()) /
                          1000
                        ).toFixed(1)}
                        s
                      </p>
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          {/* DAG with status overlay */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Workflow Execution</CardTitle>
            </CardHeader>
            <CardContent>
              {run.steps && run.edges ? (
                <DAGCanvas
                  steps={run.steps}
                  edges={run.edges}
                  stepRunStatus={stepRunStatus}
                  onNodeClick={handleNodeClick}
                  height="500px"
                />
              ) : (
                <p className="text-muted-foreground">No step data available.</p>
              )}
            </CardContent>
          </Card>

          {/* Step list / execution details */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Steps</CardTitle>
            </CardHeader>
            <CardContent>
              {run.step_runs.length === 0 ? (
                <p className="text-muted-foreground">No steps in this run.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Step Name</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Started</TableHead>
                      <TableHead>Completed</TableHead>
                      <TableHead>Duration</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {run.step_runs.map((sr) => (
                      <TableRow
                        key={sr.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => setSelectedStepId(sr.workflow_step_id)}
                      >
                        <TableCell className="font-mono text-sm">{sr.workflow_step_id}</TableCell>
                        <TableCell>
                          <Badge variant={getStatusVariant(sr.status)}>{sr.status}</Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          {sr.started_at ? new Date(sr.started_at).toLocaleString() : '—'}
                        </TableCell>
                        <TableCell className="text-sm">
                          {sr.completed_at ? new Date(sr.completed_at).toLocaleString() : '—'}
                        </TableCell>
                        <TableCell className="text-sm">
                          {sr.started_at && sr.completed_at
                            ? `${(
                                (new Date(sr.completed_at).getTime() -
                                  new Date(sr.started_at).getTime()) /
                                1000
                              ).toFixed(1)}s`
                            : '—'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Selected step info (will integrate drawer in Plan 05) */}
          {selectedStepId && (
            <div className="p-4 bg-muted rounded border">
              <p className="text-sm">
                Selected step: <strong>{selectedStepId}</strong>
                <br />
                <em className="text-muted-foreground">(Drawer will open here in Plan 05)</em>
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
