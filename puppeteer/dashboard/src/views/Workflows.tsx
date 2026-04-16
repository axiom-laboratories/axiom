import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { authenticatedFetch } from '@/auth';
import { getStatusVariant } from '@/utils/workflowStatusUtils';

interface WorkflowResponse {
  id: string;
  name: string;
  steps: Array<{ id: string; node_type: string }>;
  edges: Array<{ from_step_id: string; to_step_id: string }>;
  schedule_cron?: string;
  last_run?: {
    id: string;
    workflow_id: string;
    status: 'RUNNING' | 'COMPLETED' | 'PARTIAL' | 'FAILED' | 'CANCELLED';
    started_at: string;
    completed_at?: string;
    step_runs: Array<{ id: string }>;
  };
}

interface WorkflowListResponse {
  workflows: WorkflowResponse[];
  total: number;
}

export function Workflows() {
  const navigate = useNavigate();
  const [skip, setSkip] = useState(0);
  const limit = 25;

  const { data, isLoading, error } = useQuery({
    queryKey: ['workflows', skip, limit],
    queryFn: async () => {
      const res = await authenticatedFetch(
        `/api/workflows?skip=${skip}&limit=${limit}`
      );
      if (!res.ok) throw new Error('Failed to fetch workflows');
      return res.json() as Promise<WorkflowListResponse>;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const handleRowClick = (workflowId: string) => {
    navigate(`/workflows/${workflowId}`);
  };

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Workflows</h1>
        <p className="text-muted-foreground mt-2">Manage and monitor your workflow definitions</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Workflows</CardTitle>
          <CardDescription>
            {data?.total ? `${data.total} workflow(s)` : 'Loading...'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-muted-foreground">Loading workflows...</p>}
          {error && (
            <p className="text-destructive">
              Error: {error instanceof Error ? error.message : 'Unknown error'}
            </p>
          )}
          {data && data.workflows.length === 0 && (
            <p className="text-muted-foreground">No workflows found.</p>
          )}
          {data && data.workflows.length > 0 && (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="text-right">Steps</TableHead>
                    <TableHead>Last Run Status</TableHead>
                    <TableHead>Last Run Time</TableHead>
                    <TableHead>Trigger Type</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.workflows.map((workflow) => (
                    <TableRow
                      key={workflow.id}
                      onClick={() => handleRowClick(workflow.id)}
                      className="cursor-pointer hover:bg-muted/50"
                    >
                      <TableCell className="font-medium">{workflow.name}</TableCell>
                      <TableCell className="text-right">{workflow.steps.length}</TableCell>
                      <TableCell>
                        {workflow.last_run ? (
                          <Badge variant={getStatusVariant(workflow.last_run.status)}>
                            {workflow.last_run.status}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground text-sm">Never</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {workflow.last_run
                          ? new Date(workflow.last_run.started_at).toLocaleString()
                          : '—'}
                      </TableCell>
                      <TableCell>
                        {workflow.schedule_cron ? 'CRON' : 'MANUAL'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination controls */}
              <div className="flex justify-between items-center mt-6">
                <p className="text-sm text-muted-foreground">
                  Showing {skip + 1}–{Math.min(skip + limit, data.total)} of {data.total}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setSkip(Math.max(0, skip - limit))}
                    disabled={skip === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      if (skip + limit < data.total) {
                        setSkip(skip + limit);
                      }
                    }}
                    disabled={skip + limit >= data.total}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
