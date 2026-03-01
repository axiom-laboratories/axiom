import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import {
    Server,
    ShieldCheck,
    AlertTriangle,
    Cpu,
    HardDrive,
    Network,
    Settings2,
    Check,
    X,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import AddNodeModal from '../components/AddNodeModal';
import ManageMountsModal from '../components/ManageMountsModal';
import { authenticatedFetch } from '../auth';

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
    status: 'ONLINE' | 'OFFLINE' | 'BUSY';
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
    const cpu = node.stats?.cpu ?? 0;
    const ram = node.stats?.ram ?? 0;

    const cpuColor = cpu > 85 ? 'bg-red-500' : cpu > 60 ? 'bg-yellow-500' : 'bg-violet-500';
    const ramColor = ram > 85 ? 'bg-red-500' : ram > 60 ? 'bg-yellow-500' : 'bg-emerald-500';
    const capabilities = node.capabilities ? Object.entries(node.capabilities) : [];

    const [editing, setEditing] = useState(false);
    const [concurrency, setConcurrency] = useState(String(node.concurrency_limit ?? 5));
    const [memLimit, setMemLimit] = useState(node.job_memory_limit ?? '512m');
    const [saving, setSaving] = useState(false);

    const saveConfig = async () => {
        setSaving(true);
        try {
            const res = await authenticatedFetch(`/nodes/${node.node_id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ concurrency_limit: parseInt(concurrency) || 5, job_memory_limit: memLimit }),
            });
            if (res.ok) {
                queryClient.invalidateQueries({ queryKey: ['nodes'] });
                setEditing(false);
            }
        } finally {
            setSaving(false);
        }
    };

    return (
        <Card className="overflow-hidden bg-zinc-925 border-zinc-800/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex flex-col gap-1">
                    <CardTitle className="text-base font-medium flex items-center gap-2 text-white">
                        {node.hostname}
                        {isOnline
                            ? <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                            : <div className="h-2 w-2 rounded-full bg-red-500" />
                        }
                    </CardTitle>
                    <CardDescription className="text-xs font-mono text-zinc-500">{node.ip}</CardDescription>
                </div>
                {isOnline
                    ? <ShieldCheck className="h-4 w-4 text-green-500" />
                    : <AlertTriangle className="h-4 w-4 text-red-500" />
                }
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
                        <Button size="icon" variant="ghost" className="h-7 w-7 text-green-400 hover:bg-green-500/10 ml-auto" onClick={saveConfig} disabled={saving}>
                            <Check className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="icon" variant="ghost" className="h-7 w-7 text-zinc-500 hover:bg-zinc-800" onClick={() => setEditing(false)}>
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
                            <Button size="icon" variant="ghost" className="h-6 w-6 text-zinc-600 hover:text-white hover:bg-zinc-800 rounded" onClick={() => setEditing(true)}>
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
    const [showAddModal, setShowAddModal] = useState(false);
    const [showMountsModal, setShowMountsModal] = useState(false);

    const { data: nodes, isLoading } = useQuery({
        queryKey: ['nodes'],
        queryFn: fetchNodes,
        refetchInterval: 3000,
    });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight text-white">Puppet Mesh</h2>
                    <p className="text-zinc-500">
                        Real-time telemetry and control plane for {nodes?.length || 0} active puppets.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" className="border-zinc-700 text-zinc-300 hover:text-white" onClick={() => setShowMountsModal(true)}>
                        <Network className="mr-2 h-4 w-4" />
                        Network Mounts
                    </Button>
                    <Button className="bg-primary hover:bg-primary/90 text-white font-bold" onClick={() => setShowAddModal(true)}>
                        <Server className="mr-2 h-4 w-4" />
                        Provision Puppet
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
