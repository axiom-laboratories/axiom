import React, { useEffect, useState } from 'react';
import {
    Code2,
    Info,
    Tag,
    Cpu,
    AlertTriangle,
    CheckSquare,
    ChevronDown,
    ChevronRight,
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
    validation_exit_code: string;
    validation_stdout_regex: string;
    validation_json_path: string;
    validation_json_expected: string;
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
    validation_rules?: {
        exit_code?: number | null;
        stdout_regex?: string | null;
        json_path?: string | null;
        json_expected?: string | null;
    } | null;
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
    const [validationExpanded, setValidationExpanded] = useState(false);

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
            validation_exit_code: editingJob.validation_rules?.exit_code != null
                ? String(editingJob.validation_rules.exit_code)
                : '0',
            validation_stdout_regex: editingJob.validation_rules?.stdout_regex ?? '',
            validation_json_path: editingJob.validation_rules?.json_path ?? '',
            validation_json_expected: editingJob.validation_rules?.json_expected ?? '',
        });
        setValidationExpanded(!!(editingJob?.validation_rules && Object.values(editingJob.validation_rules).some(v => v != null && v !== '')));
    }, [editingJob]);

    const isEditMode = !!editingJob;

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="bg-zinc-925 border-zinc-800 text-white sm:max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-xl font-bold">
                        <Code2 className="h-5 w-5 text-primary" />
                        {isEditMode ? 'Edit Job Definition' : 'Seal & Schedule Payload'}
                    </DialogTitle>
                    <DialogDescription className="text-zinc-500">
                        {isEditMode
                            ? 'Update the job definition. If you change the script content, you must provide a new signature.'
                            : 'Create an immutable, cryptographically signed Python job. Every byte of the script is verified at runtime by the puppet nodes.'}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={onSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-8 py-6">
                    <div className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="job-name" className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Metadata</Label>
                            <div className="space-y-4">
                                <div className="relative">
                                    <Input
                                        id="job-name"
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
                                        id="job-cron"
                                        placeholder="* * * * *"
                                        className="bg-zinc-900 border-zinc-800 pl-14 h-11 font-mono"
                                        value={formData.schedule_cron}
                                        onChange={e => setFormData({ ...formData, schedule_cron: e.target.value })}
                                        aria-label="Cron schedule"
                                    />
                                </div>
                                <div className="flex items-center gap-3">
                                    <label className="text-sm text-zinc-400">Allow Overlap</label>
                                    <button
                                        type="button"
                                        onClick={() => setFormData({ ...formData, allow_overlap: !formData.allow_overlap })}
                                        className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                                            formData.allow_overlap
                                                ? 'bg-amber-600 text-white'
                                                : 'bg-zinc-700 text-zinc-300'
                                        }`}
                                    >
                                        {formData.allow_overlap ? 'Allowed' : 'Blocked (default)'}
                                    </button>
                                    <span className="text-xs text-zinc-500">
                                        {formData.allow_overlap
                                            ? 'Concurrent runs permitted — use with caution'
                                            : 'Skip fire if previous run still active'}
                                    </span>
                                </div>
                                <div>
                                    <label className="text-sm text-zinc-400">Dispatch Timeout (minutes)</label>
                                    <input
                                        type="number"
                                        min={1}
                                        placeholder="No timeout"
                                        value={formData.dispatch_timeout_minutes ?? ''}
                                        onChange={e => setFormData({
                                            ...formData,
                                            dispatch_timeout_minutes: e.target.value ? parseInt(e.target.value) : null,
                                        })}
                                        className="mt-1 w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
                                    />
                                    <p className="text-xs text-zinc-500 mt-1">
                                        PENDING jobs failing to dispatch within this window are auto-failed. Leave blank for no timeout.
                                        <em className="ml-1">(Distinct from Execution Timeout which kills running jobs.)</em>
                                    </p>
                                </div>
                                <Input
                                    id="job-target"
                                    placeholder="Target Node ID (Optional)"
                                    className="bg-zinc-900 border-zinc-800 h-11 font-mono"
                                    value={formData.target_node_id}
                                    onChange={e => setFormData({ ...formData, target_node_id: e.target.value })}
                                    aria-label="Target Node ID"
                                />
                                <div className="relative">
                                    <Tag className="absolute left-3 top-3.5 h-4 w-4 text-zinc-600" />
                                    <Input
                                        id="job-tags"
                                        placeholder="Tags: linux, gpu (Optional)"
                                        className="bg-zinc-900 border-zinc-800 pl-10 h-11 font-mono"
                                        value={formData.target_tags}
                                        onChange={e => setFormData({ ...formData, target_tags: e.target.value })}
                                        aria-label="Target tags (comma-separated)"
                                    />
                                </div>
                                <div className="relative">
                                    <Cpu className="absolute left-3 top-3.5 h-4 w-4 text-zinc-600" />
                                    <Input
                                        id="job-caps"
                                        placeholder="Caps: python:3.11, docker:24 (Optional)"
                                        className="bg-zinc-900 border-zinc-800 pl-10 h-11 font-mono"
                                        value={formData.capability_requirements}
                                        onChange={e => setFormData({ ...formData, capability_requirements: e.target.value })}
                                        aria-label="Capability requirements (key:version, comma-separated)"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="job-signature-id" className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Root of Trust</Label>
                            <Select
                                value={formData.signature_id}
                                onValueChange={(val) => setFormData({ ...formData, signature_id: val })}
                            >
                                <SelectTrigger id="job-signature-id" className="bg-zinc-900 border-zinc-800 h-11">
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
                            <Label htmlFor="job-signature" className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Signature Payload (B64)</Label>
                            <Textarea
                                id="job-signature"
                                placeholder="Paste Ed25519/RSA signature..."
                                className="bg-zinc-900 border-zinc-800 h-24 font-mono text-xs text-zinc-400"
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
                            <div className="flex items-start gap-2 p-3 rounded-lg bg-zinc-900 border border-zinc-800" id="signature-help">
                                <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" aria-hidden="true" />
                                <p className="text-xs text-zinc-500 leading-normal">
                                    Use the system CLI or <code>openssl</code> to sign the script. If the signature doesn't match the script bytes exactly, nodes will reject the payload with a <code>SIGNATURE_INVALID</code> alert.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="job-script" className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Python Payload Source</Label>
                        <div className="relative h-full flex flex-col">
                            <div className="absolute top-3 left-3 h-4 w-4 text-zinc-700 pointer-events-none">
                                <Code2 className="h-full w-full" />
                            </div>
                            <Textarea
                                id="job-script"
                                className="flex-1 min-h-[400px] bg-zinc-950 border-zinc-800 pl-10 pt-3 text-green-500 font-mono text-sm resize-none focus:ring-1 focus:ring-primary/20"
                                placeholder="import os\nprint('Identity verified')"
                                value={formData.script_content}
                                onChange={e => setFormData({ ...formData, script_content: e.target.value })}
                                required
                                aria-label="Python script source code"
                            />
                        </div>
                    </div>

                    {/* Validation Rules */}
                    <div className="col-span-full border border-zinc-800 rounded-lg overflow-hidden">
                        <button
                            type="button"
                            className="w-full flex items-center justify-between px-4 py-2.5 bg-zinc-900/50 hover:bg-zinc-900 transition-colors text-sm font-medium text-zinc-300"
                            onClick={() => setValidationExpanded(v => !v)}
                        >
                            <span className="flex items-center gap-2">
                                <CheckSquare className="h-4 w-4 text-zinc-500" />
                                Validation Rules
                            </span>
                            {validationExpanded
                                ? <ChevronDown className="h-4 w-4 text-zinc-500" />
                                : <ChevronRight className="h-4 w-4 text-zinc-500" />
                            }
                        </button>
                        {validationExpanded && (
                            <div className="px-4 py-4 space-y-4 bg-zinc-950/30">
                                {/* Exit code */}
                                <div className="space-y-1.5">
                                    <Label htmlFor="validation_exit_code" className="text-xs text-zinc-400">
                                        Expected exit code
                                    </Label>
                                    <Input
                                        id="validation_exit_code"
                                        type="number"
                                        placeholder="0 — clear to disable"
                                        value={formData.validation_exit_code}
                                        onChange={e => setFormData({ ...formData, validation_exit_code: e.target.value })}
                                        className="h-8 text-xs"
                                    />
                                    <p className="text-[11px] text-zinc-600">Leave empty to skip exit code validation. Default: 0.</p>
                                </div>

                                {/* Stdout regex */}
                                <div className="space-y-1.5">
                                    <Label htmlFor="validation_stdout_regex" className="text-xs text-zinc-400">
                                        Stdout regex (optional)
                                    </Label>
                                    <Input
                                        id="validation_stdout_regex"
                                        placeholder="e.g. SUCCESS|ok"
                                        value={formData.validation_stdout_regex}
                                        onChange={e => setFormData({ ...formData, validation_stdout_regex: e.target.value })}
                                        className="h-8 text-xs font-mono"
                                    />
                                    <p className="text-[11px] text-zinc-600">Job fails if stdout does not match this pattern. Empty = not enforced.</p>
                                </div>

                                {/* JSON field assertion */}
                                <div className="space-y-1.5">
                                    <Label className="text-xs text-zinc-400">JSON field assertion (optional)</Label>
                                    <div className="flex gap-2">
                                        <div className="flex-1 space-y-1">
                                            <Input
                                                placeholder="JSON path, e.g. result.status"
                                                value={formData.validation_json_path}
                                                onChange={e => setFormData({ ...formData, validation_json_path: e.target.value })}
                                                className="h-8 text-xs font-mono"
                                            />
                                        </div>
                                        <div className="flex-1 space-y-1">
                                            <Input
                                                placeholder="Expected value, e.g. ok"
                                                value={formData.validation_json_expected}
                                                onChange={e => setFormData({ ...formData, validation_json_expected: e.target.value })}
                                                className="h-8 text-xs"
                                            />
                                        </div>
                                    </div>
                                    <p className="text-[11px] text-zinc-600">Both fields must be filled. Parses stdout as JSON and checks the path value equals expected.</p>
                                </div>
                            </div>
                        )}
                    </div>

                    <DialogFooter className="col-span-full pt-4 border-t border-zinc-800 mt-2">
                        <Button type="button" variant="ghost" onClick={() => onClose(false)} className="text-zinc-500">Abandon</Button>
                        <Button type="submit" className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-8 rounded-xl ring-2 ring-primary/20 ring-offset-2 ring-offset-zinc-925">
                            {isEditMode ? 'Save Changes' : 'Seal and Register'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};

export default JobDefinitionModal;
