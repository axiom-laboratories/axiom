import React, { useState, useMemo } from 'react';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from './ui/dialog';
import { Input } from './ui/input';

export interface ScriptNodeJobSelectorProps {
  nodeId: string;
  currentJobId?: string;
  currentJobName?: string;
  onSelectJob: (nodeId: string, jobId: string) => void;
  availableJobs?: Array<{ id: string; name: string }>;
}

// Default mock jobs if none provided
const DEFAULT_JOBS = [
  { id: '1', name: 'build' },
  { id: '2', name: 'deploy' },
  { id: '3', name: 'test' },
];

export const ScriptNodeJobSelector: React.FC<ScriptNodeJobSelectorProps> = ({
  nodeId,
  currentJobId,
  currentJobName,
  onSelectJob,
  availableJobs = DEFAULT_JOBS,
}) => {
  const [open, setOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredJobs = useMemo(() => {
    if (!searchTerm) return availableJobs;
    return availableJobs.filter(job =>
      job.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [searchTerm, availableJobs]);

  const handleSelectJob = (jobId: string) => {
    onSelectJob(nodeId, jobId);
    setOpen(false);
    setSearchTerm('');
  };

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      setSearchTerm('');
    }
  };

  if (currentJobId) {
    // Show current job name with change link
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">{currentJobName || 'Job'}</span>
        <Dialog open={open} onOpenChange={handleOpenChange}>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOpen(true)}
          >
            Change
          </Button>

          <DialogContent>
            <DialogHeader>
              <DialogTitle>Change Job</DialogTitle>
            </DialogHeader>

            <div className="space-y-4">
              <Input
                placeholder="Search jobs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                autoFocus
              />

              <div className="max-h-64 overflow-y-auto space-y-1">
                {filteredJobs.map(job => (
                  <div
                    key={job.id}
                    onClick={() => handleSelectJob(job.id)}
                    className="p-2 cursor-pointer hover:bg-slate-100 rounded text-sm"
                  >
                    {job.name}
                  </div>
                ))}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // Show select button
  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
      >
        Select job
      </Button>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Select a Job</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <Input
            placeholder="Search jobs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            autoFocus
          />

          <div className="max-h-64 overflow-y-auto space-y-1">
            {filteredJobs.map(job => (
              <div
                key={job.id}
                onClick={() => handleSelectJob(job.id)}
                className="p-2 cursor-pointer hover:bg-slate-100 rounded text-sm"
              >
                {job.name}
              </div>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
