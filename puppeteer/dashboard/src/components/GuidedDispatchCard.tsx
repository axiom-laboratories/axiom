import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { ChevronDown, ChevronUp, Play, X } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { authenticatedFetch } from '../auth';

// ─── Types ────────────────────────────────────────────────────────────────────

interface NodeItem {
    node_id: string;
    hostname?: string;
    tags?: string[];
}

interface SignatureEntry {
    id: string;
    name: string;
    uploaded_by?: string;
}

interface GuidedFormState {
    name: string;
    runtime: 'python' | 'bash' | 'powershell';
    scriptContent: string;
    targetNodeId: string;
    targetTags: string[];
    capabilityReqs: string[];
    signatureId: string;
    signature: string;
    signatureCleared: boolean;
}

const INITIAL_FORM: GuidedFormState = {
    name: '',
    runtime: 'python',
    scriptContent: '',
    targetNodeId: '',
    targetTags: [],
    capabilityReqs: [],
    signatureId: '',
    signature: '',
    signatureCleared: false,
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface GuidedDispatchCardProps {
    nodes: NodeItem[];
    onJobCreated: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

const GuidedDispatchCard = ({ nodes, onJobCreated }: GuidedDispatchCardProps) => {
    const [form, setForm] = useState<GuidedFormState>(INITIAL_FORM);
    const [tagInput, setTagInput] = useState('');
    const [capInput, setCapInput] = useState('');
    const [previewOpen, setPreviewOpen] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [signatures, setSignatures] = useState<SignatureEntry[]>([]);

    // Fetch key IDs on mount
    useEffect(() => {
        authenticatedFetch('/signatures')
            .then(r => r.ok ? r.json() : { items: [], results: [] })
            .then(data => {
                const items: any[] = Array.isArray(data)
                    ? data
                    : (data.items ?? data.results ?? []);
                setSignatures(items.map((s: any) => ({
                    id: s.id ?? s.key_id ?? '',
                    name: s.name ?? s.key_name ?? s.id ?? '',
                    uploaded_by: s.uploaded_by ?? s.created_by ?? '',
                })));
            })
            .catch(() => {/* non-critical */});
    }, []);

    // Stale signature detection (Pattern 3)
    const prevScriptRef = useRef(form.scriptContent);
    useEffect(() => {
        if (form.scriptContent !== prevScriptRef.current && form.signature) {
            setForm(f => ({ ...f, signature: '', signatureId: '', signatureCleared: true }));
        }
        prevScriptRef.current = form.scriptContent;
    }, [form.scriptContent]); // eslint-disable-line react-hooks/exhaustive-deps

    // Tag suggestions derived from nodes prop (no extra API call)
    const tagSuggestions = useMemo(
        () => [...new Set(nodes.flatMap(n => n.tags ?? []))].sort(),
        [nodes]
    );
    // Suppress unused var warning — tagSuggestions used in future datalist
    void tagSuggestions;

    // Generated payload (useMemo over form state)
    const generatedPayload = useMemo(() => {
        const allTargetTags: string[] = [];
        if (form.targetNodeId) allTargetTags.push(form.targetNodeId);
        allTargetTags.push(...form.targetTags);

        const capDict: Record<string, string> = {};
        for (const chip of form.capabilityReqs) {
            const idx = chip.indexOf(':');
            if (idx > 0) {
                capDict[chip.slice(0, idx).trim()] = chip.slice(idx + 1).trim();
            }
        }

        const payload: Record<string, unknown> = {
            task_type: 'script',
            payload: { script: form.scriptContent },
            runtime: form.runtime,
        };
        if (form.name) payload.name = form.name;
        if (allTargetTags.length) payload.target_tags = allTargetTags;
        if (Object.keys(capDict).length) payload.capability_requirements = capDict;
        if (form.signatureId) payload.signature_id = form.signatureId;
        if (form.signature) payload.signature = form.signature;

        return payload;
    }, [form]);

    // Dispatch enable conditions
    const hasTargeting = form.targetNodeId || form.targetTags.length > 0 || form.capabilityReqs.length > 0;
    const canDispatch = hasTargeting && form.signatureId && form.signature;

    // ── Chip helpers ──────────────────────────────────────────────────────────

    const addTargetTag = useCallback((value: string) => {
        const trimmed = value.trim().replace(/,$/, '');
        if (trimmed && !form.targetTags.includes(trimmed)) {
            setForm(f => ({ ...f, targetTags: [...f.targetTags, trimmed] }));
        }
        setTagInput('');
    }, [form.targetTags]);

    const removeTargetTag = (tag: string) => {
        setForm(f => ({ ...f, targetTags: f.targetTags.filter(t => t !== tag) }));
    };

    const addCapReq = useCallback((value: string) => {
        const trimmed = value.trim().replace(/,$/, '');
        if (trimmed && !form.capabilityReqs.includes(trimmed)) {
            setForm(f => ({ ...f, capabilityReqs: [...f.capabilityReqs, trimmed] }));
        }
        setCapInput('');
    }, [form.capabilityReqs]);

    const removeCapReq = (cap: string) => {
        setForm(f => ({ ...f, capabilityReqs: f.capabilityReqs.filter(c => c !== cap) }));
    };

    // ── Dispatch handler ──────────────────────────────────────────────────────

    const handleDispatch = async () => {
        setIsSubmitting(true);
        try {
            const res = await authenticatedFetch('/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(generatedPayload),
            });
            if (res.status === 200 || res.status === 201 || res.ok) {
                toast.success('Job dispatched successfully');
                onJobCreated();
                setForm(INITIAL_FORM);
                setTagInput('');
                setCapInput('');
                setPreviewOpen(false);
            } else {
                const err = await res.json().catch(() => ({}));
                toast.error(err.detail || 'Failed to dispatch job');
            }
        } catch (e) {
            console.error(e);
            toast.error('Failed to dispatch job');
        } finally {
            setIsSubmitting(false);
        }
    };

    // ── Render ────────────────────────────────────────────────────────────────

    return (
        <Card className="bg-zinc-925 border-zinc-800/50">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-bold text-white">Dispatch Job</CardTitle>
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs text-zinc-500 border-zinc-700 hover:text-white"
                        aria-label="Advanced mode"
                    >
                        ADV
                    </Button>
                </div>
            </CardHeader>

            <CardContent className="space-y-4">

                {/* Name */}
                <div className="space-y-1.5">
                    <label htmlFor="guided-name" className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">
                        Name <span className="text-zinc-600 normal-case font-normal">(optional)</span>
                    </label>
                    <Input
                        id="guided-name"
                        placeholder="Job name..."
                        value={form.name}
                        onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                        className="bg-zinc-900 border-zinc-800 text-white h-9 text-sm placeholder:text-zinc-600"
                    />
                </div>

                {/* Runtime */}
                <div className="space-y-1.5">
                    <label htmlFor="guided-runtime" className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">
                        Runtime
                    </label>
                    <Select
                        value={form.runtime}
                        onValueChange={v => setForm(f => ({ ...f, runtime: v as 'python' | 'bash' | 'powershell' }))}
                    >
                        <SelectTrigger id="guided-runtime" className="bg-zinc-900 border-zinc-800 text-white h-9 text-sm">
                            <SelectValue placeholder="Select runtime" />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                            <SelectItem value="python">Python</SelectItem>
                            <SelectItem value="bash">Bash</SelectItem>
                            <SelectItem value="powershell">PowerShell</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {/* Script content */}
                <div className="space-y-1.5">
                    <label htmlFor="guided-script" className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">
                        Script
                    </label>
                    <textarea
                        id="guided-script"
                        aria-label="Script content"
                        placeholder="# Enter your script here..."
                        value={form.scriptContent}
                        onChange={e => setForm(f => ({ ...f, scriptContent: e.target.value }))}
                        className="w-full h-36 px-3 py-2 bg-zinc-900 border border-zinc-800 text-green-400 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all resize-y placeholder:text-zinc-600"
                    />
                </div>

                {/* Targeting */}
                <div className="space-y-3 border border-zinc-800 rounded-lg p-3">
                    <p className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">Targeting</p>

                    {/* Node dropdown */}
                    <div className="space-y-1">
                        <label htmlFor="guided-node" className="text-xs text-zinc-500">Node (optional)</label>
                        <Select
                            value={form.targetNodeId || '__none__'}
                            onValueChange={v => setForm(f => ({ ...f, targetNodeId: v === '__none__' ? '' : v }))}
                        >
                            <SelectTrigger id="guided-node" className="bg-zinc-900 border-zinc-800 text-white h-9 text-sm">
                                <SelectValue placeholder="Any node" />
                            </SelectTrigger>
                            <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                                <SelectItem value="__none__">Any node</SelectItem>
                                {nodes.map(n => (
                                    <SelectItem key={n.node_id} value={n.node_id}>
                                        {n.hostname ? `${n.hostname} (${n.node_id.slice(0, 8)})` : n.node_id}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Target tags chips */}
                    <div className="space-y-1">
                        <label htmlFor="guided-target-tags" className="text-xs text-zinc-500">
                            Target tags <span className="text-zinc-600">(Enter or comma to add)</span>
                        </label>
                        {form.targetTags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mb-1">
                                {form.targetTags.map(tag => (
                                    <span
                                        key={tag}
                                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-800 text-xs text-zinc-300 border border-zinc-700"
                                    >
                                        {tag}
                                        <button
                                            type="button"
                                            onClick={() => removeTargetTag(tag)}
                                            className="hover:text-white text-zinc-500"
                                            aria-label={`Remove tag ${tag}`}
                                        >
                                            <X className="h-2.5 w-2.5" />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                        <Input
                            id="guided-target-tags"
                            placeholder="e.g. linux, gpu"
                            value={tagInput}
                            onChange={e => setTagInput(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' || e.key === ',') {
                                    e.preventDefault();
                                    addTargetTag(tagInput);
                                }
                            }}
                            onBlur={() => { if (tagInput.trim()) addTargetTag(tagInput); }}
                            className="bg-zinc-900 border-zinc-800 text-white h-8 text-sm placeholder:text-zinc-600 font-mono"
                        />
                    </div>

                    {/* Capability chips */}
                    <div className="space-y-1">
                        <label htmlFor="guided-cap-reqs" className="text-xs text-zinc-500">
                            Capability requirements <span className="text-zinc-600">(key:value format)</span>
                        </label>
                        {form.capabilityReqs.length > 0 && (
                            <div className="flex flex-wrap gap-1 mb-1">
                                {form.capabilityReqs.map(cap => (
                                    <span
                                        key={cap}
                                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-900/30 text-xs text-blue-300 border border-blue-800/50"
                                    >
                                        {cap}
                                        <button
                                            type="button"
                                            onClick={() => removeCapReq(cap)}
                                            className="hover:text-white text-blue-500/70"
                                            aria-label={`Remove capability ${cap}`}
                                        >
                                            <X className="h-2.5 w-2.5" />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                        <Input
                            id="guided-cap-reqs"
                            placeholder="e.g. python:3.11"
                            value={capInput}
                            onChange={e => setCapInput(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' || e.key === ',') {
                                    e.preventDefault();
                                    addCapReq(capInput);
                                }
                            }}
                            onBlur={() => { if (capInput.trim()) addCapReq(capInput); }}
                            className="bg-zinc-900 border-zinc-800 text-white h-8 text-sm placeholder:text-zinc-600 font-mono"
                        />
                    </div>
                </div>

                {/* Sign section */}
                <div className="space-y-3 border border-zinc-800 rounded-lg p-3">
                    <p className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">Sign</p>

                    {/* Stale signature warning */}
                    {form.signatureCleared && (
                        <div className="rounded-md bg-amber-900/30 border border-amber-700/50 px-3 py-2 text-xs text-amber-300">
                            Script changed — signature cleared. Re-sign before dispatching.
                        </div>
                    )}

                    {/* Key ID dropdown */}
                    <div className="space-y-1">
                        <label htmlFor="guided-key-id" className="text-xs text-zinc-500">Key ID</label>
                        <Select
                            value={form.signatureId || '__none__'}
                            onValueChange={v => setForm(f => ({
                                ...f,
                                signatureId: v === '__none__' ? '' : v,
                                signatureCleared: false,
                            }))}
                        >
                            <SelectTrigger id="guided-key-id" className="bg-zinc-900 border-zinc-800 text-white h-9 text-sm">
                                <SelectValue placeholder="Select signing key" />
                            </SelectTrigger>
                            <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                                <SelectItem value="__none__">Select signing key</SelectItem>
                                {signatures.map(s => (
                                    <SelectItem key={s.id} value={s.id}>
                                        {s.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Signature textarea */}
                    <div className="space-y-1">
                        <label htmlFor="guided-signature" className="text-xs text-zinc-500">Signature (base64)</label>
                        <textarea
                            id="guided-signature"
                            aria-label="Signature"
                            placeholder="Paste Ed25519 signature here..."
                            value={form.signature}
                            onChange={e => setForm(f => ({ ...f, signature: e.target.value, signatureCleared: false }))}
                            className="w-full h-16 px-3 py-2 bg-zinc-900 border border-zinc-800 text-zinc-300 rounded-md font-mono text-xs focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all resize-none placeholder:text-zinc-600"
                        />
                    </div>
                </div>

                {/* JSON Preview accordion */}
                <div className="border border-zinc-800 rounded-lg overflow-hidden">
                    <button
                        type="button"
                        onClick={() => setPreviewOpen(v => !v)}
                        className="w-full flex items-center justify-between px-3 py-2 text-xs text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition-colors"
                        aria-expanded={previewOpen}
                        aria-controls="guided-payload-preview"
                    >
                        <span className="font-semibold uppercase tracking-widest">Generated Payload</span>
                        {previewOpen
                            ? <ChevronUp className="h-3.5 w-3.5" />
                            : <ChevronDown className="h-3.5 w-3.5" />
                        }
                    </button>
                    {previewOpen && (
                        <div id="guided-payload-preview" className="bg-zinc-950 border-t border-zinc-800 p-3">
                            <pre className="text-green-400 font-mono text-xs whitespace-pre-wrap overflow-auto max-h-64">
                                {JSON.stringify(generatedPayload, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>

                {/* Dispatch button */}
                <Button
                    className="w-full h-11 bg-primary hover:bg-primary/90 text-white font-bold rounded-xl shadow-lg shadow-primary/10 transition-all active:scale-[0.98]"
                    onClick={handleDispatch}
                    disabled={!canDispatch || isSubmitting}
                    aria-label="Dispatch job"
                >
                    <Play className="mr-2 h-4 w-4 fill-current" />
                    {isSubmitting ? 'Dispatching...' : 'Dispatch Job'}
                </Button>

            </CardContent>
        </Card>
    );
};

export { GuidedDispatchCard };
export default GuidedDispatchCard;
