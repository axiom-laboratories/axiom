import { useState, useMemo } from 'react';
import { useTheme } from '@/hooks/useTheme';

const PAGE_SIZE = 25;
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import {
    Server,
    ShieldCheck,
    ShieldAlert,
    AlertTriangle,
    Ban,
    RotateCcw,
    Cpu,
    HardDrive,
    Network,
    Settings2,
    Check,
    X,
    Trash2,
    Zap,
    ChevronRight,
    CheckCircle2,
    Loader2,
    PauseCircle
} from 'lucide-react';
import { toast } from 'sonner';

import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import AddNodeModal from '../components/AddNodeModal';
import ManageMountsModal from '../components/ManageMountsModal';
import HotUpgradeModal from '../components/HotUpgradeModal';
import { authenticatedFetch, getUser } from '../auth';
import { useWebSocket } from '../hooks/useWebSocket';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';

interface NodeStats {
    cpu: number;
    ram: number;
}

interface StatPoint {
    t: string;
    cpu: number | null;
    ram: number | null;
}

interface Node {
    node_id: string;
    hostname: string;
    ip: string;
    status: 'ONLINE' | 'OFFLINE' | 'BUSY' | 'REVOKED' | 'TAMPERED' | 'DRAINING';
    last_seen: string;
    base_os_family?: string;
    stats?: NodeStats;
    version?: string;
    tags?: string[];
    capabilities?: Record<string, string>;
    expected_capabilities?: Record<string, string>;
    tamper_details?: string;
    concurrency_limit?: number;
    job_memory_limit?: string;
    stats_history?: StatPoint[];
    env_tag?: string;
    detected_cgroup_version?: string | null;
}

interface NodeDetail {
    running_job: { guid: string; status: string; task_type: string; name?: string; runtime?: string } | null;
    eligible_pending_jobs: Array<{ guid: string; status: string; task_type: string; name?: string; created_at: string }>;
    recent_history: Array<{ guid: string; status: string; task_type: string; name?: string; completed_at: string }>;
    capabilities: Record<string, string>;
}

interface PaginatedNodeResponse {
    items: Node[];
    total: number;
    page: number;
    pages: number;
}

const fetchNodes = async (page: number): Promise<PaginatedNodeResponse> => {
    const res = await authenticatedFetch(`/nodes?page=${page}&page_size=${PAGE_SIZE}`);
    if (!res.ok) throw new Error('Failed to fetch nodes');
    const data = await res.json();
    // Handle both paginated envelope and legacy bare array (backwards compat)
    if (Array.isArray(data)) {
        return { items: data, total: data.length, page: 1, pages: 1 };
    }
    return data as PaginatedNodeResponse;
};

const GaugeBar = ({ value, color }: { value: number; color: string }) => (
    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
            className={`h-full rounded-full transition-all duration-500 ${color}`}
            style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
    </div>
);

const getEnvBadgeColor = (tag: string) => {
    if (!tag.startsWith('env:')) return 'bg-muted text-muted-foreground border-muted';
    const env = tag.split(':')[1];
    switch (env) {
        case 'prod': return 'bg-rose-500/10 text-rose-500 border-rose-500/20 font-bold';
        case 'staging': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
        case 'test': return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
        default: return 'bg-muted text-foreground border-muted';
    }
};

const getEnvTagBadgeClass = (tag: string): string => {
    switch (tag.toUpperCase()) {
        case 'PROD':
            return 'bg-rose-500/10 text-rose-500 border-rose-500/20 font-bold';
        case 'TEST':
            return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
        case 'DEV':
            return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
        default:
            return 'bg-muted text-foreground border-muted';
    }
};

export const getCgroupBadgeClass = (version: string | null | undefined): string => {
    switch (version) {
        case 'v2': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
        case 'v1': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
        case 'unsupported': return 'bg-red-500/10 text-red-500 border-red-500/20';
        default: return 'bg-muted text-muted-foreground border-muted';
    }
};

export const getCgroupTooltip = (version: string | null | undefined): string => {
    switch (version) {
        case 'v2': return 'Cgroup v2 — Full resource isolation. Memory and CPU limits fully enforced.';
        case 'v1': return 'Cgroup v1 (Degraded) — Memory limits supported. CPU enforcement may be limited. Upgrade to v2 recommended.';
        case 'unsupported': return 'No cgroup support detected. Resource limits cannot be enforced. Jobs run without isolation.';
        default: return 'Cgroup status not reported. Node may be running an older version.';
    }
};

export const getCgroupDisplayText = (version: string | null | undefined): string => {
    return version || 'unknown';
};

const StatsSparkline = ({ history }: { history: StatPoint[] }) => {
    const { theme } = useTheme();

    if (history.length < 2) return null;

    // Theme-aware colors: lighter in dark mode, darker in light mode for visibility
    const cpuColor = theme === 'dark' ? '#a78bfa' : '#8b5cf6';
    const ramColor = theme === 'dark' ? '#34d399' : '#10b981';

    return (
        <div className="h-10 w-full mt-2">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
                    <Area
                        type="monotone"
                        dataKey="cpu"
                        stroke={cpuColor}
                        strokeWidth={1.5}
                        fill={cpuColor}
                        fillOpacity={0.1}
                        dot={false}
                        isAnimationActive={false}
                    />
                    <Area
                        type="monotone"
                        dataKey="ram"
                        stroke={ramColor}
                        strokeWidth={1.5}
                        fill={ramColor}
                        fillOpacity={0.1}
                        dot={false}
                        isAnimationActive={false}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

const NodeCard = ({ node, onUpgrade }: { node: Node; onUpgrade: (node: Node) => void }) => {
    const queryClient = useQueryClient();
    const isOnline = node.status === 'ONLINE' || node.status === 'ACTIVE' || node.status === 'BUSY';
    const isRevoked = node.status === 'REVOKED';
    const isTampered = node.status === 'TAMPERED';
    const cpu = node.stats?.cpu ?? 0;
    const ram = node.stats?.ram ?? 0;

    const cpuColor = cpu > 85 ? 'bg-red-500' : cpu > 60 ? 'bg-yellow-500' : 'bg-violet-500';
    const ramColor = ram > 85 ? 'bg-red-500' : ram > 60 ? 'bg-yellow-500' : 'bg-emerald-500';
    
    const [showHealth, setShowHealth] = useState(false);
    const [editing, setEditing] = useState(false);
    const [concurrency, setConcurrency] = useState(String(node.concurrency_limit ?? 5));
    const [memLimit, setMemLimit] = useState(node.job_memory_limit ?? '512m');
    const [tags, setTags] = useState(node.tags ? node.tags.join(', ') : '');
    const [envTag, setEnvTag] = useState(node.env_tag ?? '');
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [revoking, setRevoking] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [showRevokeConfirm, setShowRevokeConfirm] = useState(false);

    // Drift Detection Engine
    const checkDrift = () => {
        const reported = node.capabilities || {};
        const expected = node.expected_capabilities || {};
        const allTools = Array.from(new Set([...Object.keys(reported), ...Object.keys(expected)]));
        
        return allTools.map(tool => {
            const rVer = reported[tool];
            const eVer = expected[tool];
            if (eVer && !rVer) return { tool, status: 'MISSING' };
            if (!eVer && rVer) return { tool, status: 'UNAUTHORIZED' };
            if (eVer !== rVer) return { tool, status: 'VERSION_MISMATCH', expected: eVer, reported: rVer };
            return { tool, status: 'COMPLIANT' };
        });
    };

    const healthReport = checkDrift();
    const isDrifted = healthReport.some(r => r.status === 'MISSING' || r.status === 'VERSION_MISMATCH');

    const deleteNode = async () => {
        setDeleting(true);
        try {
            const res = await authenticatedFetch(`/nodes/${node.node_id}`, { method: 'DELETE' });
            if (res.ok) {
                toast.success(`Node ${node.hostname} removed from mesh`);
                queryClient.invalidateQueries({ queryKey: ['nodes'] });
            } else {
                toast.error(`Failed to remove node ${node.hostname}`);
            }
        } catch (e) {
            toast.error(`Error removing node: ${e instanceof Error ? e.message : 'Unknown error'}`);
        } finally {
            setDeleting(false);
            setShowDeleteConfirm(false);
        }
    };

    const revokeNode = async () => {
        setRevoking(true);
        try {
            const res = await authenticatedFetch(`/nodes/${node.node_id}/revoke`, { method: 'POST' });
            if (res.ok) {
                toast.success(`Node ${node.hostname} access revoked`);
                queryClient.invalidateQueries({ queryKey: ['nodes'] });
            } else {
                toast.error(`Failed to revoke node ${node.hostname}`);
            }
        } catch (e) {
            toast.error(`Error revoking node: ${e instanceof Error ? e.message : 'Unknown error'}`);
        } finally {
            setRevoking(false);
            setShowRevokeConfirm(false);
        }
    };

    const reinstateNode = async () => {
        setRevoking(true);
        try {
            const res = await authenticatedFetch(`/nodes/${node.node_id}/reinstate`, { method: 'POST' });
            if (res.ok) {
                toast.success(`Node ${node.hostname} access reinstated`);
                queryClient.invalidateQueries({ queryKey: ['nodes'] });
            } else {
                toast.error(`Failed to reinstate node ${node.hostname}`);
            }
        } catch (e) {
            toast.error(`Error reinstating node: ${e instanceof Error ? e.message : 'Unknown error'}`);
        } finally {
            setRevoking(false);
        }
    };

    const clearTamper = async () => {
        setSaving(true);
        try {
            const res = await authenticatedFetch(`/api/nodes/${node.node_id}/clear-tamper`, { method: 'POST' });
            if (res.ok) {
                toast.success(`Security alert cleared for ${node.hostname}`);
                queryClient.invalidateQueries({ queryKey: ['nodes'] });
            } else {
                toast.error('Failed to clear tamper alert');
            }
        } catch (e) {
            toast.error('Error communicating with server');
        } finally {
            setSaving(false);
        }
    };

    const saveConfig = async () => {
        setSaving(true);
        try {
            const tagsArray = tags.split(',').map(t => t.trim()).filter(Boolean);
            const res = await authenticatedFetch(`/nodes/${node.node_id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    concurrency_limit: parseInt(concurrency) || 5,
                    job_memory_limit: memLimit,
                    tags: tagsArray,
                    env_tag: envTag,
                }),
            });
            if (res.ok) {
                toast.success(`Node ${node.hostname} configuration updated`);
                queryClient.invalidateQueries({ queryKey: ['nodes'] });
                setEditing(false);
            } else {
                toast.error(`Failed to update node ${node.hostname}`);
            }
        } catch (e) {
            toast.error(`Error updating node: ${e instanceof Error ? e.message : 'Unknown error'}`);
        } finally {
            setSaving(false);
        }
    };

    const isDraining = node.status === 'DRAINING';

    const statusDot = isOnline
        ? <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
        : isDraining
            ? <div className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
            : isTampered
                ? <div className="h-2 w-2 rounded-full bg-red-600 animate-ping" />
                : isRevoked
                    ? <div className="h-2 w-2 rounded-full bg-amber-500" />
                    : <div className="h-2 w-2 rounded-full bg-red-500" />;

    const statusIcon = isOnline
        ? <ShieldCheck className="h-4 w-4 text-green-500" />
        : isDraining
            ? <PauseCircle className="h-4 w-4 text-amber-500" />
            : isTampered
                ? <ShieldAlert className="h-4 w-4 text-red-600 animate-pulse" />
                : isRevoked
                    ? <Ban className="h-4 w-4 text-amber-500" />
                    : <AlertTriangle className="h-4 w-4 text-red-500" />;

    return (
        <Card className={`overflow-hidden bg-card border-muted/50 ${isRevoked ? 'opacity-70' : ''}`}>
            <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Remove Node?</AlertDialogTitle>
                        <AlertDialogDescription>
                            {isOnline
                                ? `Are you sure you want to force-remove ${node.hostname}? It is currently ONLINE — this will not stop running jobs.`
                                : `Are you sure you want to remove ${node.hostname} from the mesh?`}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={deleteNode} disabled={deleting}>
                            {deleting ? 'Removing...' : 'Remove Node'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <AlertDialog open={showRevokeConfirm} onOpenChange={setShowRevokeConfirm}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Revoke Node Access?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to revoke {node.hostname}? It will be blocked from all orchestrator communication immediately.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={revokeNode} disabled={revoking}>
                            {revoking ? 'Revoking...' : 'Revoke Access'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex flex-col gap-1">
                    <CardTitle className="text-base font-medium flex items-center gap-2 text-foreground">
                        {node.hostname}
                        {statusDot}
                        {isRevoked && <span className="text-[10px] font-mono text-amber-500 border border-amber-500/30 rounded px-1">REVOKED</span>}
                        {isDraining && <span className="text-[10px] font-mono text-amber-400 border border-amber-400/30 rounded px-1">DRAINING</span>}
                        {node.env_tag && (
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getEnvTagBadgeClass(node.env_tag)}`}>
                                {node.env_tag.toUpperCase()}
                            </span>
                        )}
                        {node.detected_cgroup_version && (
                            <span
                                className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getCgroupBadgeClass(node.detected_cgroup_version)}`}
                                title={getCgroupTooltip(node.detected_cgroup_version)}
                            >
                                {getCgroupDisplayText(node.detected_cgroup_version)}
                            </span>
                        )}
                    </CardTitle>
                    <CardDescription className="text-xs font-mono text-muted-foreground">{node.ip}</CardDescription>
                </div>
                {statusIcon}
            </CardHeader>

            <CardContent className="space-y-4">
                {node.tags && node.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {node.tags.map(tag => (
                            <span key={tag} className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${getEnvBadgeColor(tag)}`}>{tag}</span>
                        ))}
                    </div>
                )}
                {isTampered && (
                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 space-y-1 animate-in zoom-in-95 duration-300">
                        <div className="flex items-center gap-2 text-red-500 text-xs font-bold uppercase tracking-wider">
                            <ShieldAlert className="h-3.5 w-3.5" /> Security Alert
                        </div>
                        <p className="text-[10px] text-red-200/70 leading-relaxed italic">
                            {node.tamper_details || 'Unauthorized runtime modifications detected.'}
                        </p>
                    </div>
                )}

                {/* Runtime Health Section */}
                <div className="space-y-2">
                    <button 
                        onClick={() => setShowHealth(!showHealth)}
                        className="flex items-center justify-between w-full text-[10px] font-bold uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors"
                    >
                        <span className="flex items-center gap-1.5">
                            <ShieldCheck className={`h-3 w-3 ${isDrifted ? 'text-amber-500' : 'text-muted-foreground'}`} />
                            Runtime Health
                        </span>
                        {isDrifted && <Badge variant="outline" className="h-4 px-1 text-[8px] border-amber-500/30 text-amber-500">Drift Detected</Badge>}
                    </button>
                    
                    {showHealth ? (
                        <div className="space-y-1.5 pt-1 animate-in slide-in-from-top-1 duration-200">
                            {healthReport.map(r => (
                                <div key={r.tool} className="flex items-center justify-between text-[10px] bg-black/20 p-1.5 rounded border border-muted">
                                    <span className="font-mono text-muted-foreground">{r.tool}</span>
                                    {r.status === 'COMPLIANT' && <CheckCircle2 className="h-3 w-3 text-green-500" />}
                                    {r.status === 'MISSING' && <Badge variant="outline" className="h-4 px-1 text-[8px] border-amber-500/30 text-amber-500">Pending Install</Badge>}
                                    {r.status === 'VERSION_MISMATCH' && <Badge variant="outline" className="h-4 px-1 text-[8px] border-amber-500/30 text-amber-500">Update Available</Badge>}
                                    {r.status === 'UNAUTHORIZED' && <Badge variant="outline" className="h-4 px-1 text-[8px] border-red-500/30 text-red-500 font-bold tracking-tighter">UNAUTHORIZED</Badge>}
                                </div>
                            ))}
                            {healthReport.length === 0 && <p className="text-[10px] text-muted-foreground/60 italic px-1">No tools authorized.</p>}
                        </div>
                    ) : (
                        <div className="flex flex-wrap gap-1">
                            {Object.entries(node.capabilities || {}).map(([cap, ver]) => (
                                <span key={cap} className="px-1.5 py-0.5 rounded bg-primary/10 text-[10px] font-mono border border-primary/20 text-primary/80">{cap}: {ver}</span>
                            ))}
                        </div>
                    )}
                </div>

                <div className="space-y-3">
                    <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span className="flex items-center gap-1.5"><Cpu className="h-3 w-3" /> CPU</span>
                            <span className="font-mono tabular-nums">{node.stats ? `${cpu}%` : '—'}</span>
                        </div>
                        <GaugeBar value={cpu} color={cpuColor} />
                    </div>
                    <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span className="flex items-center gap-1.5"><HardDrive className="h-3 w-3" /> RAM</span>
                            <span className="font-mono tabular-nums">{node.stats ? `${ram}%` : '—'}</span>
                        </div>
                        <GaugeBar value={ram} color={ramColor} />
                    </div>
                    {node.stats_history && <StatsSparkline history={node.stats_history} />}
                </div>
            </CardContent>

            <Separator className="bg-muted" />
            <CardFooter className="px-4 py-2 flex items-center justify-between gap-2" onClick={(e) => e.stopPropagation()}>
                {editing ? (
                    <div className="flex flex-col gap-2 w-full">
                        <div className="flex items-center gap-1.5 w-full">
                            <Input
                                type="number"
                                value={concurrency}
                                onChange={e => setConcurrency(e.target.value)}
                                className="h-7 w-14 bg-muted border-muted text-foreground text-xs px-2 font-mono"
                                min={1} max={50}
                                title="Max concurrent jobs"
                            />
                            <Input
                                value={memLimit}
                                onChange={e => setMemLimit(e.target.value)}
                                className="h-7 w-16 bg-muted border-muted text-foreground text-xs px-2 font-mono"
                                placeholder="512m"
                                title="Memory limit per job"
                            />
                            <Button size="icon" variant="ghost" className="h-7 w-7 text-green-400 hover:bg-green-500/10 ml-auto" onClick={saveConfig} disabled={saving} aria-label="Save configuration">
                                <Check className="h-3.5 w-3.5" />
                            </Button>
                            <Button size="icon" variant="ghost" className="h-7 w-7 text-muted-foreground hover:bg-muted" onClick={() => setEditing(false)} aria-label="Cancel editing">
                                <X className="h-3.5 w-3.5" />
                            </Button>
                        </div>
                        <div className="flex items-center gap-1.5 w-full">
                            <Input
                                value={tags}
                                onChange={e => setTags(e.target.value)}
                                className="h-7 flex-1 bg-muted border-muted text-foreground text-xs px-2 font-mono"
                                placeholder="tags: env:prod, secure"
                                title="Node tags (comma separated)"
                            />
                            <select
                                value={envTag}
                                onChange={e => setEnvTag(e.target.value)}
                                className="h-7 bg-muted border border-muted text-foreground text-xs px-1.5 rounded font-mono"
                                title="Environment tag"
                            >
                                <option value="">no env</option>
                                <option value="PROD">PROD</option>
                                <option value="TEST">TEST</option>
                                <option value="DEV">DEV</option>
                            </select>
                        </div>
                    </div>
                ) : (
                    <>
                        <span className="text-xs text-muted-foreground/60">
                            {node.concurrency_limit ? `${node.concurrency_limit} workers · ${node.job_memory_limit}` : node.version || 'Unknown'}
                        </span>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground/60">{new Date(node.last_seen).toLocaleTimeString()}</span>
                            {isRevoked ? (
                                <>
                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-emerald-600 hover:text-emerald-400 hover:bg-emerald-500/10 rounded" onClick={reinstateNode} disabled={revoking} title="Reinstate node" aria-label="Reinstate node">
                                        <RotateCcw className="h-3 w-3" />
                                    </Button>
                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-red-700 hover:text-red-400 hover:bg-red-500/10 rounded" onClick={() => setShowDeleteConfirm(true)} disabled={deleting} title="Remove node" aria-label="Remove node">
                                        <Trash2 className="h-3 w-3" />
                                    </Button>
                                </>
                            ) : (
                                <>
                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-muted-foreground/60 hover:text-amber-400 hover:bg-amber-500/10 rounded" onClick={() => setShowRevokeConfirm(true)} disabled={revoking} title="Revoke node access" aria-label="Revoke node access">
                                        <Ban className="h-3 w-3" />
                                    </Button>
                                    <Button size="icon" variant="ghost" className={`h-6 w-6 rounded ${isOnline ? 'text-muted-foreground/40 hover:text-red-400 hover:bg-red-500/10' : 'text-red-700 hover:text-red-400 hover:bg-red-500/10'}`} onClick={() => setShowDeleteConfirm(true)} disabled={deleting} title={isOnline ? 'Force-remove (node is online)' : 'Remove node'} aria-label={isOnline ? 'Force-remove (node is online)' : 'Remove node'}>
                                        <Trash2 className="h-3 w-3" />
                                    </Button>
                                </>
                            )}
                            {isTampered && (
                                <Button size="sm" variant="ghost" className="h-6 px-2 text-[10px] font-bold text-red-500 hover:text-red-400 hover:bg-red-500/10 rounded gap-1" onClick={clearTamper} disabled={saving}>
                                    <RotateCcw className="h-3 w-3" /> Clear Alert
                                </Button>
                            )}
                            <Button size="icon" variant="ghost" className="h-6 w-6 text-muted-foreground/60 hover:text-primary hover:bg-primary/10 rounded" onClick={() => onUpgrade(node)} title="Hot-Upgrade Runtime" aria-label="Hot-Upgrade Runtime">
                                <Zap className="h-3 w-3" />
                            </Button>
                            <Button size="icon" variant="ghost" className="h-6 w-6 text-muted-foreground/60 hover:text-foreground hover:bg-muted rounded" onClick={() => setEditing(true)} aria-label="Configure node">
                                <Settings2 className="h-3 w-3" />
                            </Button>
                        </div>
                    </>
                )}
            </CardFooter>
        </Card>
    );
};

const Nodes = () => {
    const queryClient = useQueryClient();
    const currentUser = getUser();
    const [showAddModal, setShowAddModal] = useState(false);
    const [showMountsModal, setShowMountsModal] = useState(false);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [selectedNode, setSelectedNode] = useState<Node | null>(null);
    const [page, setPage] = useState(1);

    // Node detail drawer state
    const [drawerNode, setDrawerNode] = useState<Node | null>(null);
    const [nodeDrawerOpen, setNodeDrawerOpen] = useState(false);
    const [nodeDetail, setNodeDetail] = useState<NodeDetail | null>(null);
    const [nodeDetailLoading, setNodeDetailLoading] = useState(false);

    const { data: pageData, isLoading } = useQuery({
        queryKey: ['nodes', page],
        queryFn: () => fetchNodes(page),
        refetchInterval: 10000,
    });

    const nodes = pageData?.items ?? [];
    const totalNodes = pageData?.total ?? 0;
    const totalPages = pageData?.pages ?? 1;

    useWebSocket((event) => {
        if (event === 'node:heartbeat' || event === 'node:updated') queryClient.invalidateQueries({ queryKey: ['nodes', page] });
    });

    const handleNodeClick = async (node: Node) => {
        setDrawerNode(node);
        setNodeDrawerOpen(true);
        setNodeDetail(null);
        setNodeDetailLoading(true);
        try {
            const res = await authenticatedFetch(`/nodes/${node.node_id}/detail`);
            if (res.ok) setNodeDetail(await res.json());
        } catch { /* non-critical */ }
        finally { setNodeDetailLoading(false); }
    };

    const handleDrain = async (nodeId: string) => {
        const res = await authenticatedFetch(`/nodes/${nodeId}/drain`, { method: 'PATCH' });
        if (res.ok) {
            toast.success('Node set to DRAINING');
            setNodeDrawerOpen(false);
            queryClient.invalidateQueries({ queryKey: ['nodes'] });
        } else {
            const err = await res.json().catch(() => ({}));
            toast.error((err as any).detail || 'Failed to drain node');
        }
    };

    const handleUndrain = async (nodeId: string) => {
        const res = await authenticatedFetch(`/nodes/${nodeId}/undrain`, { method: 'PATCH' });
        if (res.ok) {
            toast.success('Node returned to ONLINE');
            setNodeDrawerOpen(false);
            queryClient.invalidateQueries({ queryKey: ['nodes'] });
        } else {
            const err = await res.json().catch(() => ({}));
            toast.error((err as any).detail || 'Failed to undrain node');
        }
    };

    const [envFilter, setEnvFilter] = useState<string>('ALL');

    const uniqueEnvTags = useMemo(() => {
        const tags = nodes
            .map(n => n.env_tag)
            .filter((t): t is string => !!t);
        return Array.from(new Set(tags)).sort();
    }, [nodes]);

    const displayNodes = nodes.filter(n =>
        envFilter === 'ALL' || n.env_tag === envFilter
    );

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-foreground">Nodes</h1>
                    <p className="text-sm text-muted-foreground mt-1">
                        Real-time telemetry for {totalNodes} active nodes.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" className="border-muted text-foreground hover:text-foreground" onClick={() => setShowMountsModal(true)}>
                        <Network className="mr-2 h-4 w-4" />
                        Network Mounts
                    </Button>
                    <Button className="bg-primary hover:bg-primary/90 text-foreground font-bold" onClick={() => setShowAddModal(true)}>
                        <Server className="mr-2 h-4 w-4" />
                        Provision Node
                    </Button>
                </div>
            </div>

            {(uniqueEnvTags.length > 0) && (
                <div className="flex items-center gap-3">
                    <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider whitespace-nowrap">
                        Filter by environment:
                    </label>
                    <Select value={envFilter} onValueChange={setEnvFilter}>
                        <SelectTrigger className="w-44 bg-secondary border-muted text-foreground h-9">
                            <SelectValue placeholder="All" />
                        </SelectTrigger>
                        <SelectContent className="bg-secondary border-muted text-foreground">
                            <SelectItem value="ALL">All</SelectItem>
                            {uniqueEnvTags.map(tag => (
                                <SelectItem key={tag} value={tag}>{tag}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            )}

            {(() => {
                const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
                const degradedNodes = onlineNodes.filter(
                    n => n.detected_cgroup_version && n.detected_cgroup_version !== 'v2'
                );
                const v1Count = degradedNodes.filter(n => n.detected_cgroup_version === 'v1').length;
                const unsupportedCount = degradedNodes.filter(n => n.detected_cgroup_version === 'unsupported').length;

                return degradedNodes.length > 0 ? (
                    <div className="mb-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                        <div className="text-sm text-amber-700">
                            <strong>{degradedNodes.length} of {onlineNodes.length} nodes have degraded cgroup support</strong>
                            {v1Count > 0 && <div className="text-xs mt-1">• {v1Count} node{v1Count !== 1 ? 's' : ''} running cgroup v1 (limited enforcement)</div>}
                            {unsupportedCount > 0 && <div className="text-xs mt-1">• {unsupportedCount} node{unsupportedCount !== 1 ? 's' : ''} with unsupported cgroups (no enforcement)</div>}
                        </div>
                    </div>
                ) : null;
            })()}

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {isLoading ? (
                    Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="h-[220px] rounded-xl border border-muted bg-secondary animate-pulse" />
                    ))
                ) : displayNodes.length ? (
                    displayNodes.map(node => (
                        <div
                            key={node.node_id}
                            onClick={() => handleNodeClick(node)}
                            className="cursor-pointer"
                        >
                            <NodeCard
                                node={node}
                                onUpgrade={(n) => { setSelectedNode(n); setShowUpgradeModal(true); }}
                            />
                        </div>
                    ))
                ) : (
                    <div className="col-span-full py-20 text-center rounded-2xl border border-dashed border-muted bg-secondary/20">
                        <Server className="h-12 w-12 text-muted mx-auto mb-4" />
                        <h3 className="text-muted-foreground font-medium">
                            {envFilter !== 'ALL' ? 'No nodes match this environment filter' : 'No nodes enrolled'}
                        </h3>
                        <p className="text-muted-foreground/60 text-sm mt-1">
                            {envFilter !== 'ALL' ? `Showing nodes tagged "${envFilter}" only.` : 'Click "Provision Puppet" to enroll your first node.'}
                        </p>
                    </div>
                )}
            </div>

            {/* Pagination controls */}
            {(totalPages > 1 || totalNodes > 0) && (
                <div className="flex items-center justify-between mt-2">
                    <span className="text-sm text-muted-foreground text-muted-foreground">
                        Showing {nodes.length} of {totalNodes} nodes
                    </span>
                    {totalPages > 1 && (
                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                className="border-muted text-foreground hover:text-foreground disabled:opacity-40"
                                disabled={page <= 1}
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                            >
                                Previous
                            </Button>
                            <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
                            <Button
                                variant="outline"
                                size="sm"
                                className="border-muted text-foreground hover:text-foreground disabled:opacity-40"
                                disabled={page >= totalPages}
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            >
                                Next
                            </Button>
                        </div>
                    )}
                </div>
            )}

            <AddNodeModal open={showAddModal} onOpenChange={setShowAddModal} />
            <ManageMountsModal open={showMountsModal} onOpenChange={setShowMountsModal} />
            {selectedNode && (
                <HotUpgradeModal
                    node={selectedNode}
                    open={showUpgradeModal}
                    onOpenChange={setShowUpgradeModal}
                />
            )}

            {/* Node Detail Drawer */}
            <Sheet open={nodeDrawerOpen} onOpenChange={setNodeDrawerOpen}>
                <SheetContent className="bg-secondary border-muted text-foreground w-full sm:max-w-xl overflow-y-auto">
                    <SheetHeader className="pb-4 border-b border-muted">
                        <SheetTitle className="text-foreground flex items-center gap-2">
                            <Server className="h-4 w-4" /> {drawerNode?.hostname}
                        </SheetTitle>
                        <SheetDescription className="font-mono text-muted-foreground text-xs">
                            {drawerNode?.node_id}
                        </SheetDescription>
                    </SheetHeader>

                    <div className="space-y-6 pt-6">
                        {/* Drain / Un-drain action — admin only */}
                        {currentUser?.role === 'admin' && drawerNode && (
                            drawerNode.status === 'DRAINING'
                                ? (
                                    <Button
                                        variant="outline"
                                        className="w-full border-green-500/40 text-green-400 hover:bg-green-500/10 hover:text-green-300"
                                        onClick={() => handleUndrain(drawerNode.node_id)}
                                    >
                                        <RotateCcw className="mr-2 h-4 w-4" /> Un-drain Node
                                    </Button>
                                )
                                : (drawerNode.status === 'ONLINE' || drawerNode.status === 'BUSY') && (
                                    <Button
                                        variant="outline"
                                        className="w-full border-amber-500/40 text-amber-400 hover:bg-amber-500/10 hover:text-amber-300"
                                        onClick={() => handleDrain(drawerNode.node_id)}
                                    >
                                        <PauseCircle className="mr-2 h-4 w-4" /> Drain Node
                                    </Button>
                                )
                        )}

                        {/* Running job */}
                        <div>
                            <h3 className="text-sm font-semibold text-foreground mb-2">Running Job</h3>
                            {nodeDetailLoading ? (
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                            ) : nodeDetail?.running_job ? (
                                <div className="font-mono text-xs text-foreground bg-muted p-2 rounded">
                                    <span className="text-muted-foreground">{nodeDetail.running_job.name || nodeDetail.running_job.guid}</span>
                                    <Badge variant="outline" className="ml-2 text-[10px] border-yellow-500/30 text-yellow-400">
                                        {nodeDetail.running_job.status}
                                    </Badge>
                                </div>
                            ) : (
                                <p className="text-xs text-muted-foreground">No job currently running</p>
                            )}
                        </div>

                        {/* Eligible pending jobs */}
                        <div>
                            <h3 className="text-sm font-semibold text-foreground mb-2">
                                Eligible Pending Jobs ({nodeDetail?.eligible_pending_jobs?.length ?? 0})
                            </h3>
                            {!nodeDetailLoading && nodeDetail?.eligible_pending_jobs?.length === 0 && (
                                <p className="text-xs text-muted-foreground">No pending jobs eligible for this node</p>
                            )}
                            {nodeDetail?.eligible_pending_jobs?.slice(0, 10).map(j => (
                                <div key={j.guid} className="text-xs text-muted-foreground font-mono py-1 border-b border-muted">
                                    {j.name || j.guid.slice(0, 8)}
                                </div>
                            ))}
                        </div>

                        {/* Recent history */}
                        <div>
                            <h3 className="text-sm font-semibold text-foreground mb-2">Recent History (24h)</h3>
                            {!nodeDetailLoading && nodeDetail?.recent_history?.length === 0 && (
                                <p className="text-xs text-muted-foreground">No completed jobs in the last 24 hours</p>
                            )}
                            {nodeDetail?.recent_history?.slice(0, 10).map(j => (
                                <div key={j.guid} className="flex items-center justify-between text-xs py-1 border-b border-muted">
                                    <span className="font-mono text-muted-foreground">{j.name || j.guid.slice(0, 8)}</span>
                                    <Badge
                                        variant="outline"
                                        className={j.status === 'COMPLETED' ? 'border-green-500/30 text-green-400' : 'border-red-500/30 text-red-400'}
                                    >
                                        {j.status}
                                    </Badge>
                                </div>
                            ))}
                        </div>

                        {/* Capabilities */}
                        <div>
                            <h3 className="text-sm font-semibold text-foreground mb-2">Capabilities</h3>
                            {Object.keys(nodeDetail?.capabilities ?? {}).length === 0
                                ? <p className="text-xs text-muted-foreground">No capabilities reported</p>
                                : (
                                    <div className="flex flex-wrap gap-1">
                                        {Object.entries(nodeDetail?.capabilities ?? {}).map(([name, ver]) => (
                                            <Badge key={name} variant="outline" className="text-xs border-muted text-foreground">
                                                {name} {ver}
                                            </Badge>
                                        ))}
                                    </div>
                                )
                            }
                        </div>
                    </div>
                </SheetContent>
            </Sheet>
        </div>
    );
};

export default Nodes;
