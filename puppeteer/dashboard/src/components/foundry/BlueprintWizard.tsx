import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
    ArrowRight, 
    Layers, 
    Globe, 
    CheckCircle2, 
    Copy, 
    Terminal, 
    AlertCircle,
    Loader2,
    Cpu,
    Search,
    Package,
    Plus, 
    X, 
    Wrench,
    Check
    } from 'lucide-react';

import { toast } from 'sonner';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter
} from '@/components/ui/dialog';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { authenticatedFetch } from '@/auth';

interface EditBlueprint {
    id: string;
    name: string;
    type: string;
    definition: any;
    version: number;
    os_family?: string;
}

interface BlueprintWizardProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    editBlueprint?: EditBlueprint | null;
}

interface Composition {
    name: string;
    type: 'RUNTIME' | 'NETWORK';
    os_family: string;
    base_os: string;
    packages: {
        python: string[];
        system: string[];
    };
    tools: string[];
}

const DEFAULT_COMPOSITION: Composition = {
    name: '',
    type: 'RUNTIME',
    os_family: 'DEBIAN',
    base_os: 'debian-12-slim',
    packages: {
        python: [],
        system: []
    },
    tools: []
};

const BlueprintWizard: React.FC<BlueprintWizardProps> = ({ open, onOpenChange, editBlueprint }) => {
    const queryClient = useQueryClient();
    const [step, setStep] = useState(1);
    const [composition, setComposition] = useState<Composition>(DEFAULT_COMPOSITION);
    const [isAdvanced, setIsAdvanced] = useState(false);
    const [pendingDeps, setPendingDeps] = useState<string[]>([]);
    const [showDepDialog, setShowDepDialog] = useState(false);
    const [pendingPayload, setPendingPayload] = useState<any>(null);

    const isEditMode = !!editBlueprint;

    // --- Data Fetching ---
    const { data: blueprints = [] } = useQuery({
        queryKey: ['blueprints'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/blueprints');
            return res.json();
        },
        enabled: open
    });

    // Reset wizard when opening — pre-populate in edit mode
    useEffect(() => {
        if (open) {
            setPendingDeps([]);
            setShowDepDialog(false);
            setPendingPayload(null);
            setIsAdvanced(false);

            if (editBlueprint) {
                try {
                    const def = typeof editBlueprint.definition === 'string'
                        ? JSON.parse(editBlueprint.definition)
                        : editBlueprint.definition;
                    setComposition({
                        name: editBlueprint.name,
                        type: editBlueprint.type as 'RUNTIME' | 'NETWORK',
                        os_family: editBlueprint.os_family || 'DEBIAN',
                        base_os: def.base_os || 'debian-12-slim',
                        packages: def.packages || { python: [], system: [] },
                        tools: (def.tools || []).map((t: any) => t.id),
                    });
                    setStep(1);
                } catch {
                    toast.error('Failed to parse blueprint definition for editing');
                    setComposition(DEFAULT_COMPOSITION);
                    setStep(1);
                }
            } else {
                setStep(1);
                setComposition(DEFAULT_COMPOSITION);
            }
        }
    }, [open, editBlueprint]);

    const handleClone = (blueprint: any) => {
        try {
            const def = JSON.parse(blueprint.definition);
            setComposition({
                name: `${blueprint.name} (Clone)`,
                type: blueprint.type,
                os_family: blueprint.os_family || 'DEBIAN',
                base_os: def.base_os || 'debian-12-slim',
                packages: def.packages || { python: [], system: [] },
                tools: (def.tools || []).map((t: any) => t.id),
            });
            toast.success(`Cloned from ${blueprint.name}`);
            setStep(2); // Jump to base image selection
        } catch (e) {
            toast.error('Failed to parse blueprint definition');
        }
    };

    const { data: approvedOS = [] } = useQuery({
        queryKey: ['approved-os'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/approved-os');
            return res.json();
        },
        enabled: open
    });

    const { data: ingredients = [] } = useQuery({
        queryKey: ['smelter-ingredients'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/smelter/ingredients');
            return res.json();
        },
        enabled: open
    });

    const { data: matrix = [] } = useQuery({
        queryKey: ['capability-matrix'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/capability-matrix');
            return res.json();
        },
        enabled: open
    });

    const saveMutation = useMutation({
        mutationFn: async (payload: any) => {
            const url = isEditMode
                ? `/api/blueprints/${editBlueprint!.id}`
                : '/api/blueprints';
            const method = isEditMode ? 'PATCH' : 'POST';

            const body = isEditMode
                ? { ...payload, version: editBlueprint!.version }
                : payload;

            const res = await authenticatedFetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (res.status === 422) {
                const err = await res.json();
                if (err.detail?.error === 'deps_required') {
                    // Store deps for confirmation dialog
                    setPendingDeps(err.detail.deps_to_confirm || []);
                    setPendingPayload(body);
                    setShowDepDialog(true);
                    return { __depsRequired: true };
                }
                throw new Error(typeof err.detail === 'string' ? err.detail : 'Validation error');
            }

            if (res.status === 409) {
                toast.error('Blueprint was modified by another user. Your changes were not saved.');
                onOpenChange(false);
                return { __conflict: true };
            }

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || `Failed to ${isEditMode ? 'update' : 'create'} blueprint`);
            }
            return res.json();
        },
        onSuccess: (data) => {
            if (data?.__depsRequired || data?.__conflict) return;
            queryClient.invalidateQueries({ queryKey: ['blueprints'] });
            toast.success(isEditMode ? 'Image Recipe updated successfully' : 'Image Recipe created successfully');
            onOpenChange(false);
        },
        onError: (e: Error) => toast.error(e.message)
    });

    const handleConfirmDeps = () => {
        setShowDepDialog(false);
        if (pendingPayload) {
            const withDeps = { ...pendingPayload, confirmed_deps: pendingDeps };
            saveMutation.mutate(withDeps);
        }
    };

    const getFinalJson = () => {
        return {
            name: composition.name,
            type: composition.type,
            os_family: composition.os_family,
            definition: JSON.stringify({
                base_os: composition.base_os,
                packages: composition.packages,
                tools: composition.tools.map(tid => {
                    const t = matrix.find((m: any) => m.tool_id === tid && m.base_os_family === composition.os_family);
                    return {
                        id: tid,
                        injection_recipe: t?.injection_recipe || '',
                        validation_cmd: t?.validation_cmd || '',
                        artifact_id: t?.artifact_id
                    };
                })
            })
        };
    };

    const handleFinish = () => {
        saveMutation.mutate(getFinalJson());
    };

    const nextStep = () => setStep(s => Math.min(s + 1, 5));
    const prevStep = () => setStep(s => Math.max(s - 1, 1));

    // --- Step Renderers ---

    const Step5Review = () => {
        const finalPayload = getFinalJson();
        const definition = JSON.parse(finalPayload.definition);
        
        return (
            <div className="space-y-6 py-4 animate-in slide-in-from-right-2 duration-300">
                <div className="grid grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 space-y-3">
                            <h4 className="text-xs uppercase tracking-wider text-zinc-500 font-bold">Summary</h4>
                            <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="text-zinc-400">Name</span>
                                    <span className="text-white font-medium">{composition.name}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-zinc-400">Base OS</span>
                                    <span className="text-white font-medium">{composition.base_os}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-zinc-400">Tools</span>
                                    <Badge variant="outline">{composition.tools.length}</Badge>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-zinc-400">Packages</span>
                                    <Badge variant="outline">{composition.packages.python.length}</Badge>
                                </div>
                            </div>
                        </div>

                        <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 space-y-2">
                            <div className="flex items-center gap-2 text-emerald-500 font-bold text-sm">
                                <CheckCircle2 className="h-4 w-4" /> Ready for Smelting
                            </div>
                            <p className="text-[11px] text-zinc-400">This blueprint follows all safety and compatibility guardrails.</p>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label className="text-xs uppercase tracking-wider text-zinc-500 font-bold">JSON Definition</Label>
                        <pre className="h-[300px] overflow-auto bg-black border border-zinc-800 rounded-xl p-4 font-mono text-[10px] text-primary/80 custom-scrollbar">
                            {JSON.stringify(definition, null, 2)}
                        </pre>
                    </div>
                </div>
            </div>
        );
    };

    const Step4Tools = () => {
        const [search, setSearch] = useState('');
        const filtered = matrix.filter((t: any) => 
            t.base_os_family === composition.os_family &&
            t.tool_id.toLowerCase().includes(search.toLowerCase()) &&
            t.is_active
        );

        const toggleTool = (tool: any) => {
            const current = [...composition.tools];
            if (current.includes(tool.tool_id)) {
                setComposition({
                    ...composition,
                    tools: current.filter(t => t !== tool.tool_id)
                });
            } else {
                // Auto-inject dependencies
                const newDeps = tool.runtime_dependencies || [];
                const currentPackages = [...composition.packages.python];
                const updatedPackages = [...new Set([...currentPackages, ...newDeps])];
                
                setComposition({
                    ...composition,
                    tools: [...current, tool.tool_id],
                    packages: { ...composition.packages, python: updatedPackages }
                });

                if (newDeps.length > 0) {
                    toast.info(`Added ${newDeps.length} dependencies for ${tool.tool_id}`, {
                        description: newDeps.join(', ')
                    });
                }
            }
        };

        return (
            <div className="space-y-6 py-4 animate-in slide-in-from-right-2 duration-300">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                    <Input 
                        placeholder="Search compatible tools..." 
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="pl-10 bg-zinc-950 border-zinc-800"
                    />
                </div>

                <div className="space-y-4">
                    <Label className="text-xs uppercase tracking-wider text-zinc-500 font-bold">Selected Tools ({composition.tools.length})</Label>
                    <div className="flex flex-wrap gap-2">
                        {composition.tools.length === 0 && <div className="text-xs text-zinc-600 italic">No tools selected.</div>}
                        {composition.tools.map(t => (
                            <Badge key={t} className="bg-primary/20 text-primary border-primary/30 py-1 px-2 gap-1">
                                <Wrench className="h-3 w-3" />
                                {t}
                                <button onClick={() => {
                                    setComposition({
                                        ...composition,
                                        tools: composition.tools.filter(x => x !== t)
                                    });
                                }}>
                                    <X className="h-3 w-3 hover:text-white" />
                                </button>
                            </Badge>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-2 max-h-[250px] overflow-y-auto pr-2 custom-scrollbar">
                    {filtered.map((t: any) => {
                        const isSelected = composition.tools.includes(t.tool_id);
                        return (
                            <button
                                key={t.id}
                                onClick={() => toggleTool(t)}
                                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all text-left group ${
                                    isSelected 
                                    ? 'bg-primary/5 border-primary/50' 
                                    : 'bg-zinc-950 border-zinc-800 hover:border-zinc-700'
                                }`}
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`h-8 w-8 rounded flex items-center justify-center ${isSelected ? 'bg-primary text-white' : 'bg-zinc-900 text-zinc-500'}`}>
                                        <Wrench className="h-4 w-4" />
                                    </div>
                                    <div>
                                        <div className="text-sm font-bold text-white">{t.tool_id}</div>
                                        <div className="text-[10px] text-zinc-500">
                                            {t.runtime_dependencies?.length > 0 
                                                ? `Requires: ${t.runtime_dependencies.join(', ')}`
                                                : 'No extra dependencies'}
                                        </div>
                                    </div>
                                </div>
                                <div className={`h-6 w-6 rounded-md flex items-center justify-center border transition-all ${
                                    isSelected ? 'bg-primary border-primary text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-500 group-hover:border-zinc-600'
                                }`}>
                                    {isSelected ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>
        );
    };

    const Step3Ingredients = () => {
        const [search, setSearch] = useState('');
        const filtered = ingredients.filter((i: any) => 
            i.os_family === composition.os_family &&
            i.name.toLowerCase().includes(search.toLowerCase())
        );

        const togglePackage = (pkg: any) => {
            const pkgSpec = `${pkg.name}${pkg.version_constraint}`;
            const current = [...composition.packages.python];
            if (current.includes(pkgSpec)) {
                setComposition({
                    ...composition,
                    packages: { ...composition.packages, python: current.filter(p => p !== pkgSpec) }
                });
            } else {
                setComposition({
                    ...composition,
                    packages: { ...composition.packages, python: [...current, pkgSpec] }
                });
            }
        };

        return (
            <div className="space-y-6 py-4 animate-in slide-in-from-right-2 duration-300">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                    <Input 
                        placeholder="Search vetted ingredients..." 
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="pl-10 bg-zinc-950 border-zinc-800"
                    />
                </div>

                <div className="space-y-4">
                    <Label className="text-xs uppercase tracking-wider text-zinc-500 font-bold">Selected Packages ({composition.packages.python.length})</Label>
                    <div className="flex flex-wrap gap-2">
                        {composition.packages.python.length === 0 && <div className="text-xs text-zinc-600 italic">No packages selected.</div>}
                        {composition.packages.python.map(p => (
                            <Badge key={p} className="bg-primary/20 text-primary border-primary/30 py-1 px-2 gap-1">
                                {p}
                                <button onClick={() => {
                                    setComposition({
                                        ...composition,
                                        packages: { ...composition.packages, python: composition.packages.python.filter(x => x !== p) }
                                    });
                                }}>
                                    <X className="h-3 w-3 hover:text-white" />
                                </button>
                            </Badge>
                        ))}
                    </div>
                </div>

                <div className="space-y-2 max-h-[250px] overflow-y-auto pr-2 custom-scrollbar">
                    {filtered.map((i: any) => {
                        const pkgSpec = `${i.name}${i.version_constraint}`;
                        const isSelected = composition.packages.python.includes(pkgSpec);
                        return (
                            <button
                                key={i.id}
                                onClick={() => togglePackage(i)}
                                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all text-left group ${
                                    isSelected 
                                    ? 'bg-primary/5 border-primary/50' 
                                    : 'bg-zinc-950 border-zinc-800 hover:border-zinc-700'
                                }`}
                            >
                                <div className="flex items-center gap-3">
                                    <Package className={`h-4 w-4 ${isSelected ? 'text-primary' : 'text-zinc-500'}`} />
                                    <div>
                                        <div className="text-sm font-bold text-white">{i.name}</div>
                                        <div className="text-[10px] font-mono text-zinc-500">{i.version_constraint}</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    {i.mirror_status === 'MIRRORED' ? (
                                        <Badge variant="outline" className="text-[9px] border-emerald-500/20 text-emerald-500 bg-emerald-500/5">Mirror Ready</Badge>
                                    ) : (
                                        <Badge variant="outline" className="text-[9px] border-amber-500/20 text-amber-500 bg-amber-500/5">Sync Pending</Badge>
                                    )}
                                    {i.is_vulnerable && (
                                        <Badge variant="outline" className="text-[9px] border-red-500/20 text-red-500 bg-red-500/5">Vulnerable</Badge>
                                    )}
                                    <div className={`h-6 w-6 rounded-md flex items-center justify-center border transition-all ${
                                        isSelected ? 'bg-primary border-primary text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-500 group-hover:border-zinc-600'
                                    }`}>
                                        {isSelected ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                                    </div>
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>
        );
    };

    const Step2BaseOS = () => {
        const filtered = approvedOS.filter((os: any) => os.os_family === composition.os_family);
        
        return (
            <div className="space-y-6 py-4 animate-in slide-in-from-right-2 duration-300">
                <div className="flex items-center gap-3 p-4 rounded-xl bg-primary/5 border border-primary/20">
                    <Globe className="h-5 w-5 text-primary" />
                    <div>
                        <div className="text-sm font-bold text-white">Target Family: {composition.os_family}</div>
                        <div className="text-[11px] text-zinc-400">Showing only vetted images compatible with this family.</div>
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-3 max-h-[350px] overflow-y-auto pr-2 custom-scrollbar">
                    {filtered.length === 0 ? (
                        <div className="py-12 text-center text-zinc-500 border border-dashed border-zinc-800 rounded-xl">
                            No approved images found for {composition.os_family}
                        </div>
                    ) : (
                        filtered.map((os: any) => (
                            <button
                                key={os.id}
                                onClick={() => setComposition({...composition, base_os: os.image_uri})}
                                className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all text-left group ${
                                    composition.base_os === os.image_uri 
                                    ? 'bg-primary/10 border-primary shadow-lg shadow-primary/5' 
                                    : 'bg-zinc-950 border-zinc-800 hover:border-zinc-700'
                                }`}
                            >
                                <div className="flex items-center gap-4">
                                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                                        composition.base_os === os.image_uri ? 'bg-primary text-white' : 'bg-zinc-900 text-zinc-500'
                                    }`}>
                                        <Cpu className="h-5 w-5" />
                                    </div>
                                    <div>
                                        <div className="text-sm font-bold text-white flex items-center gap-2">
                                            {os.friendly_name}
                                            {os.is_compliant && <CheckCircle2 className="h-3 w-3 text-emerald-500" />}
                                        </div>
                                        <div className="text-xs font-mono text-zinc-500">{os.image_uri}</div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">Vetted At</div>
                                    <div className="text-[11px] text-zinc-400">{new Date(os.created_at).toLocaleDateString()}</div>
                                </div>
                            </button>
                        ))
                    )}
                </div>
            </div>
        );
    };

    const Step1Identity = () => (
        <div className="space-y-6 py-4">
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label>Image Recipe Name</Label>
                    <Input 
                        placeholder="e.g. secure-data-processor" 
                        value={composition.name}
                        onChange={e => setComposition({...composition, name: e.target.value})}
                        className="bg-zinc-950 border-zinc-800"
                    />
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label>Type</Label>
                        <Select value={composition.type} onValueChange={(v: any) => setComposition({...composition, type: v})}>
                            <SelectTrigger className="bg-zinc-950 border-zinc-800">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                                <SelectItem value="RUNTIME">RUNTIME</SelectItem>
                                <SelectItem value="NETWORK">NETWORK</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-2">
                        <Label>OS Family</Label>
                        <Select value={composition.os_family} onValueChange={v => setComposition({...composition, os_family: v})}>
                            <SelectTrigger className="bg-zinc-950 border-zinc-800">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                                <SelectItem value="DEBIAN">DEBIAN</SelectItem>
                                <SelectItem value="ALPINE">ALPINE</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            </div>

            <div className="relative">
                <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-zinc-800" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-zinc-925 px-2 text-zinc-500 font-bold">Or Clone Existing</span>
                </div>
            </div>

            <div className="space-y-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
                {blueprints.filter((b: any) => b.type === composition.type).map((b: any) => (
                    <button
                        key={b.id}
                        onClick={() => handleClone(b)}
                        className="w-full flex items-center justify-between p-3 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-primary/50 hover:bg-primary/5 transition-all text-left group"
                    >
                        <div>
                            <div className="text-sm font-bold text-white flex items-center gap-2">
                                <Copy className="h-3 w-3 text-zinc-500 group-hover:text-primary" />
                                {b.name}
                            </div>
                            <div className="text-[10px] text-zinc-500">{b.os_family} • v{b.version}</div>
                        </div>
                        <Badge variant="outline" className="text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">Clone</Badge>
                    </button>
                ))}
            </div>
        </div>
    );

    return (
        <>
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl bg-zinc-925 border-zinc-800 text-white">
                <DialogHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                                <Layers className="h-4 w-4 text-primary" />
                            </div>
                            <div>
                                <DialogTitle>{isEditMode ? 'Edit Image Recipe' : 'Create Image Recipe'}</DialogTitle>
                                <DialogDescription>
                                    Step {step} of 5: {
                                        step === 1 ? 'Identity' : 
                                        step === 2 ? 'Base Image' : 
                                        step === 3 ? 'Ingredients' :
                                        step === 4 ? 'Tools' :
                                        'Review'
                                    }
                                </DialogDescription>
                            </div>
                        </div>
                        <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-zinc-500 hover:text-white h-8"
                            onClick={() => setIsAdvanced(!isAdvanced)}
                        >
                            <Terminal className="h-3.5 w-3.5 mr-2" />
                            {isAdvanced ? 'Back to Wizard' : 'Advanced (JSON)'}
                        </Button>
                    </div>
                </DialogHeader>

                {/* Progress Bar */}
                <div className="flex gap-1 py-2">
                    {[1, 2, 3, 4, 5].map(i => (
                        <div 
                            key={i} 
                            className={`h-1 flex-1 rounded-full transition-all duration-500 ${step >= i ? 'bg-primary' : 'bg-zinc-800'}`} 
                        />
                    ))}
                </div>

                <div className="min-h-[400px]">
                    {!isAdvanced ? (
                        <>
                            {step === 1 && Step1Identity()}
                            {step === 2 && Step2BaseOS()}
                            {step === 3 && Step3Ingredients()}
                            {step === 4 && Step4Tools()}
                            {step === 5 && <Step5Review />}
                        </>
                    ) : (
                        <div className="space-y-4 py-4">
                            <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-500 text-xs">
                                <AlertCircle className="h-4 w-4 shrink-0" />
                                <span>Advanced mode bypasses wizard guardrails. Ensure your JSON follows the schema.</span>
                            </div>
                            <textarea 
                                className="w-full h-[300px] bg-zinc-950 border border-zinc-800 rounded-lg p-4 font-mono text-xs text-zinc-300 focus:outline-none focus:border-primary/50"
                                value={JSON.stringify(getFinalJson(), null, 2)}
                                readOnly
                            />
                        </div>
                    )}
                </div>

                <DialogFooter className="border-t border-zinc-800/50 pt-4">
                    <Button variant="ghost" onClick={() => step > 1 ? prevStep() : onOpenChange(false)} disabled={saveMutation.isPending}>
                        {step === 1 ? 'Cancel' : 'Back'}
                    </Button>
                    {!isAdvanced && (
                        step < 5 ? (
                            <Button 
                                className="bg-primary hover:bg-primary/90 text-white font-bold"
                                disabled={
                                    (step === 1 && !composition.name) ||
                                    (step === 2 && !composition.base_os) ||
                                    (step === 3 && composition.packages.python.length === 0 && composition.type === 'RUNTIME') ||
                                    (step === 4 && composition.tools.length === 0 && composition.type === 'RUNTIME')
                                }
                                onClick={nextStep}
                            >
                                Next <ArrowRight className="ml-2 h-4 w-4" />
                            </Button>
                        ) : (
                            <Button 
                                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
                                onClick={handleFinish}
                                disabled={saveMutation.isPending}
                            >
                                {saveMutation.isPending ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {isEditMode ? 'Saving...' : 'Creating...'}</>
                                ) : (
                                    <><Check className="mr-2 h-4 w-4" /> {isEditMode ? 'Save Changes' : 'Create Image Recipe'}</>
                                )}
                            </Button>
                        )
                    )}
                    {isAdvanced && (
                        <Button 
                            className="bg-primary hover:bg-primary/90 text-white font-bold"
                            onClick={handleFinish}
                            disabled={saveMutation.isPending}
                        >
                            {isEditMode ? 'Save Changes' : 'Save Image Recipe'}
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>

        <AlertDialog open={showDepDialog} onOpenChange={setShowDepDialog}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Required Dependencies</AlertDialogTitle>
                    <AlertDialogDescription>
                        These tools are required by your selected tools:
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <ul className="list-disc pl-6 my-4">
                    {pendingDeps.map(dep => <li key={dep}>{dep}</li>)}
                </ul>
                <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleConfirmDeps}>Add and Save</AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
        </>
    );
};

export default BlueprintWizard;
