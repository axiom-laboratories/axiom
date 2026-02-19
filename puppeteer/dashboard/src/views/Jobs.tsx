import { useState, useEffect } from 'react';
import {
    Plus,
    Play,
    History,
    Terminal,
    Clock,
    Hash,
    MoreHorizontal,
    Search,
    Filter
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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
import { authenticatedFetch } from '../auth';

const Jobs = () => {
    const [jobs, setJobs] = useState([]);
    const [newTaskType, setNewTaskType] = useState('web_task');
    const [newTaskPayload, setNewTaskPayload] = useState('{}');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const fetchJobs = async () => {
        try {
            const res = await authenticatedFetch('/jobs');
            if (res.ok) {
                setJobs(await res.json());
            }
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 3000);
        return () => clearInterval(interval);
    }, []);

    const createJob = async () => {
        try {
            setIsSubmitting(true);
            const payload = JSON.parse(newTaskPayload);
            const res = await authenticatedFetch('/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task_type: newTaskType,
                    payload: payload
                })
            });
            if (res.ok) {
                fetchJobs();
                setNewTaskPayload('{}');
            } else {
                console.error('Failed to submit job');
            }
        } catch (e) {
            console.error('Invalid JSON Payload', e);
        } finally {
            setIsSubmitting(false);
        }
    };

    const getStatusVariant = (status: string) => {
        switch (status.toLowerCase()) {
            case 'completed': return 'success';
            case 'failed': return 'destructive';
            case 'assigned': return 'secondary';
            case 'pending': return 'outline';
            default: return 'outline';
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Task Queue</h1>
                    <p className="text-zinc-500">Dispatch and monitor orchestration payloads across the mesh.</p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" className="border-zinc-800 bg-zinc-900/50 hover:bg-zinc-900">
                        <History className="mr-2 h-4 w-4" />
                        Audit Log
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                {/* Create Job Box */}
                <Card className="bg-zinc-925 border-zinc-800/50">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-lg font-bold text-white">
                            <Plus className="h-5 w-5 text-primary" />
                            Submit New Job
                        </CardTitle>
                        <CardDescription className="text-zinc-500">Configure a manual orchestration payload.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">Task Definition</label>
                            <Select value={newTaskType} onValueChange={setNewTaskType}>
                                <SelectTrigger className="bg-zinc-900 border-zinc-800 text-white h-11">
                                    <SelectValue placeholder="Select type" />
                                </SelectTrigger>
                                <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                                    <SelectItem value="web_task">Web Task (Puppeteer)</SelectItem>
                                    <SelectItem value="python_script">Python Executor</SelectItem>
                                    <SelectItem value="file_download">File Provisioner</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">JSON Payload</label>
                            <div className="relative">
                                <Terminal className="absolute top-3 left-3 h-4 w-4 text-zinc-600" />
                                <textarea
                                    value={newTaskPayload}
                                    onChange={(e) => setNewTaskPayload(e.target.value)}
                                    className="w-full h-48 pl-10 pr-4 py-3 bg-zinc-900 border border-zinc-800 text-green-500 rounded-xl font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                                />
                            </div>
                        </div>

                        <Button
                            className="w-full h-11 bg-primary hover:bg-primary/90 text-white font-bold rounded-xl shadow-lg shadow-primary/10 transition-all active:scale-[0.98]"
                            onClick={createJob}
                            disabled={isSubmitting}
                        >
                            <Play className="mr-2 h-4 w-4 fill-current" />
                            {isSubmitting ? 'Dispatching...' : 'Dispatch Payload'}
                        </Button>
                    </CardContent>
                </Card>

                {/* Jobs Table */}
                <Card className="xl:col-span-2 bg-zinc-925 border-zinc-800/50 overflow-hidden">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="text-lg font-bold text-white">Queue Monitor</CardTitle>
                            <CardDescription className="text-zinc-500">Real-time status of dispatched tasks.</CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-600" />
                                <Input placeholder="Filter GUID..." className="pl-9 bg-zinc-900 border-zinc-800 h-9 w-40 text-sm" />
                            </div>
                        </div>
                    </CardHeader>
                    <Table>
                        <TableHeader className="bg-zinc-900/50 border-zinc-800">
                            <TableRow className="border-zinc-800 hover:bg-transparent">
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest pl-6">GUID</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Type</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Status</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Target Node</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest">Timestamp</TableHead>
                                <TableHead className="text-zinc-500 font-bold uppercase text-2xs tracking-widest pr-6 text-right">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {jobs.length > 0 ? (
                                jobs.map(job => (
                                    <TableRow key={job.guid} className="border-zinc-800 hover:bg-zinc-900/30 transition-colors">
                                        <TableCell className="font-mono text-zinc-400 pl-6">
                                            <div className="flex items-center gap-2">
                                                <Hash className="h-3 w-3 text-zinc-600" />
                                                {job.guid.substring(0, 8)}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-white font-medium">
                                            {job.payload.task_type || job.task_type || 'Generic'}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={getStatusVariant(job.status) as "success" | "destructive" | "secondary" | "outline"} className="capitalize">
                                                {job.status.toLowerCase()}
                                            </Badge>
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
                                        <TableCell className="pr-6 text-right">
                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-600 hover:text-white hover:bg-zinc-800 rounded-lg">
                                                <MoreHorizontal className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-32 text-center text-zinc-600">
                                        Queue is currently empty.
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </Card>
            </div>
        </div>
    );
};

export default Jobs;
