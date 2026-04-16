import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { authenticatedFetch } from '@/auth';
import DAGCanvas from '@/components/DAGCanvas';
import { getStatusVariant } from '@/utils/workflowStatusUtils';

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
}

interface WorkflowRunListResponse {
  runs: WorkflowRunResponse[];
  total: number;
  skip: number;
  limit: number;
}

interface WorkflowResponse {
  id: string;
  name: string;
  steps: WorkflowStepResponse[];
  edges: WorkflowEdgeResponse[];
  schedule_cron?: string;
  last_run?: WorkflowRunResponse;
}

export function WorkflowDetail() {
  const { id: workflowId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [runsSkip, setRunsSkip] = useState(0);
  const runsLimit = 10;

  if (!workflowId) {
    return <div className="text-destructive">Invalid workflow ID</div>;
  }

  // Fetch workflow definition
  const { data: workflow, isLoading: workflowLoading, error: workflowError } = useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: async () => {
      const res = await authenticatedFetch(`/api/workflows/${workflowId}`);
      if (!res.ok) throw new Error('Failed to fetch workflow');
      return res.json() as Promise<WorkflowResponse>;
    },
    refetchInterval: 30000,
  });

  // Fetch run history
  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ['workflow-runs', workflowId, runsSkip, runsLimit],
    queryFn: async () => {
      const res = await authenticatedFetch(
        `/api/workflows/${workflowId}/runs?skip=${runsSkip}&limit=${runsLimit}`
      );
      if (!res.ok) throw new Error('Failed to fetch runs');
      return res.json() as Promise<WorkflowRunListResponse>;
    },
    enabled: !!workflow, // Only fetch runs after workflow is loaded
    refetchInterval: 10000, // More frequent updates for active runs
  });

  const handleRunClick = (runId: string) => {
    navigate(`/workflows/${workflowId}/runs/${runId}`);
  };

  return (
    <div className="space-y-6">
      {/* Workflow info header */}
      {workflowLoading && <p className="text-muted-foreground">Loading workflow...</p>}
      {workflowError && (
        <p className="text-destructive">
          Error: {workflowError instanceof Error ? workflowError.message : 'Unknown'}
        </p>
      )}

      {workflow && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{workflow.name}</span>
                {workflow.schedule_cron && (
                  <Badge variant="outline">{workflow.schedule_cron}</Badge>
                )}
              </CardTitle>
            </CardHeader>
          </Card>

          {/* DAG Canvas */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Workflow DAG</CardTitle>
            </CardHeader>
            <CardContent>
              <DAGCanvas
                steps={workflow.steps}
                edges={workflow.edges}
                stepRunStatus={undefined} // No live status on workflow definition view
                height="400px"
              />
            </CardContent>
          </Card>

          {/* Run history */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Run History</CardTitle>
            </CardHeader>
            <CardContent>
              {runsLoading && <p className="text-muted-foreground">Loading runs...</p>}
              {runsData && runsData.runs.length === 0 && (
                <p className="text-muted-foreground">No runs yet.</p>
              )}
              {runsData && runsData.runs.length > 0 && (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Started</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Duration</TableHead>
                        <TableHead>Trigger</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {runsData.runs.map((run) => (
                        <TableRow
                          key={run.id}
                          onClick={() => handleRunClick(run.id)}
                          className="cursor-pointer hover:bg-muted/50"
                        >
                          <TableCell className="text-sm">
                            {new Date(run.started_at).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <Badge variant={getStatusVariant(run.status)}>
                              {run.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm">
                            {run.completed_at
                              ? `${(
                                  (new Date(run.completed_at).getTime() -
                                    new Date(run.started_at).getTime()) /
                                  1000
                                ).toFixed(1)}s`
                              : '—'}
                          </TableCell>
                          <TableCell className="text-sm">MANUAL</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* Run pagination */}
                  <div className="flex justify-between items-center mt-4">
                    <p className="text-sm text-muted-foreground">
                      Showing {runsSkip + 1}–{Math.min(runsSkip + runsLimit, runsData.total)} of{' '}
                      {runsData.total}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setRunsSkip(Math.max(0, runsSkip - runsLimit))}
                        disabled={runsSkip === 0}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          if (runsSkip + runsLimit < runsData.total) {
                            setRunsSkip(runsSkip + runsLimit);
                          }
                        }}
                        disabled={runsSkip + runsLimit >= runsData.total}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
