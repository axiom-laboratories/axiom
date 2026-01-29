import { useState, useEffect } from 'react';
import {
    Calendar,
    Plus,
    ShieldCheck,
    Activity,
    History,
    Terminal,
    Code2,
    User,
    Clock,
    CheckCircle2,
    XCircle,
    Info
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from '@/components/ui/table';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { authenticatedFetch } from '../auth';

const JobDefinitions = () => {
    const [definitions, setDefinitions] = useState([]);
    const [executions, setExecutions] = useState([]);
    const [signatures, setSignatures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    const [formData, setFormData] = useState({
        name: '',
        script_content: '',
        signature: '',
        signature_id: '',
        schedule_cron: '* * * * *',
        target_node_id: ''
    });

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [defRes, execRes, sigRes] = await Promise.all([
                authenticatedFetch('/jobs/definitions'),
                authenticatedFetch('/jobs'),
                authenticatedFetch('/signatures')
            ]);

            if (defRes.ok) setDefinitions(await defRes.json());
            if (execRes.ok) setExecutions(await execRes.json());
            if (sigRes.ok) setSignatures(await sigRes.json());
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    const getSparklineData = (defId) => {
        return executions
            .filter(e => e.scheduled_job_id === defId)
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .slice(0, 30)
            .reverse();
    };

    const renderSparkline = (data) => {
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

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const res = await authenticatedFetch('/jobs/definitions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            if (res.ok) {
                setShowModal(false);
                loadData();
            } else {
                const err = await res.json();
                alert(`Error: ${err.detail}`);
            }
        } catch (e) { console.error(e); alert("Submission Error"); }
    };

    if (loading) return (
        <div className="space-y-4">
            <div className="h-10 w-48 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
            <div className="h-64 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
        </div>
    );

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Immutable Schedules</h1>
                    <p className="text-zinc-500">Centrally signed Python payloads with zero-trust execution verification.</p>
                </div>
                <Button onClick={() => setShowModal(true)} className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-6 rounded-xl shadow-lg shadow-primary/10">
                    <Plus className="mr-2 h-4 w-4" />
                    Archive New Payload
                </Button>
            </div>

            <Card className="bg-[#121214] border-zinc-800/50 overflow-hidden">
                <Table>
                    <TableHeader className="bg-zinc-900/50 border-zinc-800">
                        <TableRow className="border-zinc-800 hover:bg-transparent">
                            <TableHead className="text-zinc-500 font-bold uppercase text-[10px] tracking-widest pl-6">Job Definition</TableHead>
                            <TableHead className="text-zinc-500 font-bold uppercase text-[10px] tracking-widest">Cron Schedule</TableHead>
                            <TableHead className="text-zinc-500 font-bold uppercase text-[10px] tracking-widest">Integrity</TableHead>
                            <TableHead className="text-zinc-500 font-bold uppercase text-[10px] tracking-widest">Observation Feed (30d)</TableHead>
                            <TableHead className="text-zinc-500 font-bold uppercase text-[10px] tracking-widest pr-6 text-right">Last Sync</TableHead>
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
                                            <span className="text-[10px] text-zinc-600 font-mono mt-0.5">ID: {def.id.substring(0, 8)}</span>
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

            <Dialog open={showModal} onOpenChange={setShowModal}>
                <DialogContent className="bg-[#121214] border-zinc-800 text-white sm:max-w-4xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-xl font-bold">
                            <Code2 className="h-5 w-5 text-primary" />
                            Seal & Schedule Payload
                        </DialogTitle>
                        <DialogDescription className="text-zinc-500">
                            Create an immutable, cryptographically signed Python job. Every byte of the script is verified at runtime by the puppet nodes.
                        </DialogDescription>
                    </DialogHeader>

                    <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-8 py-6">
                        <div className="space-y-6">
                            <div className="space-y-2">
                                <Label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Metadata</Label>
                                <div className="space-y-4">
                                    <div className="relative">
                                        <Input
                                            placeholder="System Monitor Script"
                                            className="bg-zinc-900 border-zinc-800 pl-4 h-11"
                                            value={formData.name}
                                            onChange={e => setFormData({ ...formData, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="relative">
                                        <span className="absolute left-3 top-3.5 text-zinc-600 text-xs font-bold">CRON</span>
                                        <Input
                                            placeholder="* * * * *"
                                            className="bg-zinc-900 border-zinc-800 pl-14 h-11 font-mono"
                                            value={formData.schedule_cron}
                                            onChange={e => setFormData({ ...formData, schedule_cron: e.target.value })}
                                        />
                                    </div>
                                    <Input
                                        placeholder="Target Node ID (Optional)"
                                        className="bg-zinc-900 border-zinc-800 h-11 font-mono"
                                        value={formData.target_node_id}
                                        onChange={e => setFormData({ ...formData, target_node_id: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Root of Trust</Label>
                                <Select
                                    value={formData.signature_id}
                                    onValueChange={(val) => setFormData({ ...formData, signature_id: val })}
                                >
                                    <SelectTrigger className="bg-zinc-900 border-zinc-800 h-11">
                                        <SelectValue placeholder="Establish Identity..." />
                                    </SelectTrigger>
                                    <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                                        {signatures.map(s => (
                                            <SelectItem key={s.id} value={s.id}>
                                                {s.name} ({s.uploaded_by})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Signature Payload (B64)</Label>
                                <Textarea
                                    placeholder="Paste Ed25519/RSA signature..."
                                    className="bg-zinc-900 border-zinc-800 h-24 font-mono text-[10px] text-zinc-400"
                                    value={formData.signature}
                                    onChange={e => setFormData({ ...formData, signature: e.target.value })}
                                    required
                                />
                                <div className="flex items-start gap-2 p-3 rounded-lg bg-zinc-900 border border-zinc-800">
                                    <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                                    <p className="text-[10px] text-zinc-500 leading-normal">
                                        Use the system CLI or <code>openssl</code> to sign the script. If the signature doesn't match the script bytes exactly, nodes will reject the payload with a <code>SIGNATURE_INVALID</code> alert.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Python Payload Source</Label>
                            <div className="relative h-full flex flex-col">
                                <div className="absolute top-3 left-3 h-4 w-4 text-zinc-700 pointer-events-none">
                                    <Code2 className="h-full w-full" />
                                </div>
                                <Textarea
                                    className="flex-1 min-h-[400px] bg-zinc-950 border-zinc-800 pl-10 pt-3 text-green-500 font-mono text-sm resize-none focus:ring-1 focus:ring-primary/20"
                                    placeholder="import os\nprint('Identity verified')"
                                    value={formData.script_content}
                                    onChange={e => setFormData({ ...formData, script_content: e.target.value })}
                                    required
                                />
                            </div>
                        </div>

                        <DialogFooter className="col-span-full pt-4 border-t border-zinc-800 mt-2">
                            <Button type="button" variant="ghost" onClick={() => setShowModal(false)} className="text-zinc-500">Abandon</Button>
                            <Button type="submit" className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-8 rounded-xl ring-2 ring-primary/20 ring-offset-2 ring-offset-[#121214]">
                                Seal and Register
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default JobDefinitions;
