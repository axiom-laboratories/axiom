import React from 'react';
import {
    Terminal,
    Clock,
    ShieldCheck,
    XCircle,
    Trash2,
    PlayCircle,
    PauseCircle,
    Pencil,
    ChevronDown,
    ChevronUp,
    Send
} from 'lucide-react';
import { useState } from 'react';
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
import { Button } from '@/components/ui/button';

interface JobDefinition {
    id: string;
    name: string;
    script_content: string;
    schedule_cron: string;
    is_active: boolean;
    status: string;
    pushed_by: string | null;
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
    onDelete: (id: string) => void;
    onToggle: (id: string) => void;
    onEdit: (id: string) => void;
    onPublish?: (id: string) => void;
    selectedDefId?: string | null;
    onSelect?: (id: string) => void;
}

const JobDefinitionList = ({ definitions, executions, onDelete, onToggle, onEdit, onPublish, selectedDefId, onSelect }: JobDefinitionListProps) => {
    const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});

    const toggleRow = (id: string) => {
        setExpandedRows(prev => ({ ...prev, [id]: !prev[id] }));
    };

    const getSparklineData = (defId: string) => {
        return executions
            .filter(e => e.scheduled_job_id === defId)
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .slice(0, 30)
            .reverse();
    };

    const renderStatusBadge = (status: string | undefined) => {
        const s = (status ?? '').toUpperCase();
        switch (s) {
            case 'ACTIVE':
                return <Badge className="bg-green-500/10 text-green-500 border-green-500/20 hover:bg-green-500/20 uppercase text-[10px] font-bold tracking-wider">Active</Badge>;
            case 'DRAFT':
                return <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20 hover:bg-yellow-500/20 uppercase text-[10px] font-bold tracking-wider">Draft</Badge>;
            case 'DEPRECATED':
                return <Badge className="bg-zinc-500/10 text-zinc-500 border-zinc-500/20 hover:bg-zinc-500/20 uppercase text-[10px] font-bold tracking-wider">Deprecated</Badge>;
            case 'REVOKED':
                return <Badge className="bg-red-500/10 text-red-500 border-red-500/20 hover:bg-red-500/20 uppercase text-[10px] font-bold tracking-wider">Revoked</Badge>;
            default:
                return <Badge className="bg-zinc-500/10 text-zinc-500 border-zinc-500/20 hover:bg-zinc-500/20 uppercase text-[10px] font-bold tracking-wider">{s}</Badge>;
        }
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
                        <TableHead className="text-zinc-500 font-bold uppercase text-xs tracking-widest pl-6">Job Definition</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-xs tracking-widest">Status</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-xs tracking-widest">Cron Schedule</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-xs tracking-widest">Integrity</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-xs tracking-widest">Observation Feed (30d)</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-xs tracking-widest">Last Sync</TableHead>
                        <TableHead className="text-zinc-500 font-bold uppercase text-xs tracking-widest pr-6 text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {definitions.length > 0 ? (
                        definitions.map(def => (
                            <React.Fragment key={def.id}>
                            <TableRow className={`border-zinc-800 hover:bg-zinc-900/30 transition-colors group${def.id === selectedDefId ? ' bg-primary/5 border-l-2 border-l-primary' : ''}`}>
                                <TableCell className="pl-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => toggleRow(def.id)}
                                            className="text-zinc-600 hover:text-zinc-400 transition-colors"
                                        >
                                            {expandedRows[def.id] ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                        </button>
                                        <div className="flex flex-col">
                                            <span
                                                className="text-white font-medium flex items-center gap-2 cursor-pointer hover:text-primary transition-colors"
                                                onClick={() => onSelect?.(def.id)}
                                            >
                                                <Terminal className="h-3 w-3 text-primary" />
                                                {def.name}
                                            </span>
                                            <div className="flex items-center gap-2 mt-0.5">
                                                <span className="text-[10px] text-zinc-600 font-mono">ID: {def.id.substring(0, 8)}</span>
                                                {def.pushed_by && (
                                                    <span className="text-[10px] text-zinc-500 italic">by {def.pushed_by}</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </TableCell>
                                <TableCell>
                                    {renderStatusBadge(def.status)}
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
                                <TableCell>
                                    <span className="text-xs text-zinc-500 font-mono">
                                        {new Date(def.created_at).toLocaleDateString()}
                                    </span>
                                </TableCell>
                                <TableCell className="text-right pr-6">
                                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        {def.status === 'DRAFT' && onPublish && (
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-7 w-7 text-zinc-500 hover:text-green-400 hover:bg-green-500/10 rounded-md"
                                                onClick={() => onPublish(def.id)}
                                                title="Publish to Active"
                                            >
                                                <Send className="h-3.5 w-3.5" />
                                            </Button>
                                        )}
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-zinc-500 hover:text-yellow-400 hover:bg-yellow-500/10 rounded-md"
                                            onClick={() => onToggle(def.id)}
                                            title={def.is_active ? 'Suspend' : 'Activate'}
                                        >
                                            {def.is_active
                                                ? <PauseCircle className="h-3.5 w-3.5" />
                                                : <PlayCircle className="h-3.5 w-3.5" />
                                            }
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-zinc-500 hover:text-blue-400 hover:bg-blue-500/10 rounded-md"
                                            onClick={() => onEdit(def.id)}
                                            title="Edit"
                                        >
                                            <Pencil className="h-3.5 w-3.5" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-md"
                                            onClick={() => onDelete(def.id)}
                                            title="Delete"
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                            {expandedRows[def.id] && (
                                <TableRow className="border-zinc-800 bg-zinc-950/50 hover:bg-zinc-950/50">
                                    <TableCell colSpan={7} className="p-0 border-t border-zinc-800">
                                        <div className="p-6">
                                            <div className="flex items-center justify-between mb-4">
                                                <h4 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Source Payload</h4>
                                                <Badge variant="outline" className="text-[10px] text-zinc-500 border-zinc-800">PYTHON_SCRIPT</Badge>
                                            </div>
                                            <pre className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 text-[13px] text-zinc-300 font-mono overflow-x-auto max-h-[400px]">
                                                <code>{def.script_content}</code>
                                            </pre>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            )}
                            </React.Fragment>
                        ))
                    ) : (
                        <TableRow>
                            <TableCell colSpan={7} className="h-32 text-center text-zinc-600">
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
