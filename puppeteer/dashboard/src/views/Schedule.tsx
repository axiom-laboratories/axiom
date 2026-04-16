import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
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
import { Skeleton } from '@/components/ui/skeleton';
import { authenticatedFetch } from '@/auth';
import { getStatusVariant } from '@/utils/workflowStatusUtils';
import { Calendar } from 'lucide-react';

interface ScheduleEntry {
  id: string;
  type: 'JOB' | 'FLOW';
  name: string;
  next_run_time: string | null; // ISO datetime or null
  last_run_status: string | null;
}

interface ScheduleListResponse {
  entries: ScheduleEntry[];
  total: number;
}

export default function Schedule() {
  const navigate = useNavigate();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['schedule'],
    queryFn: async () => {
      const res = await authenticatedFetch('/api/schedule');
      if (!res.ok) throw new Error('Failed to fetch schedule');
      return res.json() as Promise<ScheduleListResponse>;
    },
    refetchInterval: 30000, // Auto-refresh every 30s
  });

  const handleRowClick = (entry: ScheduleEntry) => {
    if (entry.type === 'JOB') {
      navigate(`/job-definitions?edit=${entry.id}`);
    } else {
      navigate(`/workflows/${entry.id}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Calendar className="w-6 h-6" />
            <div>
              <CardTitle>Schedule</CardTitle>
              <CardDescription>Upcoming scheduled jobs and workflows</CardDescription>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Main Table Card */}
      <Card>
        <CardContent className="pt-6">
          {/* Loading State */}
          {isLoading && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">Type</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Next Run</TableHead>
                  <TableHead>Last Run Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Array(5)
                  .fill(0)
                  .map((_, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <Skeleton className="h-6 w-16 rounded" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-6 w-32 rounded" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-6 w-24 rounded" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-6 w-20 rounded" />
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          )}

          {/* Error State */}
          {error && (
            <div className="border border-destructive bg-destructive/10 rounded-lg p-4">
              <p className="text-destructive font-medium mb-2">
                Error: {error instanceof Error ? error.message : 'Failed to load schedule'}
              </p>
              <Button onClick={() => refetch()} variant="outline" size="sm">
                Retry
              </Button>
            </div>
          )}

          {/* Empty State */}
          {data && data.entries.length === 0 && !isLoading && (
            <div className="border border-dashed rounded-lg p-8 text-center">
              <p className="text-muted-foreground">No active schedules</p>
            </div>
          )}

          {/* Table */}
          {data && data.entries.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">Type</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Next Run</TableHead>
                  <TableHead>Last Run Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.entries.map((entry) => (
                  <TableRow
                    key={`${entry.type}-${entry.id}`}
                    onClick={() => handleRowClick(entry)}
                    className="cursor-pointer hover:bg-muted/50"
                  >
                    <TableCell>
                      <Badge
                        variant={entry.type === 'JOB' ? 'secondary' : 'default'}
                      >
                        {entry.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{entry.name}</TableCell>
                    <TableCell>
                      {entry.next_run_time
                        ? formatDistanceToNow(new Date(entry.next_run_time), {
                          addSuffix: true,
                        })
                        : '—'}
                    </TableCell>
                    <TableCell>
                      {entry.last_run_status ? (
                        <Badge variant={getStatusVariant(entry.last_run_status)}>
                          {entry.last_run_status}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground text-sm">Never</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
