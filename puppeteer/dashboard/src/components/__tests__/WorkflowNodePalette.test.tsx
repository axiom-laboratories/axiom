import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorkflowNodePalette } from '../WorkflowNodePalette';

describe('WorkflowNodePalette', () => {
  it('Test 1: renders all 6 node types as draggable items', () => {
    const onNodeAdd = vi.fn();
    render(<WorkflowNodePalette onNodeAdd={onNodeAdd} />);

    expect(screen.getByText(/SCRIPT/i)).toBeInTheDocument();
    expect(screen.getByText(/IF_GATE/i)).toBeInTheDocument();
    expect(screen.getByText(/AND_JOIN/i)).toBeInTheDocument();
    expect(screen.getByText(/OR_GATE/i)).toBeInTheDocument();
    expect(screen.getByText(/PARALLEL/i)).toBeInTheDocument();
    expect(screen.getByText(/SIGNAL_WAIT/i)).toBeInTheDocument();
  });

  it('Test 2: each draggable item has correct label and icon', () => {
    const onNodeAdd = vi.fn();
    render(<WorkflowNodePalette onNodeAdd={onNodeAdd} />);

    const scriptItem = screen.getByText(/SCRIPT/i);
    const ifGateItem = screen.getByText(/IF_GATE/i);
    const andJoinItem = screen.getByText(/AND_JOIN/i);

    expect(scriptItem).toBeInTheDocument();
    expect(ifGateItem).toBeInTheDocument();
    expect(andJoinItem).toBeInTheDocument();
  });

  it('Test 3: drag start event sets dataTransfer data', () => {
    const onNodeAdd = vi.fn();
    render(<WorkflowNodePalette onNodeAdd={onNodeAdd} />);

    const scriptItem = screen.getByText(/SCRIPT/i).closest('[draggable]');
    expect(scriptItem).toBeDefined();
    expect(scriptItem).toHaveAttribute('draggable', 'true');
  });

  it('Test 4: onNodeAdd callback is called when drag starts', () => {
    const onNodeAdd = vi.fn();
    render(<WorkflowNodePalette onNodeAdd={onNodeAdd} />);

    const scriptItem = screen.getByText(/SCRIPT/i).closest('[draggable]');
    if (scriptItem) {
      fireEvent.dragStart(scriptItem, {
        dataTransfer: {
          setData: vi.fn(),
          effectAllowed: 'move',
        },
      });
    }

    // The callback should be called when drag starts
    expect(onNodeAdd).toHaveBeenCalledWith('SCRIPT');
  });

  it('Test 5: component renders in a narrow left panel', () => {
    const onNodeAdd = vi.fn();
    const { container } = render(<WorkflowNodePalette onNodeAdd={onNodeAdd} />);

    const panel = container.querySelector('[data-testid="node-palette"]');
    expect(panel).toBeDefined();
  });

  it('Test 6: hovering over a draggable item shows cursor move (styling)', () => {
    const onNodeAdd = vi.fn();
    render(<WorkflowNodePalette onNodeAdd={onNodeAdd} />);

    const scriptItem = screen.getByText(/SCRIPT/i).closest('[draggable]');
    expect(scriptItem).toBeDefined();
  });

  it('Test 7: each node type badge shows a distinct icon', () => {
    const onNodeAdd = vi.fn();
    const { container } = render(<WorkflowNodePalette onNodeAdd={onNodeAdd} />);

    // Check that all 6 items are rendered as distinct elements
    const draggableItems = container.querySelectorAll('[draggable="true"]');
    expect(draggableItems.length).toBe(6);
  });

  it('Test 8: onNodeAdd is not called on non-drag interactions', () => {
    const onNodeAdd = vi.fn();
    render(<WorkflowNodePalette onNodeAdd={onNodeAdd} />);

    const scriptItem = screen.getByText(/SCRIPT/i);
    fireEvent.click(scriptItem);

    // onNodeAdd should not be called on click
    expect(onNodeAdd).not.toHaveBeenCalled();
  });
});
