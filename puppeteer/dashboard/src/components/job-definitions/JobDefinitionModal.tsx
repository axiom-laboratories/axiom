import { useEffect } from 'react';
import {
    Code2,
    Info,
    Tag,
    Cpu,
    AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
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

interface Signature {
    id: string;
    name: string;
    uploaded_by: string;
}

interface JobDefinitionFormData {
    name: string;
    script_content: string;
    signature: string;
    signature_id: string;
    schedule_cron: string;
    target_node_id: string;
    target_tags: string;
    capability_requirements: string;
    allow_overlap: boolean;
    dispatch_timeout_minutes: number | null;
}

interface EditingJob {
    id: string;
    name: string;
    script_content: string;
    signature_id: string;
    signature_payload: string;
    schedule_cron: string | null;
    target_node_id: string | null;
    target_tags: string[] | null;
    capability_requirements: Record<string, string> | null;
    allow_overlap?: boolean;
    dispatch_timeout_minutes?: number | null;
}

interface JobDefinitionModalProps {
    isOpen: boolean;
    onClose: (open: boolean) => void;
    onSubmit: (e: React.FormEvent) => void;
    formData: JobDefinitionFormData;
    setFormData: (data: JobDefinitionFormData) => void;
    signatures: Signature[];
    editingJob?: EditingJob | null;
}

const JobDefinitionModal = ({
    isOpen,
    onClose,
    onSubmit,
    formData,
    setFormData,
    signatures,
    editingJob,
}: JobDefinitionModalProps) => {
    useEffect(() => {
        if (!editingJob) return;
        setFormData({
            name: editingJob.name,
            script_content: editingJob.script_content,
            signature: editingJob.signature_payload,
            signature_id: editingJob.signature_id,
            schedule_cron: editingJob.schedule_cron ?? '',
            target_node_id: editingJob.target_node_id ?? '',
            target_tags: (editingJob.target_tags ?? []).join(', '),
            capability_requirements: Object.entries(editingJob.capability_requirements ?? {})
                .map(([k, v]) => `${k}:${v}`)
                .join(', '),
            allow_overlap: editingJob.allow_overlap ?? false,
            dispatch_timeout_minutes: editingJob.dispatch_timeout_minutes ?? null,
        });
    }, [editingJob]);

    const isEditMode = !!editingJob;

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="bg-card border-muted text-foreground sm:max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-xl font-bold">
                        <Code2 className="h-5 w-5 text-primary" />
                        {isEditMode ? 'Edit Job Definition' : 'Seal & Schedule Payload'}
                    </DialogTitle>
                    <DialogDescription className="text-muted-foreground">
                        {isEditMode
                            ? 'Update the job definition. If you change the script content, you must provide a new signature.'
                            : 'Create an immutable, cryptographically signed Python job. Every byte of the script is verified at runtime by the puppet nodes.'}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={onSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-8 py-6">
                    <div className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="job-name" className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Metadata</Label>
                            <div className="space-y-4">
                                <div className="relative">
                                    <Input
                                        id="job-name"
                                        placeholder="System Monitor Script"
                                        className="bg-background border-muted pl-4 h-11"
                                        value={formData.name}
                                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                                        required
                                    />
                                </div>
                                <div className="relative">
                                    <span className="absolute left-3 top-3.5 text-muted-foreground/60 text-xs font-bold">CRON</span>
                                    <Input
                                        id="job-cron"
                                        placeholder="* * * * *"
                                        className="bg-background border-muted pl-14 h-11 font-mono"
                                        value={formData.schedule_cron}
                                        onChange={e => setFormData({ ...formData, schedule_cron: e.target.value })}
                                        aria-label="Cron schedule"
                                    />
                                </div>
                                <div className="flex items-center gap-3">
                                    <label className="text-sm text-muted-foreground">Allow Overlap</label>
                                    <button
                                        type="button"
                                        onClick={() => setFormData({ ...formData, allow_overlap: !formData.allow_overlap })}
                                        className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                                            formData.allow_overlap
                                                ? 'bg-amber-600 text-white'
                                                : 'bg-muted text-muted-foreground'
                                        }`}
                                    >
                                        {formData.allow_overlap ? 'Allowed' : 'Blocked (default)'}
                                    </button>
                                    <span className="text-xs text-muted-foreground">
                                        {formData.allow_overlap
                                            ? 'Concurrent runs permitted — use with caution'
                                            : 'Skip fire if previous run still active'}
                                    </span>
                                </div>
                                <div>
                                    <label className="text-sm text-muted-foreground">Dispatch Timeout (minutes)</label>
                                    <input
                                        type="number"
                                        min={1}
                                        placeholder="No timeout"
                                        value={formData.dispatch_timeout_minutes ?? ''}
                                        onChange={e => setFormData({
                                            ...formData,
                                            dispatch_timeout_minutes: e.target.value ? parseInt(e.target.value) : null,
                                        })}
                                        className="mt-1 w-full bg-background border border-muted rounded px-3 py-2 text-sm text-foreground placeholder-muted-foreground"
                                    />
                                    <p className="text-xs text-muted-foreground mt-1">
                                        PENDING jobs failing to dispatch within this window are auto-failed. Leave blank for no timeout.
                                        <em className="ml-1">(Distinct from Execution Timeout which kills running jobs.)</em>
                                    </p>
                                </div>
                                <Input
                                    id="job-target"
                                    placeholder="Target Node ID (Optional)"
                                    className="bg-background border-muted h-11 font-mono"
                                    value={formData.target_node_id}
                                    onChange={e => setFormData({ ...formData, target_node_id: e.target.value })}
                                    aria-label="Target Node ID"
                                />
                                <div className="relative">
                                    <Tag className="absolute left-3 top-3.5 h-4 w-4 text-muted-foreground/60" />
                                    <Input
                                        id="job-tags"
                                        placeholder="Tags: linux, gpu (Optional)"
                                        className="bg-background border-muted pl-10 h-11 font-mono"
                                        value={formData.target_tags}
                                        onChange={e => setFormData({ ...formData, target_tags: e.target.value })}
                                        aria-label="Target tags (comma-separated)"
                                    />
                                </div>
                                <div className="relative">
                                    <Cpu className="absolute left-3 top-3.5 h-4 w-4 text-muted-foreground/60" />
                                    <Input
                                        id="job-caps"
                                        placeholder="Caps: python:3.11, docker:24 (Optional)"
                                        className="bg-background border-muted pl-10 h-11 font-mono"
                                        value={formData.capability_requirements}
                                        onChange={e => setFormData({ ...formData, capability_requirements: e.target.value })}
                                        aria-label="Capability requirements (key:version, comma-separated)"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="job-signature-id" className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Root of Trust</Label>
                            <Select
                                value={formData.signature_id}
                                onValueChange={(val) => setFormData({ ...formData, signature_id: val })}
                            >
                                <SelectTrigger id="job-signature-id" className="bg-background border-muted h-11">
                                    <SelectValue placeholder="Establish Identity..." />
                                </SelectTrigger>
                                <SelectContent className="bg-card border-muted text-foreground">
                                    {signatures.map(s => (
                                        <SelectItem key={s.id} value={s.id}>
                                            {s.name} ({s.uploaded_by})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="job-signature" className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Signature Payload (B64)</Label>
                            <Textarea
                                id="job-signature"
                                placeholder="Paste Ed25519/RSA signature..."
                                className="bg-background border-muted h-24 font-mono text-xs text-muted-foreground"
                                value={formData.signature}
                                onChange={e => setFormData({ ...formData, signature: e.target.value })}
                                required
                                aria-describedby="signature-help"
                            />
                            {isEditMode && (
                                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-950/30 border border-amber-800/50">
                                    <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" aria-hidden="true" />
                                    <p className="text-xs text-amber-400 leading-normal">
                                        If you change the script content, you must provide a new signature. The server will reject any payload where the signature doesn't match.
                                    </p>
                                </div>
                            )}
                            <div className="flex items-start gap-2 p-3 rounded-lg bg-background border border-muted" id="signature-help">
                                <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" aria-hidden="true" />
                                <p className="text-xs text-muted-foreground leading-normal">
                                    Use the system CLI or <code>openssl</code> to sign the script. If the signature doesn't match the script bytes exactly, nodes will reject the payload with a <code>SIGNATURE_INVALID</code> alert.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="job-script" className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Python Payload Source</Label>
                        <div className="relative h-full flex flex-col">
                            <div className="absolute top-3 left-3 h-4 w-4 text-muted-foreground/60 pointer-events-none">
                                <Code2 className="h-full w-full" />
                            </div>
                            <Textarea
                                id="job-script"
                                className="flex-1 min-h-[400px] bg-background border-muted pl-10 pt-3 text-green-500 font-mono text-sm resize-none focus:ring-1 focus:ring-primary/20"
                                placeholder="import os\nprint('Identity verified')"
                                value={formData.script_content}
                                onChange={e => setFormData({ ...formData, script_content: e.target.value })}
                                required
                                aria-label="Python script source code"
                            />
                        </div>
                    </div>

                    <DialogFooter className="col-span-full pt-4 border-t border-muted mt-2">
                        <Button type="button" variant="ghost" onClick={() => onClose(false)} className="text-muted-foreground">Abandon</Button>
                        <Button type="submit" className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-8 rounded-xl ring-2 ring-primary/20 ring-offset-2 ring-offset-background">
                            {isEditMode ? 'Save Changes' : 'Seal and Register'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};

export default JobDefinitionModal;
