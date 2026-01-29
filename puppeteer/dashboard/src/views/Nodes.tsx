import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Area, AreaChart, ResponsiveContainer, YAxis } from 'recharts';
import {
    Server,
    Activity,
    ShieldCheck,
    AlertTriangle,
    MoreVertical,
    Cpu,
    HardDrive
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
// import AddNodeModal from '../components/AddNodeModal'; // TODO: Migrate
// import ManageMountsModal from '../components/ManageMountsModal'; // TODO: Migrate
import { authenticatedFetch } from '../auth'; // Assume this is effectively JS/TS compatible or needs types

// Mock history generator since backend only gives point-in-time
const generateMockHistory = (currentVal: number) => {
    return Array.from({ length: 20 }, (_, i) => ({
        value: Math.max(0, Math.min(100, currentVal + (Math.random() * 20 - 10)))
    }));
};

interface NodeStats {
    cpu: number;
    ram: number;
}

interface Node {
    node_id: string;
    hostname: string;
    ip: string;
    status: 'ONLINE' | 'OFFLINE' | 'BUSY';
    last_seen: string;
    stats?: NodeStats;
    version?: string;
    role?: string;
    tags?: string[];
}

const fetchNodes = async (): Promise<Node[]> => {
    const res = await authenticatedFetch('/nodes');
    if (!res.ok) throw new Error("Failed to fetch nodes");
    return await res.json();
};

const NodeCard = ({ node }: { node: Node }) => {
    const isOnline = node.status === 'ONLINE';
    const cpuData = generateMockHistory(node.stats?.cpu || 0);
    const ramData = generateMockHistory(node.stats?.ram || 0);

    return (
        <Card className="overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex flex-col gap-1">
                    <CardTitle className="text-base font-medium flex items-center gap-2">
                        {node.hostname}
                        {isOnline ? (
                            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                        ) : (
                            <div className="h-2 w-2 rounded-full bg-red-500" />
                        )}
                    </CardTitle>
                    <CardDescription className="text-xs font-mono">{node.ip}</CardDescription>
                </div>
                {isOnline ? <ShieldCheck className="h-4 w-4 text-green-500" /> : <AlertTriangle className="h-4 w-4 text-red-500" />}
            </CardHeader>
            <CardContent>
                {node.tags && node.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-4">
                        {node.tags.map(tag => (
                            <span key={tag} className="px-1.5 py-0.5 rounded bg-muted text-[10px] font-medium border border-border">
                                {tag}
                            </span>
                        ))}
                    </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Cpu className="h-3 w-3" /> CPU {node.stats?.cpu}%
                        </div>
                        <div className="h-[40px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={cpuData}>
                                    <defs>
                                        <linearGradient id={`cpu-${node.node_id}`} x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#8884d8" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <Area
                                        type="monotone"
                                        dataKey="value"
                                        stroke="#8884d8"
                                        fillOpacity={1}
                                        fill={`url(#cpu-${node.node_id})`}
                                        strokeWidth={1.5}
                                        isAnimationActive={false} // Disable animation for "Medical" feel
                                    />
                                    <YAxis domain={[0, 100]} hide />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                    <div className="space-y-1">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <HardDrive className="h-3 w-3" /> RAM {node.stats?.ram}%
                        </div>
                        <div className="h-[40px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={ramData}>
                                    <defs>
                                        <linearGradient id={`ram-${node.node_id}`} x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#82ca9d" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <Area
                                        type="monotone"
                                        dataKey="value"
                                        stroke="#82ca9d"
                                        fillOpacity={1}
                                        fill={`url(#ram-${node.node_id})`}
                                        strokeWidth={1.5}
                                        isAnimationActive={false}
                                    />
                                    <YAxis domain={[0, 100]} hide />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>
            </CardContent>
            <Separator />
            <CardFooter className="bg-muted/50 px-6 py-2 text-xs text-muted-foreground flex justify-between">
                <span>{node.version || 'Unknown'}</span>
                <span>{new Date(node.last_seen).toLocaleTimeString()}</span>
            </CardFooter>
        </Card>
    );
};

const Nodes = () => {
    const { data: nodes, isLoading } = useQuery({
        queryKey: ['nodes'],
        queryFn: fetchNodes,
        refetchInterval: 3000 // 3s Heartbeat
    });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">Puppet Mesh</h2>
                    <p className="text-muted-foreground">
                        Real-time telemetry and control plane for {nodes?.length || 0} active puppets.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline">
                        <NetworkIcon className="mr-2 h-4 w-4" />
                        Network Mounts
                    </Button>
                    <Button>
                        <Server className="mr-2 h-4 w-4" />
                        Provision Puppet
                    </Button>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {isLoading ? (
                    // Skeletons
                    Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="h-[180px] rounded-xl border bg-card text-card-foreground shadow-sm animate-pulse" />
                    ))
                ) : (
                    nodes?.map((node) => (
                        <NodeCard key={node.node_id} node={node} />
                    ))
                )}
            </div>
        </div>
    );
};

function NetworkIcon(props: any) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <rect x="16" y="16" width="6" height="6" rx="1" />
            <rect x="2" y="16" width="6" height="6" rx="1" />
            <rect x="9" y="2" width="6" height="6" rx="1" />
            <path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3" />
            <path d="M12 12V8" />
        </svg>
    )
}

export default Nodes;
