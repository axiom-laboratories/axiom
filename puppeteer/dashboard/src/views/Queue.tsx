import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { subHours, formatDistanceToNow } from 'date-fns';
import {
    ListOrdered,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Timer,
    RefreshCw,
    Skull,
    Lock,
    Ban,
    ShieldAlert,
    Clock,
    Activity,
    ArrowRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { authenticatedFetch } from '../auth';
import { useWebSocket } from '../hooks/useWebSocket';

// ─── Types ────────────────────────────────────────────────────────────────────

interface QueueJob {
    guid: string;
    name?: string;
    status: string;
    task_type?: string;
    display_type?: string;
    node_id?: string;
    target_tags?: string[];
    created_at?: string;
    runtime?: string;
}

interface QueueNode {
    node_id: string;
    hostname?: string;
    status: string;
    tags?: string[];
}

interface PaginatedJobResponse {
    items: QueueJob[];
    total: number;
    next_cursor: string | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const getStatusVariant = (status: string) => {
    switch (status.toLowerCase()) {
        case 'completed': return 'success';
        case 'failed': return 'destructive';
        case 'cancelled': return 'destructive';
        case 'security_rejected': return 'destructive';
        case 'assigned': return 'secondary';
        case 'blocked': return 'outline';
        case 'pending': return 'outline';
        case 'running': return 'secondary';
        case 'retrying': return 'warning';
        case 'dead_letter': return 'deadletter';
        default: return 'outline';
    }
};

const StatusIcon = ({ status }: { status: string }) => {
    switch (status.toLowerCase()) {
        case 'completed': return <CheckCircle2 className="h-4 w-4 text-green-500" />;
        case 'failed': return <XCircle className="h-4 w-4 text-red-500" />;
        case 'security_rejected': return <ShieldAlert className="h-4 w-4 text-orange-500" />;
        case 'assigned': return <Timer className="h-4 w-4 text-yellow-500 animate-pulse" />;
        case 'running': return <Activity className="h-4 w-4 text-blue-400 animate-pulse" />;
        case 'retrying': return <RefreshCw className="h-4 w-4 text-amber-500 animate-spin" />;
        case 'dead_letter': return <Skull className="h-4 w-4 text-rose-800" />;
        case 'blocked': return <Lock className="h-4 w-4 text-zinc-500" />;
        case 'cancelled': return <Ban className="h-4 w-4 text-zinc-600" />;
        default: return <Clock className="h-4 w-4 text-zinc-500" />;
    }
};

const truncateGuid = (guid: string) => `${guid.slice(0, 8)}…`;

const formatRelative = (ts?: string) => {
    if (!ts) return '—';
    try {
        return formatDistanceToNow(new Date(ts), { addSuffix: true });
    } catch {
        return ts;
    }
};

async function fetchJobs(params: Record<string, string>): Promise<PaginatedJobResponse> {
    const qs = new URLSearchParams(params).toString();
    const res = await authenticatedFetch(`/api/jobs?${qs}`);
    if (!res.ok) throw new Error('Failed to fetch jobs');
    const json = await res.json();
    // Handle both paginated envelope and bare array (backwards compat)
    if (Array.isArray(json)) {
        return { items: json, total: json.length, next_cursor: null };
    }
    return json as PaginatedJobResponse;
}

async function fetchNodes(): Promise<QueueNode[]> {
    const res = await authenticatedFetch('/api/nodes');
    if (!res.ok) throw new Error('Failed to fetch nodes');
    const json = await res.json();
    const items: QueueNode[] = Array.isArray(json) ? json : (json.items ?? []);
    return items;
}

// ─── Queue Row ────────────────────────────────────────────────────────────────

const QueueRow = ({
    job,
    drainingNodeIds,
}: {
    job: QueueJob;
    drainingNodeIds: Set<string>;
}) => {
    // A PENDING job is affected by draining if any of its target_tags match a draining node_id
    // or if its node_id is a draining node
    const isPendingAffected =
        job.status === 'PENDING' &&
        (job.target_tags ?? []).some((tag) => drainingNodeIds.has(tag));

    return (
        <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
            <TableCell>
                <div className="flex items-center gap-2">
                    <StatusIcon status={job.status} />
                    <Badge variant={getStatusVariant(job.status) as any} className="uppercase text-xs font-mono">
                        {job.status}
                    </Badge>
                    {isPendingAffected && (
                        <Badge variant="warning" className="text-xs">
                            Node Draining
                        </Badge>
                    )}
                </div>
            </TableCell>
            <TableCell className="font-mono text-xs text-zinc-300">
                <div className="max-w-[180px] truncate" title={job.guid}>
                    {job.name ? (
                        <span className="text-white font-medium">{job.name}</span>
                    ) : (
                        <span className="text-zinc-400">{truncateGuid(job.guid)}</span>
                    )}
                </div>
                <div className="text-zinc-600 text-xs mt-0.5">{truncateGuid(job.guid)}</div>
            </TableCell>
            <TableCell className="text-zinc-400 text-xs">
                <span className="font-mono">
                    {job.display_type ?? job.task_type ?? '—'}
                </span>
                {job.runtime && (
                    <span className="ml-1 text-zinc-600">({job.runtime})</span>
                )}
            </TableCell>
            <TableCell className="text-zinc-400 text-xs font-mono">
                {job.node_id ? (
                    <span className="truncate max-w-[120px] block" title={job.node_id}>
                        {job.node_id.slice(0, 12)}…
                    </span>
                ) : (
                    <span className="text-zinc-700">—</span>
                )}
            </TableCell>
            <TableCell className="text-zinc-500 text-xs">
                {formatRelative((job as any).created_at)}
            </TableCell>
        </TableRow>
    );
};

// ─── Queue View ───────────────────────────────────────────────────────────────

const Queue = () => {
    const queryClient = useQueryClient();
    const [recencyWindow, setRecencyWindow] = useState<1 | 6 | 24>(1);

    // Fetch active jobs: PENDING, ASSIGNED, RUNNING
    const { data: activeData, isLoading: activeLoading } = useQuery({
        queryKey: ['queue', 'active'],
        queryFn: () =>
            fetchJobs({
                status: 'PENDING,ASSIGNED,RUNNING',
                limit: '200',
            }),
    });

    // Fetch terminal jobs within recency window
    const { data: terminalData, isLoading: terminalLoading } = useQuery({
        queryKey: ['queue', 'terminal', recencyWindow],
        queryFn: () =>
            fetchJobs({
                status: 'COMPLETED,FAILED,CANCELLED,DEAD_LETTER,SECURITY_REJECTED',
                date_from: subHours(new Date(), recencyWindow).toISOString(),
                limit: '200',
            }),
    });

    // Fetch nodes to identify DRAINING ones
    const { data: nodes = [] } = useQuery({
        queryKey: ['queue', 'nodes'],
        queryFn: fetchNodes,
    });

    const drainingNodeIds = new Set(
        nodes
            .filter((n) => n.status === 'DRAINING')
            .map((n) => n.node_id)
    );

    // WebSocket: invalidate both queue queries on job or node events
    useWebSocket((event) => {
        if (
            event === 'job:created' ||
            event === 'job:updated' ||
            event === 'node:updated' ||
            event === 'node:heartbeat'
        ) {
            queryClient.invalidateQueries({ queryKey: ['queue'] });
        }
    });

    const activeJobs = activeData?.items ?? [];
    const terminalJobs = terminalData?.items ?? [];

    const recencyLabel = recencyWindow === 1 ? 'Last 1 hour' : `Last ${recencyWindow} hours`;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-3">
                        <div className="bg-primary/10 p-2 rounded-lg">
                            <ListOrdered className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold tracking-tight text-white">Queue</h1>
                            <p className="text-sm text-zinc-500 mt-0.5">
                                Live job queue — read-only monitoring view
                            </p>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-zinc-500">Terminal window:</span>
                        <Select
                            value={String(recencyWindow)}
                            onValueChange={(v) => setRecencyWindow(Number(v) as 1 | 6 | 24)}
                        >
                            <SelectTrigger className="w-28 bg-zinc-900 border-zinc-700 text-white text-sm">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="1">1 hour</SelectItem>
                                <SelectItem value="6">6 hours</SelectItem>
                                <SelectItem value="24">24 hours</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <Link
                        to="/jobs"
                        className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition-colors"
                    >
                        Manage jobs
                        <ArrowRight className="h-4 w-4" />
                    </Link>
                </div>
            </div>

            {/* Active Jobs Section */}
            <Card className="bg-zinc-950 border-zinc-800">
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
                            <Activity className="h-4 w-4 text-blue-400" />
                            Active
                            {!activeLoading && (
                                <span className="text-zinc-500 font-normal text-sm">
                                    ({activeJobs.length})
                                </span>
                            )}
                        </CardTitle>
                        {drainingNodeIds.size > 0 && (
                            <Badge variant="warning" className="text-xs">
                                {drainingNodeIds.size} node{drainingNodeIds.size > 1 ? 's' : ''} draining
                            </Badge>
                        )}
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    {activeLoading ? (
                        <div className="space-y-2 p-4">
                            {[...Array(3)].map((_, i) => (
                                <div key={i} className="h-10 rounded bg-zinc-900 animate-pulse" />
                            ))}
                        </div>
                    ) : activeJobs.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-zinc-600">
                            <CheckCircle2 className="h-8 w-8 mb-2 text-zinc-800" />
                            <p className="text-sm">No active jobs</p>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow className="border-zinc-800 hover:bg-transparent">
                                    <TableHead className="text-zinc-500 text-xs w-48">Status</TableHead>
                                    <TableHead className="text-zinc-500 text-xs">Job</TableHead>
                                    <TableHead className="text-zinc-500 text-xs">Task Type</TableHead>
                                    <TableHead className="text-zinc-500 text-xs">Node</TableHead>
                                    <TableHead className="text-zinc-500 text-xs">Created</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {activeJobs.map((job) => (
                                    <QueueRow
                                        key={job.guid}
                                        job={job}
                                        drainingNodeIds={drainingNodeIds}
                                    />
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            {/* Terminal Jobs Section */}
            <Card className="bg-zinc-950 border-zinc-800">
                <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
                        <Clock className="h-4 w-4 text-zinc-500" />
                        Recent
                        <span className="text-zinc-500 font-normal text-sm">— {recencyLabel}</span>
                        {!terminalLoading && (
                            <span className="text-zinc-500 font-normal text-sm">
                                ({terminalJobs.length})
                            </span>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {terminalLoading ? (
                        <div className="space-y-2 p-4">
                            {[...Array(4)].map((_, i) => (
                                <div key={i} className="h-10 rounded bg-zinc-900 animate-pulse" />
                            ))}
                        </div>
                    ) : terminalJobs.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-zinc-600">
                            <AlertTriangle className="h-8 w-8 mb-2 text-zinc-800" />
                            <p className="text-sm">No completed jobs in this window</p>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow className="border-zinc-800 hover:bg-transparent">
                                    <TableHead className="text-zinc-500 text-xs w-48">Status</TableHead>
                                    <TableHead className="text-zinc-500 text-xs">Job</TableHead>
                                    <TableHead className="text-zinc-500 text-xs">Task Type</TableHead>
                                    <TableHead className="text-zinc-500 text-xs">Node</TableHead>
                                    <TableHead className="text-zinc-500 text-xs">Created</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {terminalJobs.map((job) => (
                                    <QueueRow
                                        key={job.guid}
                                        job={job}
                                        drainingNodeIds={drainingNodeIds}
                                    />
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};

export default Queue;
