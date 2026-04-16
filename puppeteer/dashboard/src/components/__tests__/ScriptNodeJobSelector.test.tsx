import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScriptNodeJobSelector } from '../ScriptNodeJobSelector';

// Mock data
const mockJobs = [
  { id: '1', name: 'build' },
  { id: '2', name: 'deploy' },
  { id: '3', name: 'test' },
];

describe('ScriptNodeJobSelector', () => {
  it('Test 1: renders a "Select job" button when node.scheduled_job_id is null', () => {
    const onSelectJob = vi.fn();
    render(
      <ScriptNodeJobSelector
        nodeId="node-1"
        currentJobId={undefined}
        onSelectJob={onSelectJob}
      />
    );

    expect(screen.getByText(/Select job/i)).toBeInTheDocument();
  });

  it('Test 2: clicking trigger opens a popover/drawer with job search input', async () => {
    const user = userEvent.setup();
    const onSelectJob = vi.fn();
    render(
      <ScriptNodeJobSelector
        nodeId="node-1"
        currentJobId={undefined}
        onSelectJob={onSelectJob}
      />
    );

    const button = screen.getByText(/Select job/i);
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search|filter/i)).toBeInTheDocument();
    });
  });

  it('Test 3: typing in search input filters job list', async () => {
    const user = userEvent.setup();
    const onSelectJob = vi.fn();
    const { rerender } = render(
      <ScriptNodeJobSelector
        nodeId="node-1"
        currentJobId={undefined}
        onSelectJob={onSelectJob}
        availableJobs={mockJobs}
      />
    );

    const button = screen.getByText(/Select job/i);
    await user.click(button);

    const searchInput = await screen.findByPlaceholderText(/search|filter/i);
    await user.type(searchInput, 'build');

    // After typing, only 'build' should be visible
    await waitFor(() => {
      expect(screen.getByText('build')).toBeInTheDocument();
    });
  });

  it('Test 4: clicking a job in list calls onSelectJob with correct IDs', async () => {
    const user = userEvent.setup();
    const onSelectJob = vi.fn();
    render(
      <ScriptNodeJobSelector
        nodeId="node-1"
        currentJobId={undefined}
        onSelectJob={onSelectJob}
        availableJobs={mockJobs}
      />
    );

    const button = screen.getByText(/Select job/i);
    await user.click(button);

    const jobOption = await screen.findByText('build');
    await user.click(jobOption);

    expect(onSelectJob).toHaveBeenCalledWith('node-1', '1');
  });

  it('Test 5: selecting a job closes the popover', async () => {
    const user = userEvent.setup();
    const onSelectJob = vi.fn();
    render(
      <ScriptNodeJobSelector
        nodeId="node-1"
        currentJobId={undefined}
        onSelectJob={onSelectJob}
        availableJobs={mockJobs}
      />
    );

    const button = screen.getByText(/Select job/i);
    await user.click(button);

    const jobOption = await screen.findByText('build');
    await user.click(jobOption);

    await waitFor(() => {
      expect(screen.queryByPlaceholderText(/search|filter/i)).not.toBeInTheDocument();
    });
  });

  it('Test 6: if node has scheduled_job_id, shows current job name + "Change" link', () => {
    const onSelectJob = vi.fn();
    render(
      <ScriptNodeJobSelector
        nodeId="node-1"
        currentJobId="1"
        onSelectJob={onSelectJob}
        currentJobName="build"
      />
    );

    expect(screen.getByText(/build/)).toBeInTheDocument();
    expect(screen.getByText(/Change|Edit/i)).toBeInTheDocument();
  });

  it('Test 7: clicking "Change" re-opens selector to pick a different job', async () => {
    const user = userEvent.setup();
    const onSelectJob = vi.fn();
    render(
      <ScriptNodeJobSelector
        nodeId="node-1"
        currentJobId="1"
        onSelectJob={onSelectJob}
        currentJobName="build"
      />
    );

    const changeButton = screen.getByText(/Change|Edit/i);
    await user.click(changeButton);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search|filter/i)).toBeInTheDocument();
    });
  });

  it('Test 8: Escape key closes the popover without selecting', async () => {
    const user = userEvent.setup();
    const onSelectJob = vi.fn();
    render(
      <ScriptNodeJobSelector
        nodeId="node-1"
        currentJobId={undefined}
        onSelectJob={onSelectJob}
        availableJobs={mockJobs}
      />
    );

    const button = screen.getByText(/Select job/i);
    await user.click(button);

    const searchInput = await screen.findByPlaceholderText(/search|filter/i);
    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(screen.queryByPlaceholderText(/search|filter/i)).not.toBeInTheDocument();
    });

    expect(onSelectJob).not.toHaveBeenCalled();
  });
});
