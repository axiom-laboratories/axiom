import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWorkflowEdit } from '../useWorkflowEdit';

interface Node {
  id: string;
  data: { label: string; scheduled_job_id?: string };
  position: { x: number; y: number };
  type: string;
}

interface Edge {
  id: string;
  source: string;
  target: string;
}

describe('useWorkflowEdit Hook', () => {
  const initialNodes: Node[] = [
    { id: 'A', data: { label: 'Script A', scheduled_job_id: 'job1' }, position: { x: 0, y: 0 }, type: 'SCRIPT' },
    { id: 'B', data: { label: 'Script B' }, position: { x: 100, y: 100 }, type: 'SCRIPT' },
  ];

  const initialEdges: Edge[] = [
    { id: 'e1', source: 'A', target: 'B' },
  ];

  it('Test 1: initializes with nodes, edges, isEditing=false', () => {
    const { result } = renderHook(() => useWorkflowEdit(initialNodes, initialEdges));

    expect(result.current.nodes).toEqual(initialNodes);
    expect(result.current.edges).toEqual(initialEdges);
    expect(result.current.isEditing).toBe(false);
  });

  it('Test 2: setIsEditing toggles editing mode', () => {
    const { result } = renderHook(() => useWorkflowEdit(initialNodes, initialEdges));

    expect(result.current.isEditing).toBe(false);

    act(() => {
      result.current.setIsEditing(true);
    });

    expect(result.current.isEditing).toBe(true);

    act(() => {
      result.current.setIsEditing(false);
    });

    expect(result.current.isEditing).toBe(false);
  });

  it('Test 3: handleNodesChange updates nodes array', () => {
    const { result } = renderHook(() => useWorkflowEdit(initialNodes, initialEdges));

    act(() => {
      result.current.handleNodesChange([
        {
          type: 'position',
          id: 'A',
          position: { x: 50, y: 50 },
        } as any,
      ]);
    });

    const nodeA = result.current.nodes.find(n => n.id === 'A');
    expect(nodeA?.position).toEqual({ x: 50, y: 50 });
  });

  it('Test 4: handleEdgesChange updates edges array', () => {
    const { result } = renderHook(() => useWorkflowEdit(initialNodes, initialEdges));

    act(() => {
      result.current.handleEdgesChange([
        {
          type: 'select',
          id: 'e1',
          selected: true,
        } as any,
      ]);
    });

    const edge = result.current.edges.find(e => e.id === 'e1');
    expect(edge?.selected).toBe(true);
  });

  it('Test 5: handleConnect creates new edge between two nodes', () => {
    const { result } = renderHook(() => useWorkflowEdit(initialNodes, initialEdges));

    act(() => {
      result.current.handleConnect({ source: 'B', target: 'A' } as any);
    });

    const newEdge = result.current.edges.find(e => e.source === 'B' && e.target === 'A');
    expect(newEdge).toBeDefined();
    expect(newEdge?.id).toMatch(/^e\d+$/);
  });

  it('Test 6: handleDrop adds a new node at dropped position', () => {
    const { result } = renderHook(() => useWorkflowEdit(initialNodes, initialEdges));

    const initialLength = result.current.nodes.length;

    act(() => {
      result.current.handleDrop({
        type: 'SCRIPT',
        nodeId: 'new-node',
        position: { x: 200, y: 200 },
      });
    });

    expect(result.current.nodes.length).toBe(initialLength + 1);
    const newNode = result.current.nodes.find(n => n.id === 'new-node');
    expect(newNode?.type).toBe('SCRIPT');
    expect(newNode?.position).toEqual({ x: 200, y: 200 });
  });

  it('Test 7: getUnlinkedScriptNodes returns SCRIPT nodes without scheduled_job_id', () => {
    const { result } = renderHook(() => useWorkflowEdit(initialNodes, initialEdges));

    const unlinked = result.current.getUnlinkedScriptNodes();

    expect(unlinked.length).toBe(1);
    expect(unlinked[0].id).toBe('B');
    expect(unlinked[0].data.scheduled_job_id).toBeUndefined();
  });

  it('Test 8: getUnlinkedScriptNodes returns empty if all SCRIPT nodes have scheduled_job_id', () => {
    const linkedNodes: Node[] = [
      { id: 'A', data: { label: 'Script A', scheduled_job_id: 'job1' }, position: { x: 0, y: 0 }, type: 'SCRIPT' },
      { id: 'B', data: { label: 'Script B', scheduled_job_id: 'job2' }, position: { x: 100, y: 100 }, type: 'SCRIPT' },
    ];

    const { result } = renderHook(() => useWorkflowEdit(linkedNodes, initialEdges));

    const unlinked = result.current.getUnlinkedScriptNodes();
    expect(unlinked.length).toBe(0);
  });

  it('Test 9: canSave returns false if unlinked SCRIPT nodes exist', () => {
    const { result } = renderHook(() => useWorkflowEdit(initialNodes, initialEdges));

    expect(result.current.canSave()).toBe(false);
  });

  it('Test 10: canSave returns true if all SCRIPT nodes have scheduled_job_id', () => {
    const linkedNodes: Node[] = [
      { id: 'A', data: { label: 'Script A', scheduled_job_id: 'job1' }, position: { x: 0, y: 0 }, type: 'SCRIPT' },
      { id: 'B', data: { label: 'Script B', scheduled_job_id: 'job2' }, position: { x: 100, y: 100 }, type: 'SCRIPT' },
    ];
    const edges: Edge[] = [
      { id: 'e1', source: 'A', target: 'B' },
    ];

    const { result } = renderHook(() => useWorkflowEdit(linkedNodes, edges));

    expect(result.current.canSave()).toBe(true);
  });
});
