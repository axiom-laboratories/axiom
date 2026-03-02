import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import {
    Server,
    ShieldCheck,
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
} from 'lucide-react';
import { toast } from 'sonner';

import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
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
import AddNodeModal from '../components/AddNodeModal';
import ManageMountsModal from '../components/ManageMountsModal';
import { authenticatedFetch } from '../auth';
import { useWebSocket } from '../hooks/useWebSocket';

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
    status: 'ONLINE' | 'OFFLINE' | 'BUSY' | 'REVOKED';
    last_seen: string;
    stats?: NodeStats;
    version?: string;
    tags?: string[];
    capabilities?: Record<string, string>;
    concurrency_limit?: number;
    job_memory_limit?: string;
    stats_history?: StatPoint[];
}

const fetchNodes = async (): Promise<Node[]> => {
    const res = await authenticatedFetch('/nodes');
    if (!res.ok) throw new Error('Failed to fetch nodes');
    return await res.json();
};

const GaugeBar = ({ value, color }: { value: number; color: string }) => (
    <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
        <div
            className={`h-full rounded-full transition-all duration-500 ${color}`}
            style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
    </div>
);

const StatsSparkline = ({ history }: { history: StatPoint[] }) => {
    if (history.length < 2) return null;
    return (
        <div className="h-10 w-full mt-2">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
                    <Area
                        type="monotone"
                        dataKey="cpu"
                        stroke="#8b5cf6"
                        strokeWidth={1.5}
                        fill="#8b5cf6"
                        fillOpacity={0.1}
                        dot={false}
                        isAnimationActive={false}
                    />
                    <Area
                        type="monotone"
                        dataKey="ram"
                        stroke="#10b981"
                        strokeWidth={1.5}
                        fill="#10b981"
                        fillOpacity={0.1}
                        dot={false}
                        isAnimationActive={false}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

const NodeCard = ({ node }: { node: Node }) => {
    const queryClient = useQueryClient();
    const isOnline = node.status === 'ONLINE';
    const isRevoked = node.status === 'REVOKED';
    const cpu = node.stats?.cpu ?? 0;
    const ram = node.stats?.ram ?? 0;

    const cpuColor = cpu > 85 ? 'bg-red-500' : cpu > 60 ? 'bg-yellow-500' : 'bg-violet-500';
    const ramColor = ram > 85 ? 'bg-red-500' : ram > 60 ? 'bg-yellow-500' : 'bg-emerald-500';
    const capabilities = node.capabilities ? Object.entries(node.capabilities) : [];

    const [editing, setEditing] = useState(false);
    const [concurrency, setConcurrency] = useState(String(node.concurrency_limit ?? 5));
    const [memLimit, setMemLimit] = useState(node.job_memory_limit ?? '512m');
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [revoking, setRevoking] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [showRevokeConfirm, setShowRevokeConfirm] = useState(false);

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

    const saveConfig = async () => {
        setSaving(true);
        try {
            const res = await authenticatedFetch(`/nodes/${node.node_id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ concurrency_limit: parseInt(concurrency) || 5, job_memory_limit: memLimit }),
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

    const statusDot = isOnline
        ? <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
        : isRevoked
            ? <div className="h-2 w-2 rounded-full bg-amber-500" />
            : <div className="h-2 w-2 rounded-full bg-red-500" />;

    const statusIcon = isOnline
        ? <ShieldCheck className="h-4 w-4 text-green-500" />
        : isRevoked
            ? <Ban className="h-4 w-4 text-amber-500" />
            : <AlertTriangle className="h-4 w-4 text-red-500" />;

    return (
        <Card className={`overflow-hidden bg-zinc-925 border-zinc-800/50 ${isRevoked ? 'opacity-70' : ''}`}>
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
                    <CardTitle className="text-base font-medium flex items-center gap-2 text-white">
                        {node.hostname}
                        {statusDot}
                        {isRevoked && <span className="text-[10px] font-mono text-amber-500 border border-amber-500/30 rounded px-1">REVOKED</span>}
                    </CardTitle>
                    <CardDescription className="text-xs font-mono text-zinc-500">{node.ip}</CardDescription>
                </div>
                {statusIcon}
            </CardHeader>

            <CardContent className="space-y-4">
                {node.tags && node.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {node.tags.map(tag => (
                            <span key={tag} className="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] font-medium border border-zinc-700 text-zinc-400">{tag}</span>
                        ))}
                    </div>
                )}
                {capabilities.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {capabilities.map(([cap, ver]) => (
                            <span key={cap} className="px-1.5 py-0.5 rounded bg-primary/10 text-[10px] font-mono border border-primary/20 text-primary/80">{cap}: {ver}</span>
                        ))}
                    </div>
                )}
                <div className="space-y-3">
                    <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-zinc-500">
                            <span className="flex items-center gap-1.5"><Cpu className="h-3 w-3" /> CPU</span>
                            <span className="font-mono tabular-nums">{node.stats ? `${cpu}%` : '—'}</span>
                        </div>
                        <GaugeBar value={cpu} color={cpuColor} />
                    </div>
                    <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-zinc-500">
                            <span className="flex items-center gap-1.5"><HardDrive className="h-3 w-3" /> RAM</span>
                            <span className="font-mono tabular-nums">{node.stats ? `${ram}%` : '—'}</span>
                        </div>
                        <GaugeBar value={ram} color={ramColor} />
                    </div>
                    {node.stats_history && <StatsSparkline history={node.stats_history} />}
                </div>
            </CardContent>

            <Separator className="bg-zinc-800" />
            <CardFooter className="px-4 py-2 flex items-center justify-between gap-2">
                {editing ? (
                    <div className="flex items-center gap-1.5 w-full">
                        <Input
                            type="number"
                            value={concurrency}
                            onChange={e => setConcurrency(e.target.value)}
                            className="h-7 w-14 bg-zinc-800 border-zinc-700 text-white text-xs px-2 font-mono"
                            min={1} max={50}
                            title="Max concurrent jobs"
                        />
                        <Input
                            value={memLimit}
                            onChange={e => setMemLimit(e.target.value)}
                            className="h-7 w-16 bg-zinc-800 border-zinc-700 text-white text-xs px-2 font-mono"
                            placeholder="512m"
                            title="Memory limit per job"
                        />
                        <Button size="icon" variant="ghost" className="h-7 w-7 text-green-400 hover:bg-green-500/10 ml-auto" onClick={saveConfig} disabled={saving} aria-label="Save configuration">
                            <Check className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="icon" variant="ghost" className="h-7 w-7 text-zinc-500 hover:bg-zinc-800" onClick={() => setEditing(false)} aria-label="Cancel editing">
                            <X className="h-3.5 w-3.5" />
                        </Button>
                    </div>
                ) : (
                    <>
                        <span className="text-xs text-zinc-600">
                            {node.concurrency_limit ? `${node.concurrency_limit} workers · ${node.job_memory_limit}` : node.version || 'Unknown'}
                        </span>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-zinc-600">{new Date(node.last_seen).toLocaleTimeString()}</span>
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
                                    <Button size="icon" variant="ghost" className="h-6 w-6 text-zinc-600 hover:text-amber-400 hover:bg-amber-500/10 rounded" onClick={() => setShowRevokeConfirm(true)} disabled={revoking} title="Revoke node access" aria-label="Revoke node access">
                                        <Ban className="h-3 w-3" />
                                    </Button>
                                    <Button size="icon" variant="ghost" className={`h-6 w-6 rounded ${isOnline ? 'text-zinc-700 hover:text-red-400 hover:bg-red-500/10' : 'text-red-700 hover:text-red-400 hover:bg-red-500/10'}`} onClick={() => setShowDeleteConfirm(true)} disabled={deleting} title={isOnline ? 'Force-remove (node is online)' : 'Remove node'} aria-label={isOnline ? 'Force-remove (node is online)' : 'Remove node'}>
                                        <Trash2 className="h-3 w-3" />
                                    </Button>
                                </>
                            )}
                            <Button size="icon" variant="ghost" className="h-6 w-6 text-zinc-600 hover:text-white hover:bg-zinc-800 rounded" onClick={() => setEditing(true)} aria-label="Configure node">
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
    const [showAddModal, setShowAddModal] = useState(false);
    const [showMountsModal, setShowMountsModal] = useState(false);

    const { data: nodes, isLoading } = useQuery({
        queryKey: ['nodes'],
        queryFn: fetchNodes,
        refetchInterval: 10000,
    });

    useWebSocket((event) => {
        if (event === 'node:heartbeat') queryClient.invalidateQueries({ queryKey: ['nodes'] });
    });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-white">Nodes</h1>
                    <p className="text-sm text-zinc-500 mt-1">
                        Real-time telemetry for {nodes?.length || 0} active nodes.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" className="border-zinc-700 text-zinc-300 hover:text-white" onClick={() => setShowMountsModal(true)}>
                        <Network className="mr-2 h-4 w-4" />
                        Network Mounts
                    </Button>
                    <Button className="bg-primary hover:bg-primary/90 text-white font-bold" onClick={() => setShowAddModal(true)}>
                        <Server className="mr-2 h-4 w-4" />
                        Provision Node
                    </Button>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {isLoading ? (
                    Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="h-[220px] rounded-xl border border-zinc-800 bg-zinc-900 animate-pulse" />
                    ))
                ) : nodes?.length ? (
                    nodes.map(node => <NodeCard key={node.node_id} node={node} />)
                ) : (
                    <div className="col-span-full py-20 text-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20">
                        <Server className="h-12 w-12 text-zinc-800 mx-auto mb-4" />
                        <h3 className="text-zinc-400 font-medium">No nodes enrolled</h3>
                        <p className="text-zinc-600 text-sm mt-1">Click "Provision Puppet" to enroll your first node.</p>
                    </div>
                )}
            </div>

            <AddNodeModal open={showAddModal} onOpenChange={setShowAddModal} />
            <ManageMountsModal open={showMountsModal} onOpenChange={setShowMountsModal} />
        </div>
    );
};

export default Nodes;
