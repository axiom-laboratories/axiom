import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { authenticatedFetch } from '../auth';
import { useFeatures } from '../hooks/useFeatures';
import { UpgradePlaceholder } from '../components/UpgradePlaceholder';
import { 
    Table, 
    TableBody, 
    TableCell, 
    TableHead, 
    TableHeader, 
    TableRow 
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
    Select, 
    SelectContent, 
    SelectItem, 
    SelectTrigger, 
    SelectValue 
} from '@/components/ui/select';
import { formatDistanceToNow } from 'date-fns';
import { Terminal, Search, Filter } from 'lucide-react';
import { ExecutionLogModal } from '../components/ExecutionLogModal';

const History = () => {
    const features = useFeatures();
    const [page, setPage] = useState(0);
    const [nodeId, setNodeId] = useState('');
    const [status, setStatus] = useState('ALL');
    const [jobGuid, setJobGuid] = useState('');
    const [definitionId, setDefinitionId] = useState('');
    const [selectedEx, setSelectedEx] = useState<number | null>(null);
    const limit = 25;

    const { data: definitions } = useQuery({
        queryKey: ['definitions-for-filter'],
        queryFn: async () => {
            const res = await authenticatedFetch('/jobs/definitions');
            return res.json() as Promise<Array<{ id: string; name: string }>>;
        }
    });

    const { data: executions, isLoading } = useQuery({
        queryKey: ['executions', page, nodeId, status, jobGuid, definitionId],
        queryFn: async () => {
            let url = `/api/executions?skip=${page * limit}&limit=${limit}`;
            if (nodeId) url += `&node_id=${nodeId}`;
            if (status !== 'ALL') url += `&status=${status}`;
            if (jobGuid) url += `&job_guid=${jobGuid}`;
            if (definitionId) url += `&scheduled_job_id=${definitionId}`;

            const res = await authenticatedFetch(url);
            return res.json();
        }
    });

    const getStatusVariant = (status: string) => {
        switch (status) {
            case 'COMPLETED': return 'default';
            case 'FAILED': return 'destructive';
            case 'SECURITY_REJECTED': return 'destructive';
            case 'DEAD_LETTER': return 'destructive';
            case 'RETRYING': return 'outline';
            default: return 'outline';
        }
    };

    if (!features.executions) {
        return <UpgradePlaceholder feature="Execution History" description="Full audit trail of all task executions, results, and attestations across the mesh." />;
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight text-white">Execution History</h2>
                    <p className="text-zinc-500">Audit trail of all tasks across the network.</p>
                </div>
            </div>

            {/* Filter Bar */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-zinc-900/50 p-4 rounded-xl border border-zinc-900 shadow-sm">
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-1">Job GUID</label>
                    <div className="relative">
                        <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                        <Input 
                            placeholder="Search by Job GUID..." 
                            value={jobGuid}
                            onChange={e => { setJobGuid(e.target.value); setPage(0); }}
                            className="bg-zinc-950 border-zinc-800 pl-9 focus:border-primary/50"
                        />
                    </div>
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-1">Node ID</label>
                    <div className="relative">
                        <Filter className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                        <Input 
                            placeholder="Filter by Node..." 
                            value={nodeId}
                            onChange={e => { setNodeId(e.target.value); setPage(0); }}
                            className="bg-zinc-950 border-zinc-800 pl-9 focus:border-primary/50"
                        />
                    </div>
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-1">Status</label>
                    <Select value={status} onValueChange={v => { setStatus(v); setPage(0); }}>
                        <SelectTrigger className="bg-zinc-950 border-zinc-800 focus:border-primary/50">
                            <SelectValue placeholder="All Statuses" />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                            <SelectItem value="ALL">All Statuses</SelectItem>
                            <SelectItem value="COMPLETED">Completed</SelectItem>
                            <SelectItem value="FAILED">Failed</SelectItem>
                            <SelectItem value="SECURITY_REJECTED">Security Rejected</SelectItem>
                            <SelectItem value="DEAD_LETTER">Dead Letter</SelectItem>
                            <SelectItem value="RETRYING">Retrying</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-1">Scheduled Job</label>
                    <Select value={definitionId || 'ALL'} onValueChange={v => { setDefinitionId(v === 'ALL' ? '' : v); setPage(0); }}>
                        <SelectTrigger className="bg-zinc-950 border-zinc-800 focus:border-primary/50">
                            <SelectValue placeholder="All Definitions" />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                            <SelectItem value="ALL">All Definitions</SelectItem>
                            {(definitions ?? []).map(def => (
                                <SelectItem key={def.id} value={def.id}>{def.name}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <div className="rounded-xl border border-zinc-900 bg-zinc-975 overflow-hidden shadow-sm">
                <Table>
                    <TableHeader className="bg-zinc-900/50">
                        <TableRow className="border-zinc-900 hover:bg-transparent">
                            <TableHead className="text-zinc-400 font-bold py-4">Timestamp</TableHead>
                            <TableHead className="text-zinc-400 font-bold">Job GUID</TableHead>
                            <TableHead className="text-zinc-400 font-bold">Node</TableHead>
                            <TableHead className="text-zinc-400 font-bold">Status</TableHead>
                            <TableHead className="text-zinc-400 font-bold text-right">Duration</TableHead>
                            <TableHead className="text-zinc-400 font-bold text-right pr-6">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            <TableRow><TableCell colSpan={6} className="text-center py-20 text-zinc-500 font-medium italic">Loading history...</TableCell></TableRow>
                        ) : (executions?.length === 0) ? (
                            <TableRow><TableCell colSpan={6} className="text-center py-20 text-zinc-500 font-medium italic">No execution history found matching filters.</TableCell></TableRow>
                        ) : executions?.map((ex: any) => (
                            <TableRow key={ex.id} className="border-zinc-900 hover:bg-zinc-900/30 transition-colors group">
                                <TableCell className="font-medium text-zinc-300 whitespace-nowrap tabular-nums">
                                    {ex.started_at ? formatDistanceToNow(new Date(ex.started_at), { addSuffix: true }) : 'Pending'}
                                </TableCell>
                                <TableCell className="font-mono text-xs text-zinc-500 group-hover:text-zinc-400 transition-colors">{ex.job_guid}</TableCell>
                                <TableCell className="text-zinc-400 group-hover:text-zinc-300 transition-colors">{ex.node_id || 'N/A'}</TableCell>
                                <TableCell>
                                    <Badge variant={getStatusVariant(ex.status)} className="font-semibold px-2 py-0.5">{ex.status}</Badge>
                                </TableCell>
                                <TableCell className="text-right text-zinc-400 whitespace-nowrap tabular-nums group-hover:text-zinc-300 transition-colors">
                                    {ex.duration_seconds ? `${ex.duration_seconds.toFixed(1)}s` : '-'}
                                </TableCell>
                                <TableCell className="text-right pr-6">
                                    <Button 
                                        variant="ghost" 
                                        size="sm" 
                                        onClick={() => setSelectedEx(ex.id)}
                                        className="gap-2 text-primary hover:text-primary hover:bg-primary/10 transition-all font-bold"
                                    >
                                        <Terminal className="h-3.5 w-3.5" />
                                        <span>Logs</span>
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
            
            <div className="flex items-center justify-end gap-4 pb-10">
                <div className="text-zinc-600 text-xs font-bold uppercase tracking-widest">
                    Page {page + 1}
                </div>
                <div className="flex gap-2">
                    <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => setPage(p => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all h-9 px-4"
                    >
                        Previous
                    </Button>
                    <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => setPage(p => p + 1)}
                        disabled={!executions || executions.length < limit}
                        className="bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all h-9 px-4"
                    >
                        Next
                    </Button>
                </div>
            </div>

            <ExecutionLogModal 
                executionId={selectedEx || undefined} 
                open={!!selectedEx} 
                onClose={() => setSelectedEx(null)} 
            />
        </div>
    );
};

export default History;
