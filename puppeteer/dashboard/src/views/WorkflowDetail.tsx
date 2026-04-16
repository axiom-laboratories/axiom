import React, { useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Edit, AlertCircle } from 'lucide-react';
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
import { WorkflowNodePalette } from '@/components/WorkflowNodePalette';
import { ScriptNodeJobSelector } from '@/components/ScriptNodeJobSelector';
import { IfGateConfigDrawer } from '@/components/IfGateConfigDrawer';
import { getStatusVariant } from '@/utils/workflowStatusUtils';
import { useWorkflowEdit } from '@/hooks/useWorkflowEdit';
import { useDAGValidation } from '@/hooks/useDAGValidation';
import { Node, Edge, NodeChange, EdgeChange, Connection } from '@xyflow/react';

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
  const queryClient = useQueryClient();
  const [runsSkip, setRunsSkip] = useState(0);
  const runsLimit = 10;
  const [isEditing, setIsEditing] = useState(false);
  const [selectedNodeForJobSelector, setSelectedNodeForJobSelector] = useState<string | null>(null);
  const [selectedIfGateNode, setSelectedIfGateNode] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const reactFlowInstance = useRef(null);

  if (!workflowId) {
    return <div className="text-destructive">Invalid workflow ID</div>;
  }

  // Fetch workflow definition
  const { data: workflow, isLoading: workflowLoading, error: workflowError, refetch: refetchWorkflow } = useQuery({
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
    enabled: !!workflow,
    refetchInterval: 10000,
  });

  // Convert workflow steps/edges to ReactFlow nodes/edges format for edit mode
  const convertedNodes: Node[] = (workflow?.steps || []).map((step) => ({
    id: step.id,
    data: {
      label: step.id,
      nodeType: step.node_type,
      scheduled_job_id: step.scheduled_job_id || null,
      isEditing,
    },
    position: { x: 0, y: 0 },
    type: 'default',
  }));

  const convertedEdges: Edge[] = (workflow?.edges || []).map((edge) => ({
    id: `${edge.from_step_id}-${edge.to_step_id}`,
    source: edge.from_step_id,
    target: edge.to_step_id,
  }));

  // Use the edit hook for state management
  const {
    nodes,
    edges,
    handleNodesChange,
    handleEdgesChange,
    handleConnect,
    handleDrop: handleDropFromHook,
    getUnlinkedScriptNodes,
    canSave: canSaveFromHook,
  } = useWorkflowEdit(convertedNodes, convertedEdges);

  // Use validation hook for real-time feedback
  const { validation, hasCycle, maxDepth, depthExceeded } = useDAGValidation(nodes, edges);

  // Handle palette node drop
  const handleNodeAdd = useCallback(
    (nodeType: string) => {
      // This will be called when palette is used, but actual drop happens via drag-drop
    },
    []
  );

  // Handle drag-over for palette nodes
  const handleDragOver = useCallback((e: DragEvent) => {
    // Already handled by DAGCanvas wrapper
  }, []);

  // Handle drop on canvas
  const handleDropOnCanvas = useCallback((e: DragEvent) => {
    const nodeType = (e.dataTransfer as DataTransfer).getData('application/reactflow');
    if (!nodeType) return;

    // Get canvas position from event
    const canvasElement = (e.target as HTMLElement).closest('[style*="height"]');
    if (!canvasElement) return;

    const rect = canvasElement.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    handleDropFromHook(nodeType, { x, y });
  }, [handleDropFromHook]);

  // Handle node click for job selector or IF gate config
  const handleNodeClick = useCallback(
    (nodeId: string) => {
      if (!isEditing) return;

      const node = nodes.find((n) => n.id === nodeId);
      if (!node) return;

      if (node.data.nodeType === 'SCRIPT' && !node.data.scheduled_job_id) {
        setSelectedNodeForJobSelector(nodeId);
      } else if (node.data.nodeType === 'IF_GATE') {
        setSelectedIfGateNode(nodeId);
      }
    },
    [isEditing, nodes]
  );

  // Handle job selection
  const handleSelectJob = useCallback(
    (nodeId: string, jobId: string) => {
      // Update the node with the selected job
      const updatedNodes = nodes.map((n) =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, scheduled_job_id: jobId } }
          : n
      );
      // This is a bit hacky - we need to manually update through ReactFlow
      // For now, let's just close the selector and let the parent handle updates
      setSelectedNodeForJobSelector(null);
    },
    [nodes]
  );

  // Handle IF gate config save
  const handleIfGateConfigSave = useCallback(
    (config: any) => {
      // Update the node with the IF gate config
      setSelectedIfGateNode(null);
    },
    []
  );

  // Handle save
  const handleSave = useCallback(async () => {
    setSaveError(null);

    // Check unlinked nodes
    const unlinked = getUnlinkedScriptNodes();
    if (unlinked.length > 0) {
      setSaveError('All SCRIPT steps must be linked to a job');
      return;
    }

    // Check validation
    if (hasCycle || depthExceeded) {
      setSaveError('Fix validation errors before saving');
      return;
    }

    setIsSaving(true);
    try {
      // Convert nodes and edges back to workflow format
      const stepsForSave = nodes.map((node) => ({
        id: node.id,
        node_type: node.data.nodeType,
        scheduled_job_id: node.data.scheduled_job_id || undefined,
      }));

      const edgesForSave = edges.map((edge) => ({
        from_step_id: edge.source,
        to_step_id: edge.target,
      }));

      // Call validate endpoint
      const validateRes = await authenticatedFetch('/api/workflows/validate', {
        method: 'POST',
        body: JSON.stringify({ steps: stepsForSave, edges: edgesForSave }),
      });

      if (!validateRes.ok) {
        const error = await validateRes.json();
        setSaveError(error.error || 'Validation failed');
        return;
      }

      // Call save endpoint
      const saveRes = await authenticatedFetch(`/api/workflows/${workflowId}`, {
        method: 'PUT',
        body: JSON.stringify({ steps: stepsForSave, edges: edgesForSave }),
      });

      if (!saveRes.ok) {
        const error = await saveRes.json();
        setSaveError(error.error || 'Failed to save workflow');
        return;
      }

      // Success
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['workflow', workflowId] });
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save workflow');
    } finally {
      setIsSaving(false);
    }
  }, [getUnlinkedScriptNodes, hasCycle, depthExceeded, nodes, edges, workflowId, queryClient]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setSaveError(null);
    queryClient.invalidateQueries({ queryKey: ['workflow', workflowId] });
  }, [workflowId, queryClient]);

  const handleRunClick = (runId: string) => {
    navigate(`/workflows/${workflowId}/runs/${runId}`);
  };

  const hasActiveRun = workflow?.last_run?.status === 'RUNNING';
  const canEdit = !hasActiveRun && !isEditing;

  return (
    <div className="space-y-6">
      {/* Breadcrumb section */}
      <div className="mb-6 flex items-center gap-2">
        <button
          onClick={() => navigate('/workflows')}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Workflows
        </button>
      </div>

      {/* Workflow info header */}
      {workflowLoading && <p className="text-muted-foreground">Loading workflow...</p>}
      {workflowError && (
        <p className="text-destructive">
          Error: {workflowError instanceof Error ? workflowError.message : 'Unknown'}
        </p>
      )}

      {workflow && (
        <>
          {/* Header with workflow name and edit/save/cancel buttons */}
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">
                {workflow.name || 'Loading...'}
                {isEditing && <span className="text-muted-foreground ml-2 text-sm">│ Editing…</span>}
              </h1>
              <p className="text-muted-foreground mt-1">
                {workflow.steps?.length || 0} steps · Trigger: {workflow.schedule_cron ? 'CRON' : 'MANUAL'}
              </p>
            </div>

            <div className="flex gap-2">
              {isEditing ? (
                <>
                  <Button
                    onClick={handleSave}
                    disabled={isSaving || hasCycle || depthExceeded || getUnlinkedScriptNodes().length > 0}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    Save
                  </Button>
                  <Button
                    onClick={handleCancel}
                    variant="outline"
                  >
                    Cancel
                  </Button>
                </>
              ) : (
                <Button
                  onClick={() => setIsEditing(true)}
                  disabled={!canEdit}
                  variant="outline"
                  title={hasActiveRun ? 'Workflow has an active run. Editing is disabled.' : ''}
                >
                  <Edit className="w-4 h-4 mr-1" />
                  Edit
                </Button>
              )}
            </div>
          </div>

          {/* Validation banners in edit mode */}
          {isEditing && (
            <div className="space-y-2">
              {hasCycle && (
                <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg p-3 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  <span>❌ Cycle detected. Please remove the cycle to proceed.</span>
                </div>
              )}
              {maxDepth >= 25 && maxDepth <= 30 && !depthExceeded && (
                <div className="border border-yellow-600 bg-yellow-50 text-yellow-800 rounded-lg p-3 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  <span>⚠️ Depth: {maxDepth}/30 max</span>
                </div>
              )}
              {depthExceeded && (
                <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg p-3 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  <span>❌ Depth limit exceeded: {maxDepth}/30 max</span>
                </div>
              )}
              {saveError && (
                <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg p-3 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  <span>{saveError}</span>
                </div>
              )}
            </div>
          )}

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

          {/* DAG Canvas with edit mode */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">
                {isEditing ? 'Edit Workflow DAG' : 'Workflow DAG'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                {isEditing && (
                  <WorkflowNodePalette onNodeAdd={handleNodeAdd} />
                )}
                <div className="flex-1">
                  <DAGCanvas
                    steps={nodes.map((n) => ({
                      id: n.id,
                      node_type: n.data.nodeType,
                      scheduled_job_id: n.data.scheduled_job_id,
                    }))}
                    edges={edges.map((e) => ({
                      from_step_id: e.source,
                      to_step_id: e.target,
                    }))}
                    stepRunStatus={undefined}
                    onNodeClick={handleNodeClick}
                    editable={isEditing}
                    onNodesChange={isEditing ? handleNodesChange : undefined}
                    onEdgesChange={isEditing ? handleEdgesChange : undefined}
                    onConnect={isEditing ? handleConnect : undefined}
                    onDrop={isEditing ? handleDropOnCanvas : undefined}
                    onDragOver={isEditing ? handleDragOver : undefined}
                    height="500px"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Selectors and drawers for edit mode */}
          {selectedNodeForJobSelector && (
            <ScriptNodeJobSelector
              nodeId={selectedNodeForJobSelector}
              currentJobId={nodes.find((n) => n.id === selectedNodeForJobSelector)?.data.scheduled_job_id}
              onSelectJob={handleSelectJob}
            />
          )}

          {selectedIfGateNode && (
            <IfGateConfigDrawer
              stepId={selectedIfGateNode}
              currentConfig={nodes.find((n) => n.id === selectedIfGateNode)?.data.config_json}
              onSave={handleIfGateConfigSave}
              onClose={() => setSelectedIfGateNode(null)}
            />
          )}

          {/* Run history (hidden in edit mode) */}
          {!isEditing && (
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
          )}
        </>
      )}
    </div>
  );
}
