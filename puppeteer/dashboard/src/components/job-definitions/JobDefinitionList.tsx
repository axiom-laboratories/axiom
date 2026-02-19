import {
    Terminal,
    Clock,
    ShieldCheck,
    XCircle
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

interface JobDefinition {
    id: string;
    name: string;
    schedule_cron: string;
    is_active: boolean;
    created_at: string;
}

interface Execution {
    scheduled_job_id: string;
    status: string;
    created_at: string;
}

interface JobDefinitionListProps {
    definitions: JobDefinition[];
    executions: Execution[];
}

const JobDefinitionList = ({ definitions, executions }: JobDefinitionListProps) => {
    const getSparklineData = (defId: string) => {
        return executions
            .filter(e => e.scheduled_job_id === defId)
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .slice(0, 30)
            .reverse();
    };

    const renderSparkline = (data: Execution[]) => {
        if (!data.length) return <span className="text-zinc-600 text-xs italic">No verification history</span>;

        return (
            <div className="flex items-end h-5 gap-[2px]">
                {data.map((run, i) => {
                    const status = run.status.toLowerCase();
                    const color = status === 'completed' ? 'bg-green-500' : (status === 'failed' ? 'bg-red-500' : 'bg-yellow-500');
                    const height = status === 'completed' ? 'h-full' : 'h-1/2';
                    return (
                        <div
                            key={i}
                            className={`w-1 ${height} ${color} rounded-[1px] transition-all hover:w-1.5 cursor-help`}
                            title={`${run.status} - ${new Date(run.created_at).toLocaleString()}`}
                        />
                    );
                })}
            </div>
        );
    };

    return (
        <Card className="bg-zinc-925 border-zinc-800/50 overflow-hidden">
            <Table>
                <TableHeader className="bg-zinc-900/50 border-zinc-800">
                    <TableRow className="border-zinc-800 hover:bg-transparent">
                        <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest pl-6">Job Definition</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Cron Schedule</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Integrity</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Observation Feed (30d)</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest pr-6 text-right">Last Sync</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {definitions.length > 0 ? (
                        definitions.map(def => (
                            <TableRow key={def.id} className="border-zinc-800 hover:bg-zinc-900/30 transition-colors group">
                                <TableCell className="pl-6 py-4">
                                    <div className="flex flex-col">
                                        <span className="text-white font-medium flex items-center gap-2">
                                            <Terminal className="h-3 w-3 text-primary" />
                                            {def.name}
                                        </span>
                                        <span className="text-2xs text-zinc-600 font-mono mt-0.5">ID: {def.id.substring(0, 8)}</span>
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <Badge variant="outline" className="font-mono bg-zinc-900 border-zinc-800 text-zinc-400">
                                        <Clock className="mr-1 h-3 w-3" />
                                        {def.schedule_cron || 'Manual Trigger'}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    {def.is_active ? (
                                        <div className="flex items-center gap-1.5 text-green-500 text-xs font-bold uppercase tracking-tighter">
                                            <ShieldCheck className="h-3.5 w-3.5" />
                                            Enforced
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-1.5 text-zinc-600 text-xs font-bold uppercase tracking-tighter">
                                            <XCircle className="h-3.5 w-3.5" />
                                            Suspended
                                        </div>
                                    )}
                                </TableCell>
                                <TableCell>
                                    <div className="min-w-[120px]">
                                        {renderSparkline(getSparklineData(def.id))}
                                    </div>
                                </TableCell>
                                <TableCell className="text-right pr-6">
                                    <span className="text-xs text-zinc-500 font-mono">
                                        {new Date(def.created_at).toLocaleDateString()}
                                    </span>
                                </TableCell>
                            </TableRow>
                        ))
                    ) : (
                        <TableRow>
                            <TableCell colSpan={5} className="h-32 text-center text-zinc-600">
                                No signed definitions found in registry.
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </Card>
    );
};

export default JobDefinitionList;
