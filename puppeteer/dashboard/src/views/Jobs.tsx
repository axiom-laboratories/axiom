import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import {
    History,
    Terminal,
    Clock,
    Hash,
    MoreHorizontal,
    Search,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Timer,
    Ban,
    ShieldAlert,
    RefreshCw,
    Skull,
    Lock,
    Zap,
    SlidersHorizontal,
    X,
    Download,
    Pin,
    } from 'lucide-react';
import { toast } from 'sonner';
import { subHours, subDays } from 'date-fns';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from '@/components/ui/table';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Checkbox } from '@/components/ui/checkbox';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { authenticatedFetch } from '../auth';
import { useWebSocket } from '../hooks/useWebSocket';
import { ExecutionLogModal } from '../components/ExecutionLogModal';
import { GuidedDispatchCard } from '../components/GuidedDispatchCard';

// ─── Interfaces ──────────────────────────────────────────────────────────────

interface Job {
    guid: string;
    name?: string;
    status: string;
    task_type?: string;
    display_type?: string;
    payload: Record<string, any>;
    result?: Record<string, any>;
    node_id?: string;
    started_at?: string;
    duration_seconds?: number;
    target_tags?: string[];
    retry_count?: number;
    max_retries?: number;
    retry_after?: string | null;
    depends_on?: string[];
    created_by?: string;
    originating_guid?: string;
    runtime?: string;
}

interface DispatchDiagnosis {
    reason: 'no_nodes_online' | 'capability_mismatch' | 'all_nodes_busy' | 'target_node_unavailable' | 'pending_dispatch' | 'not_pending';
    message: string;
    queue_position?: number | null;
}

interface GuidedFormState {
    name: string;
    runtime: 'python' | 'bash' | 'powershell';
    scriptContent: string;
    targetNodeId: string;
    targetTags: string[];
    capabilityReqs: string[];
    signatureId: string;
    signature: string;
    signatureCleared: boolean;
}

interface PaginatedJobResponse {
    items: Job[];
    total: number;
    next_cursor: string | null;
}

interface NodeItem {
    node_id: string;
    hostname?: string;
    tags?: string[];
}

interface FilterState {
    search: string;
    status: string;
    runtime: string;
    taskType: string;
    nodeId: string;
    tags: string[];
    createdBy: string;
    dateFrom: string;
    dateTo: string;
    datePreset: string;
}

const EMPTY_FILTERS: FilterState = {
    search: '', status: 'all', runtime: 'all', taskType: 'all',
    nodeId: '', tags: [], createdBy: '', dateFrom: '', dateTo: '', datePreset: '',
};

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
        case 'retrying': return <RefreshCw className="h-4 w-4 text-amber-500 animate-spin" />;
        case 'dead_letter': return <Skull className="h-4 w-4 text-rose-800" />;
        case 'blocked': return <Lock className="h-4 w-4 text-zinc-500" />;
        case 'cancelled': return <Ban className="h-4 w-4 text-zinc-600" />;
        default: return <Clock className="h-4 w-4 text-zinc-500" />;
    }
};

// ─── JobDetailPanel ───────────────────────────────────────────────────────────

const JobDetailPanel = ({
    job,
    open,
    onClose,
    onCancel,
    onResubmit,
    onEditResubmit,
}: {
    job: Job | null;
    open: boolean;
    onClose: () => void;
    onCancel: (guid: string) => void;
    onResubmit: (guid: string) => void;
    onEditResubmit: (job: Job) => void;
}) => {
    const [retryCountdown, setRetryCountdown] = useState<string | null>(null);
    const [resubmitConfirming, setResubmitConfirming] = useState(false);
    const [executions, setExecutions] = useState<any[] | null>(null);
    const [nodeHealth, setNodeHealth] = useState<{ cpu: number; ram: number; recorded_at: string } | null>(null);
    const [execLoading, setExecLoading] = useState(false);
    const [diagnosis, setDiagnosis] = useState<DispatchDiagnosis | null>(null);
    const [diagnosisLoading, setDiagnosisLoading] = useState(false);
    const [exportingCsv, setExportingCsv] = useState(false);

    useEffect(() => {
        if (!job?.retry_after || job.status !== 'RETRYING') {
            setRetryCountdown(null);
            return;
        }
        const tick = () => {
            const diff = Math.max(0, new Date(job.retry_after!).getTime() - Date.now());
            if (diff === 0) { setRetryCountdown('Pending assignment...'); return; }
            const mins = Math.floor(diff / 60000);
            const secs = Math.floor((diff % 60000) / 1000);
            setRetryCountdown(`Next attempt in ${mins}m ${secs}s`);
        };
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, [job?.retry_after, job?.status]);

    useEffect(() => {
        if (!open) { setResubmitConfirming(false); return; }
    }, [open]);

    useEffect(() => {
        if (!open || !job) { setExecutions(null); setNodeHealth(null); return; }
        setExecLoading(true);
        authenticatedFetch(`/jobs/${job.guid}/executions`)
            .then(r => r.json())
            .then(data => {
                setExecutions(data.records ?? []);
                setNodeHealth(data.node_health_at_execution ?? null);
            })
            .catch(() => { /* non-critical — drawer still useful without output */ })
            .finally(() => setExecLoading(false));
    }, [open, job?.guid]);

    useEffect(() => {
        if (!open || !job || job.status !== 'PENDING') {
            setDiagnosis(null);
            return;
        }
        setDiagnosisLoading(true);
        authenticatedFetch(`/jobs/${job.guid}/dispatch-diagnosis`)
            .then(r => r.ok ? r.json() : null)
            .then(data => setDiagnosis(data))
            .catch(() => {})
            .finally(() => setDiagnosisLoading(false));
    }, [open, job?.guid, job?.status]);

    useWebSocket((event) => {
        if ((event === 'node:updated' || event === 'node:heartbeat' || event === 'job:updated')
            && open && job?.status === 'PENDING' && job?.guid) {
            authenticatedFetch(`/jobs/${job.guid}/dispatch-diagnosis`)
                .then(r => r.ok ? r.json() : null)
                .then(data => data && setDiagnosis(data))
                .catch(() => {});
        }
    });

    const handlePin = async (id: number, currentlyPinned: boolean) => {
        const action = currentlyPinned ? 'unpin' : 'pin';
        // Optimistic update
        setExecutions(prev => prev ? prev.map(r => r.id === id ? { ...r, pinned: !currentlyPinned } : r) : prev);
        try {
            await authenticatedFetch(`/api/executions/${id}/${action}`, { method: 'PATCH' });
        } catch {
            // Revert on error
            setExecutions(prev => prev ? prev.map(r => r.id === id ? { ...r, pinned: currentlyPinned } : r) : prev);
            toast.error('Failed to update pin status');
        }
    };

    const handleExportCsv = async () => {
        if (!job) return;
        setExportingCsv(true);
        try {
            const res = await authenticatedFetch(`/jobs/${job.guid}/executions/export`);
            if (!res.ok) { toast.error('Export failed'); return; }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `executions-${job.guid}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        } catch {
            toast.error('Export failed');
        } finally {
            setExportingCsv(false);
        }
    };

    if (!job) return null;
    const cancellable = job.status === 'PENDING' || job.status === 'ASSIGNED';
    const retryable = job.status === 'FAILED' || job.status === 'DEAD_LETTER';
    const securityRejected = job.result?.security_rejected === true || job.status === 'SECURITY_REJECTED';

    const flightRecorder = job.result?.flight_recorder;
    const resultData = job.result
        ? Object.fromEntries(Object.entries(job.result).filter(([k]) => k !== 'flight_recorder'))
        : null;

    const latestExecution = executions && executions.length > 0 ? executions[0] : null;
    const outputLines: Array<{ t: string; stream: string; line: string }> = latestExecution?.output_log ?? [];

    return (
        <Sheet open={open} onOpenChange={onClose}>
            <SheetContent className="bg-zinc-900 border-zinc-800 text-white w-full sm:max-w-xl overflow-y-auto">
                <SheetHeader className="pb-4 border-b border-zinc-800">
                    <SheetTitle className="text-white flex items-center gap-2">
                        <StatusIcon status={job.status} />
                        Job Detail
                    </SheetTitle>
                    <SheetDescription className="font-mono text-zinc-500 text-xs break-all">
                        {job.guid}
                    </SheetDescription>
                </SheetHeader>

                <div className="space-y-6 pt-6">
                    {/* PENDING dispatch diagnosis callout */}
                    {job.status === 'PENDING' && (
                        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4">
                            <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wide mb-1">
                                Dispatch Diagnosis
                            </h4>
                            {diagnosisLoading && !diagnosis && (
                                <p className="text-xs text-amber-300/60">Analysing...</p>
                            )}
                            {diagnosis && (
                                <p className="text-sm text-amber-300">{diagnosis.message}</p>
                            )}
                            {diagnosis?.queue_position != null && diagnosis.queue_position > 1 && (
                                <p className="text-xs text-amber-300/80 mt-1">
                                    Approximately {diagnosis.queue_position - 1} jobs ahead in queue.
                                </p>
                            )}
                        </div>
                    )}

                    {cancellable && (
                        <Button
                            variant="outline"
                            className="w-full border-red-500/40 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                            onClick={() => { onCancel(job.guid); onClose(); }}
                        >
                            <Ban className="mr-2 h-4 w-4" /> Cancel Job
                        </Button>
                    )}

                    {retryable && (
                        <div className="flex gap-2">
                            {resubmitConfirming ? (
                                <div className="flex gap-2 items-center flex-1">
                                    <span className="text-xs text-zinc-400">Confirm resubmit?</span>
                                    <Button size="sm" variant="ghost" onClick={() => setResubmitConfirming(false)}>Cancel</Button>
                                    <Button size="sm" onClick={() => { onResubmit(job.guid); setResubmitConfirming(false); }}>Confirm</Button>
                                </div>
                            ) : (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="flex-1 border-amber-500/40 text-amber-400 hover:bg-amber-500/10 hover:text-amber-300"
                                    onClick={() => setResubmitConfirming(true)}
                                >
                                    <RefreshCw className="mr-2 h-3.5 w-3.5" /> Resubmit
                                </Button>
                            )}
                            {!resubmitConfirming && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="flex-1 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                                    onClick={() => onEditResubmit(job)}
                                >
                                    <Terminal className="mr-2 h-3.5 w-3.5" /> Edit &amp; Resubmit
                                </Button>
                            )}
                        </div>
                    )}

                    {/* SECURITY_REJECTED callout */}
                    {securityRejected && (
                        <div className="border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-400 rounded-md">
                            Script signature did not match registered key — re-sign and resubmit.
                        </div>
                    )}

                    {/* Inline output */}
                    <section className="space-y-2">
                        <div className="flex items-center justify-between">
                            <h3 className="text-2xs font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-1.5">
                                <Terminal className="h-3 w-3" /> Output
                            </h3>
                            {executions && executions.length > 0 && (
                                <button
                                    onClick={handleExportCsv}
                                    disabled={exportingCsv}
                                    className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                                    title="Download execution records as CSV"
                                >
                                    <Download className="h-3 w-3" />
                                    {exportingCsv ? 'Exporting…' : 'Download CSV'}
                                </button>
                            )}
                        </div>
                        {execLoading ? (
                            <div className="flex items-center gap-2 text-xs text-zinc-600 py-2">
                                <RefreshCw className="h-3 w-3 animate-spin" /> Loading output...
                            </div>
                        ) : outputLines.length > 0 ? (
                            <div className="bg-black/50 rounded-lg p-3 overflow-auto max-h-48 space-y-0.5 font-mono text-[11px]">
                                {outputLines.map((l, i) => (
                                    <div key={i} className="flex gap-4 group hover:bg-zinc-900/50 px-2 py-0.5 rounded">
                                        <span className="text-zinc-700 shrink-0">
                                            {new Date(l.t).toLocaleTimeString('en-GB', { hour12: false })}
                                        </span>
                                        <span className={`shrink-0 ${l.stream === 'stderr' ? 'text-amber-500/80' : 'text-zinc-600'}`}>
                                            [{l.stream.slice(0, 3).toUpperCase()}]
                                        </span>
                                        <span className={l.stream === 'stderr' ? 'text-amber-200' : 'text-zinc-300'}>
                                            {l.line}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : latestExecution?.stdout || latestExecution?.stderr ? (
                            <pre className="bg-black/50 rounded-lg p-3 overflow-auto max-h-48 text-xs text-zinc-300 font-mono whitespace-pre-wrap">
                                {latestExecution.stdout}{latestExecution.stderr}
                            </pre>
                        ) : (
                            <p className="text-xs text-zinc-600 italic py-1">No execution records yet.</p>
                        )}
                    </section>

                    {/* Execution Records table with pin toggles */}
                    {executions && executions.length > 0 && (
                        <section className="space-y-2">
                            <h3 className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Execution Records</h3>
                            <div className="rounded-lg border border-zinc-800 overflow-hidden">
                                <table className="w-full text-xs">
                                    <thead className="bg-zinc-900/50">
                                        <tr className="border-b border-zinc-800">
                                            <th className="w-7 pl-2 py-1.5 text-left text-zinc-500"></th>
                                            <th className="px-2 py-1.5 text-left text-zinc-500">Status</th>
                                            <th className="px-2 py-1.5 text-left text-zinc-500">Attempt</th>
                                            <th className="px-2 py-1.5 text-left text-zinc-500">Started</th>
                                            <th className="px-2 py-1.5 text-left text-zinc-500">Duration</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {executions.map((rec: any) => (
                                            <tr
                                                key={rec.id}
                                                className={`border-t border-zinc-900 ${rec.pinned ? 'border-l-2 border-l-amber-500' : ''}`}
                                            >
                                                <td className="pl-2 py-1.5">
                                                    <button
                                                        onClick={() => handlePin(rec.id, rec.pinned)}
                                                        title={rec.pinned ? 'Unpin' : 'Pin'}
                                                        className="flex items-center"
                                                    >
                                                        <Pin className={`h-3 w-3 ${rec.pinned ? 'fill-amber-500 text-amber-500' : 'text-zinc-500 hover:text-zinc-300'}`} />
                                                    </button>
                                                </td>
                                                <td className="px-2 py-1.5 font-mono text-zinc-300 capitalize">{(rec.status || '—').toLowerCase()}</td>
                                                <td className="px-2 py-1.5 text-zinc-400">{rec.attempt_number ?? 1}</td>
                                                <td className="px-2 py-1.5 text-zinc-400">{rec.started_at ? new Date(rec.started_at).toLocaleTimeString() : '—'}</td>
                                                <td className="px-2 py-1.5 text-zinc-400">{rec.duration_s != null ? `${rec.duration_s.toFixed(1)}s` : '—'}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    )}

                    {/* Node health snapshot */}
                    {nodeHealth && (
                        <section className="space-y-2">
                            <h3 className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Node Health at Execution</h3>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                                <div className="bg-zinc-950 rounded-md px-3 py-2 border border-zinc-800">
                                    <span className="text-zinc-500 block">CPU</span>
                                    <span className="text-zinc-200 font-mono font-medium">{nodeHealth.cpu.toFixed(1)}%</span>
                                </div>
                                <div className="bg-zinc-950 rounded-md px-3 py-2 border border-zinc-800">
                                    <span className="text-zinc-500 block">RAM</span>
                                    <span className="text-zinc-200 font-mono font-medium">{nodeHealth.ram.toFixed(1)}%</span>
                                </div>
                            </div>
                            <p className="text-[10px] text-zinc-600">Recorded at {new Date(nodeHealth.recorded_at).toLocaleString()}</p>
                        </section>
                    )}

                    {/* Metadata */}
                    <section className="space-y-3">
                        <h3 className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Metadata</h3>
                        <div className="grid grid-cols-2 gap-y-2 text-sm">
                            <span className="text-zinc-500">Status</span>
                            <div className="w-fit">
                                {job.status.toLowerCase() === 'retrying' ? (
                                    <Badge className="border border-amber-500/60 text-amber-400 bg-amber-500/10 capitalize">retrying</Badge>
                                ) : job.status.toLowerCase() === 'dead_letter' ? (
                                    <Badge className="border border-rose-900/60 text-rose-300 bg-rose-900/20 capitalize">dead letter</Badge>
                                ) : (
                                    <Badge variant={getStatusVariant(job.status) as any} className="w-fit capitalize">{job.status.toLowerCase()}</Badge>
                                )}
                            </div>
                            {job.status === 'RETRYING' && retryCountdown && (
                                <>
                                    <span className="text-zinc-500">Next Attempt</span>
                                    <span className="text-amber-400 text-sm font-mono">{retryCountdown}</span>
                                </>
                            )}
                            {job.max_retries && job.max_retries > 0 && (
                                <>
                                    <span className="text-zinc-500">Attempt</span>
                                    <span className="text-zinc-300">{(job.retry_count ?? 0) + 1} / {job.max_retries + 1}</span>
                                </>
                            )}
                            <span className="text-zinc-500">Type</span>
                            <span className="font-mono text-zinc-300">{job.display_type ?? job.task_type ?? '—'}</span>
                            <span className="text-zinc-500">Node</span>
                            <span className="font-mono text-zinc-300 truncate">{job.node_id || '—'}</span>
                            <span className="text-zinc-500">Started</span>
                            <span className="text-zinc-300">{job.started_at ? new Date(job.started_at).toLocaleString() : '—'}</span>
                            <span className="text-zinc-500">Duration</span>
                            <span className="text-zinc-300">{job.duration_seconds != null ? `${job.duration_seconds.toFixed(2)}s` : '—'}</span>
                            {job.originating_guid && (
                                <>
                                    <span className="text-zinc-500">Resubmitted from</span>
                                    <span className="font-mono text-zinc-400 text-xs break-all">{job.originating_guid}</span>
                                </>
                            )}
                            {job.target_tags && job.target_tags.length > 0 && (
                                <>
                                    <span className="text-zinc-500">Tags</span>
                                    <div className="flex flex-wrap gap-1">
                                        {job.target_tags.map(t => (
                                            <span key={t} className="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] border border-zinc-700 text-zinc-400">{t}</span>
                                        ))}
                                    </div>
                                </>
                            )}
                            {job.depends_on && job.depends_on.length > 0 && (
                                <>
                                    <span className="text-zinc-500">Depends On</span>
                                    <div className="flex flex-col gap-1.5">
                                        {job.depends_on.map((dep: any, idx: number) => {
                                            if (typeof dep === 'string') {
                                                return (
                                                    <span key={idx} className="px-1.5 py-0.5 rounded bg-zinc-900/50 text-[10px] border border-zinc-800 text-zinc-500 font-mono w-fit">
                                                        Job: {dep.slice(0, 8)}... (COMPLETED)
                                                    </span>
                                                );
                                            }
                                            if (dep.type === 'job') {
                                                return (
                                                    <span key={idx} className="px-1.5 py-0.5 rounded bg-zinc-900/50 text-[10px] border border-zinc-800 text-zinc-500 font-mono w-fit">
                                                        Job: {dep.ref.slice(0, 8)}... ({dep.condition || 'COMPLETED'})
                                                    </span>
                                                );
                                            }
                                            if (dep.type === 'signal') {
                                                return (
                                                    <span key={idx} className="px-1.5 py-0.5 rounded bg-amber-500/10 text-[10px] border border-amber-500/20 text-amber-500 font-bold w-fit flex items-center gap-1">
                                                        <Zap className="h-2.5 w-2.5 fill-current" /> Signal: {dep.ref}
                                                    </span>
                                                );
                                            }
                                            return null;
                                        })}
                                    </div>
                                </>
                            )}
                        </div>
                    </section>

                    {/* Result */}
                    {resultData && Object.keys(resultData).length > 0 && (
                        <section className="space-y-2">
                            <h3 className="text-2xs font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-1.5">
                                <CheckCircle2 className="h-3 w-3 text-green-500" /> Result
                            </h3>
                            <pre className="text-xs text-green-400 font-mono bg-zinc-950 rounded-lg p-3 overflow-auto max-h-48 whitespace-pre-wrap">
                                {JSON.stringify(resultData, null, 2)}
                            </pre>
                        </section>
                    )}

                    {/* Flight Recorder */}
                    {flightRecorder && (
                        <section className="space-y-2">
                            <h3 className="text-2xs font-bold text-red-500 uppercase tracking-widest flex items-center gap-1.5">
                                <AlertTriangle className="h-3 w-3" /> Flight Recorder
                            </h3>
                            <div className="bg-zinc-950 rounded-lg p-3 space-y-2 border border-red-500/20">
                                {flightRecorder.error && (
                                    <p className="text-sm text-red-400 font-medium">{flightRecorder.error}</p>
                                )}
                                {flightRecorder.exit_code != null && (
                                    <p className="text-xs text-zinc-500">Exit code: <span className="font-mono text-zinc-300">{flightRecorder.exit_code}</span></p>
                                )}
                                {flightRecorder.stack_trace && (
                                    <pre className="text-xs text-zinc-400 font-mono overflow-auto max-h-40 whitespace-pre-wrap border-t border-zinc-800 pt-2">
                                        {flightRecorder.stack_trace}
                                    </pre>
                                )}
                            </div>
                        </section>
                    )}

                    {/* Payload */}
                    <section className="space-y-2">
                        <h3 className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Payload</h3>
                        <pre className="text-xs text-zinc-400 font-mono bg-zinc-950 rounded-lg p-3 overflow-auto max-h-40 whitespace-pre-wrap">
                            {JSON.stringify(job.payload, null, 2)}
                        </pre>
                    </section>
                </div>
            </SheetContent>
        </Sheet>
    );
};

// ─── More Filters Sheet ───────────────────────────────────────────────────────

const MoreFiltersSheet = ({
    open,
    onOpenChange,
    filters,
    setFilters,
    nodes,
    nodeSearch,
    setNodeSearch,
    tagInput,
    setTagInput,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    filters: FilterState;
    setFilters: React.Dispatch<React.SetStateAction<FilterState>>;
    nodes: NodeItem[];
    nodeSearch: string;
    setNodeSearch: (v: string) => void;
    tagInput: string;
    setTagInput: (v: string) => void;
}) => {
    const filteredNodes = nodes.filter(n =>
        (n.hostname || n.node_id).toLowerCase().includes(nodeSearch.toLowerCase())
    );

    const setPreset = (preset: string) => {
        const now = new Date();
        let from: Date;
        switch (preset) {
            case '1h':  from = subHours(now, 1); break;
            case '24h': from = subHours(now, 24); break;
            case '7d':  from = subDays(now, 7); break;
            case '30d': from = subDays(now, 30); break;
            default:    from = now;
        }
        setFilters(f => ({ ...f, datePreset: preset, dateFrom: from.toISOString(), dateTo: '' }));
    };

    const addTag = (value: string) => {
        const trimmed = value.trim();
        if (trimmed && !filters.tags.includes(trimmed)) {
            setFilters(f => ({ ...f, tags: [...f.tags, trimmed] }));
        }
        setTagInput('');
    };

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent side="right" className="bg-zinc-900 border-zinc-800 text-white w-full sm:max-w-sm overflow-y-auto">
                <SheetHeader className="pb-4 border-b border-zinc-800">
                    <SheetTitle className="text-white flex items-center gap-2">
                        <SlidersHorizontal className="h-4 w-4" />
                        More Filters
                    </SheetTitle>
                    <SheetDescription className="text-zinc-500 text-xs">
                        Refine jobs by date, node, tags, and creator.
                    </SheetDescription>
                </SheetHeader>

                <div className="space-y-6 pt-6">
                    {/* Date Range */}
                    <section className="space-y-3">
                        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Date Range</h3>
                        <div className="flex flex-wrap gap-2">
                            {(['1h', '24h', '7d', '30d'] as const).map(preset => (
                                <Button
                                    key={preset}
                                    size="sm"
                                    variant={filters.datePreset === preset ? 'default' : 'outline'}
                                    className={`h-7 text-xs ${filters.datePreset === preset ? '' : 'border-zinc-700 text-zinc-400 hover:text-white hover:border-zinc-500'}`}
                                    onClick={() => setPreset(preset)}
                                >
                                    Last {preset}
                                </Button>
                            ))}
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs text-zinc-500">Custom from</label>
                            <Input
                                type="datetime-local"
                                value={filters.dateFrom ? filters.dateFrom.slice(0, 16) : ''}
                                onChange={e => setFilters(f => ({ ...f, dateFrom: e.target.value ? new Date(e.target.value).toISOString() : '', datePreset: 'custom' }))}
                                className="bg-zinc-800 border-zinc-700 text-white text-xs h-9"
                            />
                            <label className="text-xs text-zinc-500">Custom to</label>
                            <Input
                                type="datetime-local"
                                value={filters.dateTo ? filters.dateTo.slice(0, 16) : ''}
                                onChange={e => setFilters(f => ({ ...f, dateTo: e.target.value ? new Date(e.target.value).toISOString() : '', datePreset: 'custom' }))}
                                className="bg-zinc-800 border-zinc-700 text-white text-xs h-9"
                            />
                        </div>
                    </section>

                    {/* Target Node */}
                    <section className="space-y-3">
                        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Target Node</h3>
                        <Input
                            placeholder="Search nodes..."
                            value={nodeSearch}
                            onChange={e => setNodeSearch(e.target.value)}
                            className="bg-zinc-800 border-zinc-700 text-white text-xs h-9"
                        />
                        {filteredNodes.length > 0 && (
                            <div className="bg-zinc-800 rounded-lg border border-zinc-700 overflow-hidden max-h-40 overflow-y-auto">
                                {filteredNodes.slice(0, 20).map(n => {
                                    const label = n.hostname || n.node_id;
                                    const selected = filters.nodeId === n.node_id;
                                    return (
                                        <button
                                            key={n.node_id}
                                            className={`w-full text-left px-3 py-2 text-xs font-mono transition-colors ${selected ? 'bg-primary/20 text-primary' : 'text-zinc-300 hover:bg-zinc-700'}`}
                                            onClick={() => {
                                                setFilters(f => ({ ...f, nodeId: selected ? '' : n.node_id }));
                                                setNodeSearch('');
                                            }}
                                        >
                                            {label}
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                        {filters.nodeId && (
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-zinc-400">Selected:</span>
                                <span className="text-xs font-mono text-primary">{filters.nodeId.slice(0, 16)}…</span>
                                <button onClick={() => setFilters(f => ({ ...f, nodeId: '' }))} className="text-zinc-500 hover:text-white">
                                    <X className="h-3 w-3" />
                                </button>
                            </div>
                        )}
                    </section>

                    {/* Target Tags */}
                    <section className="space-y-3">
                        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Target Tags</h3>
                        <div className="flex gap-2">
                            <Input
                                placeholder="Add tag, press Enter"
                                value={tagInput}
                                onChange={e => setTagInput(e.target.value)}
                                onKeyDown={e => {
                                    if (e.key === 'Enter') { e.preventDefault(); addTag(tagInput); }
                                }}
                                className="bg-zinc-800 border-zinc-700 text-white text-xs h-9 flex-1"
                            />
                            <Button size="sm" variant="outline" className="border-zinc-700 text-zinc-400 h-9" onClick={() => addTag(tagInput)}>
                                Add
                            </Button>
                        </div>
                        {filters.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                                {filters.tags.map(tag => (
                                    <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-700 text-xs text-zinc-300 border border-zinc-600">
                                        {tag}
                                        <button onClick={() => setFilters(f => ({ ...f, tags: f.tags.filter(t => t !== tag) }))} className="hover:text-white">
                                            <X className="h-2.5 w-2.5" />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                    </section>

                    {/* Created By */}
                    <section className="space-y-3">
                        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Created By</h3>
                        <Input
                            placeholder="Username..."
                            value={filters.createdBy}
                            onChange={e => setFilters(f => ({ ...f, createdBy: e.target.value }))}
                            className="bg-zinc-800 border-zinc-700 text-white text-xs h-9"
                        />
                    </section>

                    {/* Clear All */}
                    <Button
                        variant="outline"
                        className="w-full border-zinc-700 text-zinc-400 hover:text-white"
                        onClick={() => {
                            setFilters(EMPTY_FILTERS);
                            setNodeSearch('');
                            setTagInput('');
                        }}
                    >
                        Clear All Filters
                    </Button>
                </div>
            </SheetContent>
        </Sheet>
    );
};

// ─── Main Component ───────────────────────────────────────────────────────────

const Jobs = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    // List state
    const [jobs, setJobs] = useState<Job[]>([]);
    const [total, setTotal] = useState(0);
    const [nextCursor, setNextCursor] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [pendingNewJobs, setPendingNewJobs] = useState(0);

    // Filter state
    const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
    const [showMoreFilters, setShowMoreFilters] = useState(false);
    const [tagInput, setTagInput] = useState('');
    const [nodes, setNodes] = useState<NodeItem[]>([]);
    const [nodeSearch, setNodeSearch] = useState('');

    // Export state
    const [exporting, setExporting] = useState(false);

    // Detail/log state
    const [selectedJob, setSelectedJob] = useState<Job | null>(null);
    const [detailOpen, setDetailOpen] = useState(false);
    const [logModalGuid, setLogModalGuid] = useState<string | null>(null);

    // Resubmit + highlight state
    const [highlightGuid, setHighlightGuid] = useState<string | null>(null);
    const [guidedInitialValues, setGuidedInitialValues] = useState<Partial<GuidedFormState> | null>(null);
    const guidedCardRef = useRef<HTMLDivElement>(null);

    // Bulk selection state
    const [selectedGuids, setSelectedGuids] = useState<Set<string>>(new Set());
    const selectionActive = selectedGuids.size > 0;
    const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);
    const [pendingBulkAction, setPendingBulkAction] = useState<'cancel' | 'resubmit' | 'delete' | null>(null);

    // Bulk selection helpers
    const TERMINAL_STATES = new Set(['COMPLETED', 'FAILED', 'DEAD_LETTER', 'CANCELLED', 'SECURITY_REJECTED']);
    const CANCELLABLE_STATES = new Set(['PENDING', 'ASSIGNED', 'RUNNING']);

    const toggleSelect = (guid: string) =>
        setSelectedGuids(prev => {
            const next = new Set(prev);
            next.has(guid) ? next.delete(guid) : next.add(guid);
            return next;
        });

    const allSelected = jobs.length > 0 && jobs.every(j => selectedGuids.has(j.guid));
    const toggleAll = () =>
        setSelectedGuids(allSelected ? new Set() : new Set(jobs.map(j => j.guid)));

    const getSelectedJobs = () => jobs.filter(j => selectedGuids.has(j.guid));

    // Build filter query params (shared between fetchJobs and handleExport)
    const buildFilterParams = useCallback((f: FilterState): URLSearchParams => {
        const params = new URLSearchParams();
        if (f.status !== 'all') params.set('status', f.status);
        if (f.runtime !== 'all') params.set('runtime', f.runtime);
        if (f.taskType !== 'all') params.set('task_type', f.taskType);
        if (f.nodeId) params.set('node_id', f.nodeId);
        if (f.tags.length) params.set('tags', f.tags.join(','));
        if (f.createdBy) params.set('created_by', f.createdBy);
        if (f.dateFrom) params.set('date_from', f.dateFrom);
        if (f.dateTo) params.set('date_to', f.dateTo);
        if (f.search) params.set('search', f.search);
        return params;
    }, []);

    // Fetch jobs — cursor-based load-more pattern
    const fetchJobs = useCallback(async (opts: { reset?: boolean; cursor?: string | null } = {}) => {
        if (opts.reset) {
            setLoading(true);
        } else {
            setLoadingMore(true);
        }
        try {
            const params = buildFilterParams(filters);
            if (opts.cursor) params.set('cursor', opts.cursor);

            const res = await authenticatedFetch(`/jobs?${params}`);
            if (!res.ok) return;
            const data: PaginatedJobResponse = await res.json();

            if (opts.reset) {
                setJobs(data.items);
                setSelectedGuids(new Set());  // clear selection on any reload/filter reset
            } else {
                setJobs(prev => [...prev, ...data.items]);
            }
            setTotal(data.total);
            setNextCursor(data.next_cursor);
            setPendingNewJobs(0);
        } catch (e) {
            console.error(e);
            toast.error('Failed to load jobs');
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    }, [filters, buildFilterParams]);

    // Fetch nodes for combobox
    const fetchNodes = useCallback(async () => {
        try {
            const res = await authenticatedFetch('/nodes?page_size=200');
            if (!res.ok) return;
            const data = await res.json();
            // Handle both paginated envelope {items} and bare array
            const items: any[] = Array.isArray(data) ? data : (data.items ?? []);
            setNodes(items.map((n: any) => ({ node_id: n.node_id, hostname: n.hostname, tags: n.tags ?? [] })));
        } catch {
            // Non-critical — combobox just won't be populated
        }
    }, []);

    // Load template from ?template_id query param on mount
    const templateId = searchParams.get('template_id');
    useEffect(() => {
        if (templateId) {
            authenticatedFetch(`/api/job-templates/${templateId}`)
                .then(r => r.ok ? r.json() : null)
                .then(tmpl => {
                    if (!tmpl) return;
                    const p = tmpl.payload ?? {};
                    const initialValues: Partial<GuidedFormState> = {
                        name: p.name ?? '',
                        runtime: (p.runtime as GuidedFormState['runtime']) ?? 'python',
                        scriptContent: p.script ?? p.script_content ?? p.payload?.script ?? p.payload?.script_content ?? '',
                        targetNodeId: '',
                        targetTags: p.target_tags ?? [],
                        capabilityReqs: p.capability_requirements
                            ? Object.entries(p.capability_requirements).map(([k, v]) => `${k}:${v}`)
                            : [],
                        signatureId: '',
                        signature: '',
                        signatureCleared: true,
                    };
                    setGuidedInitialValues(initialValues);
                    // Clear the query param
                    navigate('/jobs', { replace: true });
                    setTimeout(() => {
                        guidedCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 100);
                })
                .catch(() => {/* non-critical */});
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // On mount
    useEffect(() => {
        fetchJobs({ reset: true });
        fetchNodes();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // Re-fetch when filters change
    const filtersRef = useRef(filters);
    useEffect(() => {
        if (filtersRef.current === filters) return; // skip initial mount (handled above)
        filtersRef.current = filters;
        fetchJobs({ reset: true });
    }, [filters, fetchJobs]);

    // WebSocket: banner for new jobs, in-place patch for updates
    useWebSocket((event, data: any) => {
        if (event === 'job:created') {
            setPendingNewJobs(c => c + 1);
        } else if (event === 'job:updated') {
            setJobs(prev => prev.map(j => j.guid === data?.guid ? { ...j, ...data } : j));
        }
    });

    // Export CSV
    const handleExport = async () => {
        setExporting(true);
        try {
            const params = buildFilterParams(filters);
            const res = await authenticatedFetch(`/jobs/export?${params}`);
            if (!res.ok) { toast.error('Export failed'); return; }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'jobs-export.csv';
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error(e);
            toast.error('Export failed');
        } finally {
            setExporting(false);
        }
    };

    // Derive active filter chips
    const activeChips = [
        filters.status !== 'all' && { key: 'status', label: `Status: ${filters.status}`, clear: () => setFilters(f => ({ ...f, status: 'all' })) },
        filters.runtime !== 'all' && { key: 'runtime', label: `Runtime: ${filters.runtime}`, clear: () => setFilters(f => ({ ...f, runtime: 'all' })) },
        filters.taskType !== 'all' && { key: 'taskType', label: `Type: ${filters.taskType}`, clear: () => setFilters(f => ({ ...f, taskType: 'all' })) },
        filters.tags.length > 0 && { key: 'tags', label: `Tags: ${filters.tags.join(', ')}`, clear: () => setFilters(f => ({ ...f, tags: [] })) },
        filters.nodeId && { key: 'node', label: `Node: ${filters.nodeId.slice(0, 12)}…`, clear: () => setFilters(f => ({ ...f, nodeId: '' })) },
        filters.createdBy && { key: 'createdBy', label: `By: ${filters.createdBy}`, clear: () => setFilters(f => ({ ...f, createdBy: '' })) },
        (filters.datePreset || filters.dateFrom) && {
            key: 'date',
            label: filters.datePreset && filters.datePreset !== 'custom' ? `Last ${filters.datePreset}` : 'Custom date range',
            clear: () => setFilters(f => ({ ...f, dateFrom: '', dateTo: '', datePreset: '' })),
        },
    ].filter(Boolean) as { key: string; label: string; clear: () => void }[];

    // Job actions
    const openDetail = (job: Job) => {
        setSelectedJob(job);
        setDetailOpen(true);
    };

    const closeDetail = () => {
        setDetailOpen(false);
    };

    const handleResubmit = async (guid: string) => {
        try {
            const res = await authenticatedFetch(`/jobs/${guid}/resubmit`, { method: 'POST' });
            if (!res.ok) { toast.error('Resubmit failed'); return; }
            const newJob = await res.json();
            closeDetail();
            await fetchJobs({ reset: true });
            setHighlightGuid(newJob.guid);
            setTimeout(() => setHighlightGuid(null), 2500);
            toast.success(`Job resubmitted — ${newJob.guid.slice(0, 8)}`);
        } catch { toast.error('Resubmit failed'); }
    };

    const handleEditResubmit = (job: Job) => {
        const payload = typeof job.payload === 'object' ? job.payload : {};
        const initialValues: Partial<GuidedFormState> = {
            name: job.name ?? '',
            runtime: (job.runtime as GuidedFormState['runtime']) ?? 'python',
            scriptContent: payload.script ?? payload.script_content ?? '',
            targetNodeId: '',
            targetTags: job.target_tags ?? [],
            capabilityReqs: [],
            signatureId: '',
            signature: '',
            signatureCleared: true,
        };
        closeDetail();
        setGuidedInitialValues(initialValues);
        setTimeout(() => {
            guidedCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    };

    const cancelJob = async (guid: string) => {
        try {
            const res = await authenticatedFetch(`/jobs/${guid}/cancel`, { method: 'PATCH' });
            if (res.ok) {
                toast.success('Job cancelled');
                fetchJobs({ reset: true });
            } else {
                toast.error('Failed to cancel job');
            }
        } catch (e) {
            console.error(e);
            toast.error('Failed to cancel job');
        }
    };

    // Bulk action handlers
    const handleBulkCancel = () => {
        setPendingBulkAction('cancel');
        setBulkConfirmOpen(true);
    };
    const handleBulkResubmit = () => {
        setPendingBulkAction('resubmit');
        setBulkConfirmOpen(true);
    };
    const handleBulkDelete = () => {
        setPendingBulkAction('delete');
        setBulkConfirmOpen(true);
    };

    const executeBulkAction = async () => {
        setBulkConfirmOpen(false);
        const guids = [...selectedGuids];
        try {
            if (pendingBulkAction === 'cancel') {
                const res = await authenticatedFetch('/jobs/bulk-cancel', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ guids }),
                });
                const data = await res.json();
                toast.success(`Cancelled ${data.processed} job(s)${data.skipped > 0 ? `, skipped ${data.skipped}` : ''}`);
            } else if (pendingBulkAction === 'resubmit') {
                const res = await authenticatedFetch('/jobs/bulk-resubmit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ guids }),
                });
                const data = await res.json();
                toast.success(`Resubmitted ${data.processed} job(s)${data.skipped > 0 ? `, skipped ${data.skipped}` : ''}`);
            } else if (pendingBulkAction === 'delete') {
                const res = await authenticatedFetch('/jobs/bulk', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ guids }),
                });
                const data = await res.json();
                toast.success(`Deleted ${data.processed} job(s)${data.skipped > 0 ? `, skipped ${data.skipped} non-terminal` : ''}`);
            }
            setSelectedGuids(new Set());
            await fetchJobs({ reset: true });
        } catch { toast.error('Bulk action failed'); }
    };

    const bulkConfirmText = () => {
        const selected = getSelectedJobs();
        if (pendingBulkAction === 'cancel') {
            const toCancel = selected.filter(j => CANCELLABLE_STATES.has(j.status));
            const toSkip = selected.length - toCancel.length;
            return `Cancel ${toCancel.length} job(s)?${toSkip > 0 ? ` (${toSkip} already terminal and will be skipped)` : ''}`;
        }
        if (pendingBulkAction === 'resubmit') {
            const toResubmit = selected.filter(j => j.status === 'FAILED' || j.status === 'DEAD_LETTER');
            const toSkip = selected.length - toResubmit.length;
            return `Resubmit ${toResubmit.length} job(s)?${toSkip > 0 ? ` (${toSkip} not in FAILED/DEAD_LETTER will be skipped)` : ''}`;
        }
        if (pendingBulkAction === 'delete') {
            const toDelete = selected.filter(j => TERMINAL_STATES.has(j.status));
            const toSkip = selected.length - toDelete.length;
            return `Delete ${toDelete.length} job(s)?${toSkip > 0 ? ` (${toSkip} non-terminal will be skipped)` : ''}`;
        }
        return '';
    };

    const handleRetry = async (guid: string) => {
        try {
            const res = await authenticatedFetch(`/jobs/${guid}/retry`, { method: 'POST' });
            if (res.ok) {
                toast.success('Job re-queued for retry');
                fetchJobs({ reset: true });
            } else {
                const data = await res.json().catch(() => ({}));
                toast.error(data.detail || 'Failed to retry job');
            }
        } catch {
            toast.error('Failed to retry job');
        }
    };

    // ─── Render ───────────────────────────────────────────────────────────────

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Page header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-white">Jobs</h1>
                    <p className="text-sm text-zinc-500 mt-1">Dispatch and monitor task payloads.</p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" className="border-zinc-800 bg-zinc-900/50 hover:bg-zinc-900" asChild>
                        <Link to="/audit">
                            <History className="mr-2 h-4 w-4" />
                            Audit Log
                        </Link>
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                {/* Guided Dispatch Form */}
                <div ref={guidedCardRef}>
                    <GuidedDispatchCard
                        nodes={nodes}
                        onJobCreated={() => fetchJobs({ reset: true })}
                        initialValues={guidedInitialValues ?? undefined}
                    />
                </div>

                {/* Queue Monitor */}
                <Card className="xl:col-span-2 bg-zinc-925 border-zinc-800/50 overflow-hidden">
                    <CardHeader className="pb-3">
                        <div className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-lg font-bold text-white">Queue Monitor</CardTitle>
                                <CardDescription className="text-zinc-500">Real-time status of dispatched tasks.</CardDescription>
                            </div>
                        </div>

                        {/* Bulk action bar — replaces filter bar when selection is active */}
                        {selectionActive ? (
                            <div className="flex items-center gap-3 px-1 py-2 border-b border-zinc-800">
                                <span className="text-sm text-zinc-300 font-medium">{selectedGuids.size} selected</span>
                                <div className="flex gap-2">
                                    {getSelectedJobs().some(j => CANCELLABLE_STATES.has(j.status)) && (
                                        <Button size="sm" variant="outline" className="border-zinc-700 text-zinc-300 hover:text-white" onClick={handleBulkCancel}>Cancel</Button>
                                    )}
                                    {getSelectedJobs().some(j => j.status === 'FAILED' || j.status === 'DEAD_LETTER') && (
                                        <Button size="sm" variant="outline" className="border-zinc-700 text-zinc-300 hover:text-white" onClick={handleBulkResubmit}>Resubmit</Button>
                                    )}
                                    {getSelectedJobs().some(j => TERMINAL_STATES.has(j.status)) && (
                                        <Button size="sm" variant="destructive" onClick={handleBulkDelete}>Delete</Button>
                                    )}
                                </div>
                                <Button size="sm" variant="ghost" className="ml-auto text-zinc-400 hover:text-white" onClick={() => setSelectedGuids(new Set())}>
                                    Clear selection ×
                                </Button>
                            </div>
                        ) : null}

                        {/* Filter bar — always visible row */}
                        <div className="flex flex-wrap items-center gap-2 pt-2">
                            {/* Search */}
                            <div className="relative flex-1 min-w-40">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
                                <Input
                                    placeholder="Search name or GUID..."
                                    value={filters.search}
                                    onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
                                    className="pl-9 bg-zinc-900 border-zinc-800 h-9 text-sm text-white"
                                />
                            </div>

                            {/* Status */}
                            <Select value={filters.status} onValueChange={v => setFilters(f => ({ ...f, status: v }))}>
                                <SelectTrigger className="bg-zinc-900 border-zinc-800 text-white h-9 w-36 text-xs">
                                    <SelectValue placeholder="Status" />
                                </SelectTrigger>
                                <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                                    <SelectItem value="all">All Status</SelectItem>
                                    <SelectItem value="pending">Pending</SelectItem>
                                    <SelectItem value="assigned">Assigned</SelectItem>
                                    <SelectItem value="completed">Completed</SelectItem>
                                    <SelectItem value="failed">Failed</SelectItem>
                                    <SelectItem value="cancelled">Cancelled</SelectItem>
                                    <SelectItem value="security_rejected">Security Rejected</SelectItem>
                                    <SelectItem value="retrying">Retrying</SelectItem>
                                    <SelectItem value="dead_letter">Dead Letter</SelectItem>
                                </SelectContent>
                            </Select>

                            {/* Runtime */}
                            <Select value={filters.runtime} onValueChange={v => setFilters(f => ({ ...f, runtime: v }))}>
                                <SelectTrigger className="bg-zinc-900 border-zinc-800 text-white h-9 w-32 text-xs">
                                    <SelectValue placeholder="Runtime" />
                                </SelectTrigger>
                                <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                                    <SelectItem value="all">All Runtimes</SelectItem>
                                    <SelectItem value="python">Python</SelectItem>
                                    <SelectItem value="bash">Bash</SelectItem>
                                    <SelectItem value="powershell">PowerShell</SelectItem>
                                </SelectContent>
                            </Select>

                            {/* More filters toggle */}
                            <Button
                                variant="outline"
                                size="sm"
                                className={`h-9 border-zinc-700 text-xs gap-1.5 ${showMoreFilters || activeChips.some(c => ['date','node','tags','createdBy','taskType'].includes(c.key)) ? 'border-primary/50 text-primary' : 'text-zinc-400 hover:text-white'}`}
                                onClick={() => setShowMoreFilters(v => !v)}
                            >
                                <SlidersHorizontal className="h-3.5 w-3.5" />
                                More filters
                                {activeChips.some(c => ['date','node','tags','createdBy','taskType'].includes(c.key)) && (
                                    <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-primary text-primary-foreground text-[10px] font-bold">
                                        {activeChips.filter(c => ['date','node','tags','createdBy','taskType'].includes(c.key)).length}
                                    </span>
                                )}
                            </Button>
                        </div>

                        {/* Active chips row + Export */}
                        {(activeChips.length > 0) && (
                            <div className="flex flex-wrap items-center gap-2 pt-2">
                                <div className="flex flex-wrap gap-1.5 flex-1">
                                    {activeChips.map(chip => (
                                        <span
                                            key={chip.key}
                                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-800 text-xs text-zinc-300 border border-zinc-700"
                                        >
                                            {chip.label}
                                            <button
                                                onClick={chip.clear}
                                                className="hover:text-white text-zinc-500 ml-0.5"
                                                aria-label={`Remove ${chip.label} filter`}
                                            >
                                                <X className="h-2.5 w-2.5" />
                                            </button>
                                        </span>
                                    ))}
                                </div>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 border-zinc-700 text-zinc-400 hover:text-white text-xs gap-1.5 ml-auto"
                                    onClick={handleExport}
                                    disabled={exporting}
                                >
                                    <Download className="h-3 w-3" />
                                    {exporting ? 'Exporting…' : 'Export CSV'}
                                </Button>
                            </div>
                        )}

                        {/* Export CSV when no active chips */}
                        {activeChips.length === 0 && (
                            <div className="flex justify-end pt-1">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 text-zinc-600 hover:text-zinc-300 text-xs gap-1.5"
                                    onClick={handleExport}
                                    disabled={exporting}
                                >
                                    <Download className="h-3 w-3" />
                                    {exporting ? 'Exporting…' : 'Export CSV'}
                                </Button>
                            </div>
                        )}
                    </CardHeader>

                    {/* New jobs banner */}
                    {pendingNewJobs > 0 && (
                        <div
                            className="mx-4 mb-2 sticky top-0 z-10 bg-primary/90 text-primary-foreground text-sm px-4 py-2 cursor-pointer text-center rounded-md"
                            onClick={() => { setPendingNewJobs(0); fetchJobs({ reset: true }); }}
                        >
                            {pendingNewJobs} new job{pendingNewJobs !== 1 ? 's' : ''} — click to refresh
                        </div>
                    )}

                    <Table>
                        <TableHeader className="bg-zinc-900/50 border-zinc-800">
                            <TableRow className="border-zinc-800 hover:bg-transparent">
                                <TableHead className="w-10 pl-4">
                                    <Checkbox
                                        checked={allSelected}
                                        onCheckedChange={toggleAll}
                                        aria-label="Select all jobs"
                                    />
                                </TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest pl-6">Name / ID</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Type</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Status</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Attempt</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Target Node</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Timestamp</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest pr-6 text-right">Detail</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {loading ? (
                                Array.from({ length: 5 }).map((_, i) => (
                                    <TableRow key={i} className="border-zinc-800">
                                        {Array.from({ length: 8 }).map((_, j) => (
                                            <TableCell key={j} className="py-3 pl-6">
                                                <div className="h-3 bg-zinc-800 animate-pulse rounded w-3/4" />
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                ))
                            ) : jobs.length > 0 ? (
                                jobs.map(job => (
                                    <TableRow
                                        key={job.guid}
                                        className={`border-zinc-800 cursor-pointer hover:bg-zinc-800/50 transition-all duration-500 ${
                                            highlightGuid === job.guid ? 'ring-1 ring-primary/60 bg-primary/5' : ''
                                        }`}
                                        onClick={() => openDetail(job)}
                                    >
                                        <TableCell className="w-10 pl-4" onClick={e => e.stopPropagation()}>
                                            <Checkbox
                                                checked={selectedGuids.has(job.guid)}
                                                onCheckedChange={() => toggleSelect(job.guid)}
                                                aria-label={`Select job ${job.guid}`}
                                            />
                                        </TableCell>
                                        <TableCell className="font-mono text-zinc-400 pl-6">
                                            {job.name ? (
                                                <span className="text-foreground font-medium text-sm">{job.name}</span>
                                            ) : (
                                                <div className="flex items-center gap-2">
                                                    <Hash className="h-3 w-3 text-zinc-600" />
                                                    <span className="text-muted-foreground text-xs">{job.guid.slice(0, 8)}…</span>
                                                </div>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-white font-medium">
                                            {job.display_type ?? job.task_type ?? '—'}
                                        </TableCell>
                                        <TableCell>
                                            {job.status.toLowerCase() === 'retrying' ? (
                                                <Badge className="border border-amber-500/60 text-amber-400 bg-amber-500/10 capitalize">retrying</Badge>
                                            ) : job.status.toLowerCase() === 'dead_letter' ? (
                                                <Badge className="border border-rose-900/60 text-rose-300 bg-rose-900/20 capitalize">dead letter</Badge>
                                            ) : (
                                                <Badge variant={getStatusVariant(job.status) as any} className="capitalize">
                                                    {job.status.toLowerCase()}
                                                </Badge>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-xs text-zinc-500 tabular-nums">
                                            {job.max_retries && job.max_retries > 0
                                                ? `${(job.retry_count ?? 0) + 1}/${job.max_retries + 1}`
                                                : ''}
                                        </TableCell>
                                        <TableCell className="font-mono text-xs text-zinc-500">
                                            {job.node_id ? job.node_id.substring(0, 12) : '-'}
                                        </TableCell>
                                        <TableCell className="text-zinc-500 text-xs">
                                            <div className="flex items-center gap-2">
                                                <Clock className="h-3 w-3" />
                                                {job.started_at ? new Date(job.started_at).toLocaleTimeString() : '-'}
                                            </div>
                                        </TableCell>
                                        <TableCell className="pr-6 text-right" onClick={e => { e.stopPropagation(); openDetail(job); }}>
                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-600 hover:text-white hover:bg-zinc-800 rounded-lg">
                                                <MoreHorizontal className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={8} className="h-32 text-center text-zinc-600">
                                        {activeChips.length > 0 || filters.search ? 'No jobs match the current filters.' : 'Queue is currently empty.'}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>

                    {/* Footer: counter + load more */}
                    <div className="flex items-center justify-between px-6 py-3 border-t border-zinc-800 bg-zinc-900/30">
                        <span className="text-xs text-zinc-500">
                            Showing {jobs.length} of {total}
                        </span>
                        {nextCursor && (
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs text-zinc-400 hover:text-white"
                                disabled={loadingMore}
                                onClick={() => fetchJobs({ cursor: nextCursor })}
                            >
                                {loadingMore ? 'Loading…' : 'Load more'}
                            </Button>
                        )}
                    </div>
                </Card>
            </div>

            {/* More Filters Sheet */}
            <MoreFiltersSheet
                open={showMoreFilters}
                onOpenChange={setShowMoreFilters}
                filters={filters}
                setFilters={setFilters}
                nodes={nodes}
                nodeSearch={nodeSearch}
                setNodeSearch={setNodeSearch}
                tagInput={tagInput}
                setTagInput={setTagInput}
            />

            <JobDetailPanel
                job={selectedJob}
                open={detailOpen}
                onClose={closeDetail}
                onCancel={cancelJob}
                onResubmit={handleResubmit}
                onEditResubmit={handleEditResubmit}
            />
            <ExecutionLogModal jobGuid={logModalGuid ?? ''} open={!!logModalGuid} onClose={() => setLogModalGuid(null)} />

            {/* Bulk action confirmation dialog */}
            <Dialog open={bulkConfirmOpen} onOpenChange={setBulkConfirmOpen}>
                <DialogContent className="bg-zinc-900 border-zinc-800 text-white max-w-md">
                    <DialogHeader>
                        <DialogTitle>Confirm bulk action</DialogTitle>
                        <DialogDescription className="text-zinc-400">
                            {bulkConfirmText()}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="flex gap-2 justify-end mt-4">
                        <Button variant="ghost" onClick={() => setBulkConfirmOpen(false)}>Cancel</Button>
                        <Button
                            variant={pendingBulkAction === 'delete' ? 'destructive' : 'default'}
                            onClick={executeBulkAction}
                        >
                            Confirm
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default Jobs;
