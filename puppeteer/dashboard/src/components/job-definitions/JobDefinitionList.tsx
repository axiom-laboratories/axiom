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
    Send,
    KeyRound
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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface JobDefinition {
    id: string;
    name: string;
    script_content: string;
    signature_payload?: string;
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

interface Signature {
    id: string;
    name: string;
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
    signatures?: Signature[];
    onResign?: (id: string, signatureId: string, signature: string) => void;
}

const ReSignDialog = ({
    job,
    signatures,
    open,
    onClose,
    onResign,
}: {
    job: JobDefinition | null;
    signatures: Signature[];
    open: boolean;
    onClose: () => void;
    onResign: (id: string, signatureId: string, signature: string) => void;
}) => {
    const [sigId, setSigId] = useState('');
    const [sig, setSig] = useState('');

    if (!job) return null;

    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
            <DialogContent className="max-w-2xl bg-card border-muted">
                <DialogHeader>
                    <DialogTitle className="text-foreground flex items-center gap-2">
                        <KeyRound className="h-4 w-4 text-amber-500" />
                        Re-sign: {job.name}
                    </DialogTitle>
                    <DialogDescription className="text-muted-foreground">
                        Confirm the script content below, then provide a valid signature to reactivate.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div>
                        <Label className="text-muted-foreground text-xs uppercase tracking-wider mb-2 block">Script Content (read-only)</Label>
                        <pre className="bg-background border border-muted rounded-lg p-3 text-xs text-foreground/80 font-mono overflow-auto max-h-48 whitespace-pre-wrap">{job.script_content}</pre>
                    </div>
                    <div>
                        <Label className="text-muted-foreground text-xs uppercase tracking-wider mb-2 block">Signing Key</Label>
                        <Select value={sigId} onValueChange={setSigId}>
                            <SelectTrigger className="bg-background border-muted text-foreground/80">
                                <SelectValue placeholder="Select a signing key..." />
                            </SelectTrigger>
                            <SelectContent className="bg-background border-muted">
                                {signatures.map(s => (
                                    <SelectItem key={s.id} value={s.id} className="text-foreground">{s.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div>
                        <Label className="text-muted-foreground text-xs uppercase tracking-wider mb-2 block">Signature (base64)</Label>
                        <Textarea
                            value={sig}
                            onChange={e => setSig(e.target.value)}
                            placeholder="Base64-encoded Ed25519 signature..."
                            className="bg-background border-muted text-foreground/80 font-mono text-xs min-h-[80px]"
                        />
                    </div>
                </div>
                <DialogFooter className="gap-2">
                    <Button variant="ghost" onClick={onClose} className="text-muted-foreground hover:text-foreground">Cancel</Button>
                    <Button
                        disabled={!sigId || !sig.trim()}
                        className="bg-amber-500 hover:bg-amber-600 text-white font-bold"
                        onClick={() => { onResign(job.id, sigId, sig.trim()); onClose(); }}
                    >
                        <KeyRound className="h-3.5 w-3.5 mr-1.5" /> Re-sign &amp; Reactivate
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

const JobDefinitionList = ({ definitions, executions, onDelete, onToggle, onEdit, onPublish, selectedDefId, onSelect, signatures = [], onResign }: JobDefinitionListProps) => {
    const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
    const [resigningJob, setResigningJob] = useState<JobDefinition | null>(null);

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
                return <Badge className="bg-muted text-muted-foreground border-muted hover:bg-muted/80 uppercase text-[10px] font-bold tracking-wider">Deprecated</Badge>;
            case 'REVOKED':
                return <Badge className="bg-red-500/10 text-red-500 border-red-500/20 hover:bg-red-500/20 uppercase text-[10px] font-bold tracking-wider">Revoked</Badge>;
            default:
                return <Badge className="bg-muted text-muted-foreground border-muted hover:bg-muted/80 uppercase text-[10px] font-bold tracking-wider">{s}</Badge>;
        }
    };

    const renderSparkline = (data: Execution[]) => {
        if (!data.length) return <span className="text-muted-foreground/60 text-xs italic">No verification history</span>;

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
        <>
        <Card className="bg-card border-muted/50 overflow-hidden">
            <Table>
                <TableHeader className="bg-muted/30 border-muted">
                    <TableRow className="border-muted hover:bg-transparent">
                        <TableHead className="text-muted-foreground font-bold uppercase text-xs tracking-widest pl-6">Job Definition</TableHead>
                        <TableHead className="text-muted-foreground font-bold uppercase text-xs tracking-widest">Status</TableHead>
                        <TableHead className="text-muted-foreground font-bold uppercase text-xs tracking-widest">Cron Schedule</TableHead>
                        <TableHead className="text-muted-foreground font-bold uppercase text-xs tracking-widest">Integrity</TableHead>
                        <TableHead className="text-muted-foreground font-bold uppercase text-xs tracking-widest">Observation Feed (30d)</TableHead>
                        <TableHead className="text-muted-foreground font-bold uppercase text-xs tracking-widest">Last Sync</TableHead>
                        <TableHead className="text-muted-foreground font-bold uppercase text-xs tracking-widest pr-6 text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {definitions.length > 0 ? (
                        definitions.map(def => (
                            <React.Fragment key={def.id}>
                            <TableRow className={`border-muted hover:bg-muted/30 transition-colors group${def.id === selectedDefId ? ' bg-primary/5 border-l-2 border-l-primary' : ''}`}>
                                <TableCell className="pl-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => toggleRow(def.id)}
                                            className="text-muted-foreground/60 hover:text-muted-foreground transition-colors"
                                        >
                                            {expandedRows[def.id] ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                        </button>
                                        <div className="flex flex-col">
                                            <span
                                                className="text-foreground font-medium flex items-center gap-2 cursor-pointer hover:text-primary transition-colors"
                                                onClick={() => onSelect?.(def.id)}
                                            >
                                                <Terminal className="h-3 w-3 text-primary" />
                                                {def.name}
                                            </span>
                                            <div className="flex items-center gap-2 mt-0.5">
                                                <span className="text-[10px] text-muted-foreground/60 font-mono">ID: {def.id.substring(0, 8)}</span>
                                                {def.pushed_by && (
                                                    <span className="text-[10px] text-muted-foreground/80 italic">by {def.pushed_by}</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </TableCell>
                                <TableCell>
                                    {renderStatusBadge(def.status)}
                                </TableCell>
                                <TableCell>
                                    <Badge variant="outline" className="font-mono bg-muted border-muted text-muted-foreground">
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
                                        <div className="flex items-center gap-1.5 text-muted-foreground/60 text-xs font-bold uppercase tracking-tighter">
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
                                    <span className="text-xs text-muted-foreground font-mono">
                                        {new Date(def.created_at).toLocaleDateString()}
                                    </span>
                                </TableCell>
                                <TableCell className="text-right pr-6">
                                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        {def.status === 'DRAFT' && onResign && (
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-7 w-7 text-amber-500 hover:text-amber-400 hover:bg-amber-500/10 rounded-md"
                                                onClick={() => setResigningJob(def)}
                                                title="Re-sign to reactivate"
                                            >
                                                <KeyRound className="h-3.5 w-3.5" />
                                            </Button>
                                        )}
                                        {def.status === 'DRAFT' && onPublish && (
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-7 w-7 text-muted-foreground hover:text-green-400 hover:bg-green-500/10 rounded-md"
                                                onClick={() => onPublish(def.id)}
                                                title="Publish to Active"
                                            >
                                                <Send className="h-3.5 w-3.5" />
                                            </Button>
                                        )}
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-muted-foreground hover:text-yellow-400 hover:bg-yellow-500/10 rounded-md"
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
                                            className="h-7 w-7 text-muted-foreground hover:text-blue-400 hover:bg-blue-500/10 rounded-md"
                                            onClick={() => onEdit(def.id)}
                                            title="Edit"
                                        >
                                            <Pencil className="h-3.5 w-3.5" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded-md"
                                            onClick={() => onDelete(def.id)}
                                            title="Delete"
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                            {expandedRows[def.id] && (
                                <TableRow className="border-muted bg-muted/20 hover:bg-muted/20">
                                    <TableCell colSpan={7} className="p-0 border-t border-muted">
                                        <div className="p-6">
                                            <div className="flex items-center justify-between mb-4">
                                                <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Source Payload</h4>
                                                <Badge variant="outline" className="text-[10px] text-muted-foreground border-muted">PYTHON_SCRIPT</Badge>
                                            </div>
                                            <pre className="bg-card border border-muted rounded-lg p-4 text-[13px] text-foreground/80 font-mono overflow-x-auto max-h-[400px]">
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
                            <TableCell colSpan={7} className="h-32 text-center text-muted-foreground/60">
                                No signed definitions found in registry.
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </Card>
        <ReSignDialog
            job={resigningJob}
            signatures={signatures}
            open={!!resigningJob}
            onClose={() => setResigningJob(null)}
            onResign={(id, sigId, sig) => { onResign?.(id, sigId, sig); setResigningJob(null); }}
        />
        </>
    );
};

export default JobDefinitionList;
