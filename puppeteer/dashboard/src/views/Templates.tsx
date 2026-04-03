import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Boxes, CheckCircle2, Clock, AlertCircle, ShieldAlert, Loader2, Plus, Cpu, Globe, Zap, Trash2, RefreshCw, Wrench, X, Package, Layers, Pencil, Check, Monitor } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { authenticatedFetch } from '../auth';
import { useFeatures } from '../hooks/useFeatures';
import { UpgradePlaceholder } from '../components/UpgradePlaceholder';
import { CreateTemplateDialog } from '../components/CreateTemplateDialog';
import BlueprintWizard from '../components/foundry/BlueprintWizard';

interface Template {
    id: string;
    friendly_name: string;
    canonical_id: string;
    last_built_image?: string;
    last_built_at?: string;
    runtime_blueprint_id: string;
    network_blueprint_id: string;
    is_compliant: boolean;
    status?: string;
}

interface Blueprint {
    id: string;
    type: 'RUNTIME' | 'NETWORK';
    name: string;
    definition: any;
    version: number;
    created_at: string;
    os_family?: string;
}

interface ToolMatrix {
    id: number;
    base_os_family: string;
    tool_id: string;
    injection_recipe: string;
    validation_cmd: string;
    artifact_id?: string;
    runtime_dependencies: string[];
    is_active: boolean;
}

interface ApprovedOS {
    id: string;
    name: string;
    image_uri: string;
    os_family: string;
    is_active: boolean;
    created_at: string;
}

const StatusBadge = ({ status }: { status?: string }) => {
    switch (status) {
        case 'ACTIVE':
            return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 uppercase text-[10px] font-bold">Active</Badge>;
        case 'STAGING':
            return <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20 uppercase text-[10px] font-bold animate-pulse">Staging</Badge>;
        case 'FAILED':
            return <Badge className="bg-red-500/10 text-red-500 border-red-500/20 uppercase text-[10px] font-bold">Failed</Badge>;
        case 'DEPRECATED':
            return <Badge className="bg-muted/10 text-muted-foreground border-muted/20 uppercase text-[10px] font-bold">Deprecated</Badge>;
        case 'REVOKED':
            return <Badge className="bg-red-600/10 text-red-600 border-red-600/20 uppercase text-[10px] font-bold">Revoked</Badge>;
        default:
            return <Badge variant="outline" className="uppercase text-[10px] font-bold">{status || 'DRAFT'}</Badge>;
    }
};

const TemplateCard = ({ template, baseUpdatedAt }: { template: Template; baseUpdatedAt: string | null }) => {
    const queryClient = useQueryClient();
    const [buildStatus, setBuildStatus] = useState<'idle' | 'building' | 'success' | 'failed'>('idle');
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [showBuildDetails, setShowBuildDetails] = useState(false);
    const [isBOMOpen, setIsBOMOpen] = useState(false);

    const { data: bom } = useQuery({
        queryKey: ['bom', template.id],
        queryFn: async () => {
            const res = await authenticatedFetch(`/api/templates/${template.id}/bom`);
            if (!res.ok) return null;
            return res.json();
        },
        enabled: isBOMOpen
    });

    const updateStatusMutation = useMutation({
        mutationFn: async (newStatus: string) => {
            await authenticatedFetch(`/api/templates/${template.id}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });
        },
        onSuccess: (_, newStatus) => {
            queryClient.invalidateQueries({ queryKey: ['templates'] });
            toast.success(`Image marked as ${newStatus}`);
        }
    });

    const isStale = baseUpdatedAt && template.last_built_at
        ? new Date(template.last_built_at) < new Date(baseUpdatedAt)
        : false;

    const buildMutation = useMutation({
        mutationFn: async () => {
            const res = await authenticatedFetch(`/api/templates/${template.id}/build`, { method: 'POST' });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Build failed');
            }
            return await res.json();
        },
        onMutate: () => setBuildStatus('building'),
        onSuccess: () => {
            setBuildStatus('success');
            toast.success(`Build started for ${template.friendly_name}`);
            queryClient.invalidateQueries({ queryKey: ['templates'] });
        },
        onError: (e: Error) => {
            setBuildStatus('failed');
            toast.error(`Build failed: ${e.message}`);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: async () => {
            const res = await authenticatedFetch(`/api/templates/${template.id}`, { method: 'DELETE' });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Delete failed');
            }
        },
        onSuccess: () => {
            toast.success(`Node Image ${template.friendly_name} deleted`);
            queryClient.invalidateQueries({ queryKey: ['templates'] });
        },
        onError: (e: Error) => toast.error(`Delete failed: ${e.message}`),
    });

    return (
        <>
            <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Node Image?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete {template.friendly_name}? This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => deleteMutation.mutate()}
                            className="bg-red-600 hover:bg-red-700 text-foreground"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <Dialog open={isBOMOpen} onOpenChange={setIsBOMOpen}>
                <DialogContent className="bg-background border-muted text-foreground max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Package className="h-5 w-5 text-primary" />
                            Bill of Materials: {template.friendly_name}
                        </DialogTitle>
                        <DialogDescription className="text-muted-foreground">
                            Full snapshot of installed packages at build time.
                        </DialogDescription>
                    </DialogHeader>
                    
                    {bom ? (
                        <div className="grid grid-cols-2 gap-4 mt-4 h-[400px] overflow-auto pr-2 custom-scrollbar">
                            <div className="space-y-2">
                                <h4 className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest sticky top-0 bg-background py-1">Python (PIP)</h4>
                                {bom.pip.map((p: any) => (
                                    <div key={p.name} className="flex items-center justify-between p-2 rounded bg-secondary border border-muted text-xs">
                                        <span className="text-foreground font-medium">{p.name}</span>
                                        <span className="text-muted-foreground font-mono">{p.version}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="space-y-2">
                                <h4 className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest sticky top-0 bg-background py-1">System (APT)</h4>
                                {bom.apt.map((p: any) => (
                                    <div key={p.name} className="flex items-center justify-between p-2 rounded bg-secondary border border-muted text-xs">
                                        <span className="text-foreground font-medium truncate max-w-[120px]">{p.name}</span>
                                        <span className="text-muted-foreground font-mono">{p.version}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="py-12 text-center text-muted-foreground italic">BOM not yet captured for this image.</div>
                    )}
                    
                    <DialogFooter>
                        <Button onClick={() => setIsBOMOpen(false)}>Close</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Card className="bg-card border-muted/50 hover:border-primary/30 transition-all flex flex-col shadow-none group">
                <CardHeader className="pb-4">
                    <div className="flex items-start justify-between">
                        <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                            <Boxes className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex items-center gap-1.5">
                            <StatusBadge status={template.status} />
                            {!template.is_compliant && (
                                <Badge variant="outline" className="text-[10px] border-amber-600/50 text-amber-500 py-0 px-1.5 h-5 bg-amber-500/5">
                                    <ShieldAlert className="h-2.5 w-2.5 mr-1" />Non-Compliant
                                </Badge>
                            )}
                            {isStale && (
                                <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-400 py-0 px-1.5 h-5">
                                    <RefreshCw className="h-2.5 w-2.5 mr-1" />Rebuild recommended
                                </Badge>
                            )}
                        </div>
                    </div>
                    <div className="flex items-center justify-between mt-4">
                        <CardTitle className="text-foreground font-bold">{template.friendly_name}</CardTitle>
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Layers className="h-4 w-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="bg-secondary border-muted text-foreground">
                                <DropdownMenuLabel>Image Lifecycle</DropdownMenuLabel>
                                <DropdownMenuSeparator className="bg-muted" />
                                <DropdownMenuItem onClick={() => setIsBOMOpen(true)} className="gap-2">
                                    <Package className="h-4 w-4" /> View BOM
                                </DropdownMenuItem>
                                <DropdownMenuSeparator className="bg-muted" />
                                <DropdownMenuItem onClick={() => updateStatusMutation.mutate('ACTIVE')} className="text-emerald-500 gap-2">
                                    <CheckCircle2 className="h-4 w-4" /> Mark Active
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => updateStatusMutation.mutate('DEPRECATED')} className="text-amber-500 gap-2">
                                    <Clock className="h-4 w-4" /> Deprecate
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => updateStatusMutation.mutate('REVOKED')} className="text-red-500 gap-2">
                                    <ShieldAlert className="h-4 w-4" /> REVOKE
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                    <CardDescription className="text-muted-foreground text-[10px] font-mono mt-1">
                        {template.canonical_id}
                    </CardDescription>
                </CardHeader>
                <CardContent className="flex-1 pb-4">
                    <div className="text-[11px] text-muted-foreground truncate mb-3">
                        {template.last_built_image || 'Never built'}
                    </div>
                    {buildStatus === 'success' && (
                        <div className="flex items-center gap-2 text-[10px] text-green-500 font-bold uppercase tracking-wider animate-in fade-in">
                            <CheckCircle2 className="h-3 w-3" /> Build succeeded
                        </div>
                    )}
                    {buildStatus === 'failed' && (
                        <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-2 text-[10px] text-red-500 font-bold uppercase tracking-wider animate-in fade-in">
                                <AlertCircle className="h-3 w-3" /> Build failed
                            </div>
                            <Button 
                                variant="link" 
                                size="sm" 
                                className="h-auto p-0 text-[10px] text-muted-foreground hover:text-foreground justify-start"
                                onClick={() => setShowBuildDetails(true)}
                            >
                                View Logs
                            </Button>
                        </div>
                    )}
                    {buildStatus === 'idle' && template.last_built_at && (
                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-medium">
                            <Clock className="h-3 w-3" />
                            {new Date(template.last_built_at).toLocaleString()}
                        </div>
                    )}
                </CardContent>
                <CardFooter className="bg-white/[0.01] border-t border-muted/50 pt-4 gap-2">
                    <Button
                        onClick={() => buildMutation.mutate()}
                        disabled={buildStatus === 'building'}
                        className="flex-1 h-9 bg-primary hover:bg-primary/90 text-foreground font-bold rounded-lg transition-all"
                    >
                        {buildStatus === 'building' ? (
                            <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Building...</>
                        ) : (
                            <><Zap className="mr-2 h-3.5 w-3.5 fill-current" /> Build Image</>
                        )}
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9 text-muted-foreground/60 hover:text-red-400 hover:bg-red-500/10 rounded-lg"
                        onClick={() => setShowDeleteConfirm(true)}
                        disabled={deleteMutation.isPending}
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </CardFooter>
            </Card>
        </>
    );
};

const BlueprintItem = ({ blueprint, onEdit }: { blueprint: Blueprint; onEdit?: (blueprint: Blueprint) => void }) => {
    const queryClient = useQueryClient();
    const [jsonOpen, setJsonOpen] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

    const deleteMutation = useMutation({
        mutationFn: async () => {
            const res = await authenticatedFetch(`/api/blueprints/${blueprint.id}`, { method: 'DELETE' });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Delete failed');
            }
        },
        onSuccess: () => {
            toast.success(`Image Recipe ${blueprint.name} deleted`);
            queryClient.invalidateQueries({ queryKey: ['blueprints'] });
        },
        onError: (e: Error) => toast.error(`Delete failed: ${e.message}`),
    });

    return (
        <>
            <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Image Recipe?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete {blueprint.name}? If it is used by any template, deletion will fail.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => deleteMutation.mutate()}
                            className="bg-red-600 hover:bg-red-700 text-foreground"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <div className="group flex items-center justify-between p-4 bg-card border border-muted/50 rounded-xl hover:border-primary/20 transition-all">
                <div className="flex items-center gap-4">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                        blueprint.type === 'RUNTIME' ? 'bg-blue-500/10' : 'bg-green-500/10'
                    }`}>
                        {blueprint.type === 'RUNTIME' ?
                            <Cpu className={`h-5 w-5 ${blueprint.type === 'RUNTIME' ? 'text-blue-400' : 'text-green-400'}`} /> :
                            <Globe className="h-5 w-5 text-green-400" />
                        }
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h4 className="text-sm font-bold text-foreground">{blueprint.name}</h4>
                            <Badge variant="outline" className="text-[10px] h-4 px-1 border-muted text-muted-foreground">v{blueprint.version}</Badge>
                            {blueprint.type === 'RUNTIME' && blueprint.os_family && (
                                <Badge variant="outline" className={`text-[10px] h-4 px-1 ${blueprint.os_family === 'ALPINE' ? 'border-cyan-600 text-cyan-400' : 'border-amber-600 text-amber-400'}`}>
                                    {blueprint.os_family}
                                </Badge>
                            )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            {blueprint.type === 'RUNTIME'
                                ? `OS: ${blueprint.definition.base_os} | ${blueprint.definition.tools?.length || 0} tools`
                                : `${blueprint.definition.egress_rules?.length || 0} egress rules | Mode: ${blueprint.definition.policy}`
                            }
                        </p>
                    </div>
                </div>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    {onEdit && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg"
                            onClick={() => onEdit(blueprint)}
                            title="Edit blueprint"
                        >
                            <Pencil className="h-3.5 w-3.5" />
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="text-muted-foreground hover:text-foreground"
                        onClick={() => setJsonOpen(true)}
                    >
                        View JSON
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground/60 hover:text-red-400 hover:bg-red-500/10 rounded-lg"
                        onClick={() => setShowDeleteConfirm(true)}
                        disabled={deleteMutation.isPending}
                    >
                        <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                </div>
            </div>

            <Dialog open={jsonOpen} onOpenChange={setJsonOpen}>
                <DialogContent className="bg-secondary border-muted max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="text-foreground">{blueprint.name} — Definition</DialogTitle>
                    </DialogHeader>
                    <pre className="text-xs text-green-400 font-mono bg-background rounded-lg p-4 overflow-auto max-h-[60vh] whitespace-pre-wrap">
                        {JSON.stringify(blueprint.definition, null, 2)}
                    </pre>
                </DialogContent>
            </Dialog>
        </>
    );
};

const BlueprintEmptyState = ({ type }: { type: 'RUNTIME' | 'NETWORK' }) => (
    <div className="py-20 text-center rounded-2xl border border-dashed border-muted bg-secondary/20">
        {type === 'RUNTIME' ? (
            <Cpu className="h-12 w-12 text-muted mx-auto mb-4" />
        ) : (
            <Globe className="h-12 w-12 text-muted mx-auto mb-4" />
        )}
        <h3 className="text-muted-foreground font-medium">No {type.toLowerCase()} image recipes found</h3>
        <p className="text-muted-foreground/60 text-sm mt-1">Create a {type.toLowerCase()} image recipe to get started.</p>
    </div>
);

const Templates = () => {
    const queryClient = useQueryClient();
    const [isTemplateOpen, setIsTemplateOpen] = useState(false);
    const [isWizardOpen, setIsWizardOpen] = useState(false);
    const [editingBlueprint, setEditingBlueprint] = useState<Blueprint | null>(null);
    const [showAddTool, setShowAddTool] = useState(false);

    const handleEditBlueprint = async (blueprint: Blueprint) => {
        try {
            const res = await authenticatedFetch(`/api/blueprints/${blueprint.id}`);
            if (!res.ok) throw new Error('Failed to fetch blueprint');
            const full = await res.json();
            setEditingBlueprint(full);
            setIsWizardOpen(true);
        } catch (e: any) {
            toast.error(e.message || 'Failed to load blueprint for editing');
        }
    };
    const [newTool, setNewTool] = useState({
        tool_id: '', base_os_family: 'DEBIAN' as 'DEBIAN' | 'ALPINE',
        validation_cmd: '', injection_recipe: '', runtime_dependencies: [] as string[],
        is_active: true
    });
    const [newDepInput, setNewDepInput] = useState('');
    const [editingTool, setEditingTool] = useState<ToolMatrix | null>(null);
    const [toolEditOpen, setToolEditOpen] = useState(false);
    const [toolEditForm, setToolEditForm] = useState({
        tool_id: '', base_os_family: 'DEBIAN' as string,
        validation_cmd: '', injection_recipe: '', runtime_dependencies: [] as string[],
    });
    const [editDepInput, setEditDepInput] = useState('');

    // Approved OS state
    const [showAddOS, setShowAddOS] = useState(false);
    const [newOS, setNewOS] = useState({ name: '', image_uri: '', os_family: 'DEBIAN' });
    const [editingOSId, setEditingOSId] = useState<string | null>(null);
    const [osEditForm, setOsEditForm] = useState({ name: '', image_uri: '', os_family: 'DEBIAN' });

    const { data: templates = [], isLoading: loadingTemplates } = useQuery<Template[]>({
        queryKey: ['templates'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/templates');
            return await res.json();
        }
    });

    const { data: blueprints = [], isLoading: loadingBlueprints } = useQuery<Blueprint[]>({
        queryKey: ['blueprints'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/blueprints');
            return await res.json();
        }
    });

    const { data: baseImageData } = useQuery<{ base_node_image_updated_at: string | null }>({
        queryKey: ['base-image-updated'],
        queryFn: async () => {
            const res = await authenticatedFetch('/admin/base-image-updated');
            return await res.json();
        }
    });

    const markBaseUpdatedMutation = useMutation({
        mutationFn: async () => {
            const res = await authenticatedFetch('/admin/mark-base-updated', { method: 'POST' });
            if (!res.ok) throw new Error('Failed');
        },
        onSuccess: () => {
            toast.success('Base image marked as updated');
            queryClient.invalidateQueries({ queryKey: ['base-image-updated'] });
        },
        onError: () => toast.error('Failed to mark base image updated'),
    });

    // Tools (capability matrix) — include_inactive=true for admin view
    const { data: tools = [], refetch: refetchTools } = useQuery<ToolMatrix[]>({
        queryKey: ['capability-matrix-admin'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/capability-matrix?include_inactive=true');
            return await res.json();
        }
    });

    // Add tool mutation
    const addToolMutation = useMutation({
        mutationFn: async (entry: Omit<ToolMatrix, 'id'>) => {
            const res = await authenticatedFetch('/api/capability-matrix', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...entry,
                    runtime_dependencies: entry.runtime_dependencies,
                    is_active: true
                })
            });
            if (!res.ok) throw new Error('Failed to create tool entry');
            return res.json();
        },
        onSuccess: () => { refetchTools(); toast.success('Tool entry created'); }
    });

    // Soft-delete tool mutation
    const deleteToolMutation = useMutation({
        mutationFn: async (id: number) => {
            const res = await authenticatedFetch(`/api/capability-matrix/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete tool entry');
            return res.json();
        },
        onSuccess: (data) => {
            refetchTools();
            const refs = data.referencing_blueprints?.length || 0;
            if (refs > 0) {
                toast.warning(`Tool deactivated. Referenced by ${refs} blueprint(s) — they can still build.`);
            } else {
                toast.success('Tool deactivated');
            }
        }
    });

    // Edit tool mutation
    const editToolMutation = useMutation({
        mutationFn: async ({ id, data }: { id: number; data: Record<string, unknown> }) => {
            const res = await authenticatedFetch(`/api/capability-matrix/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to update tool');
            }
            return res.json();
        },
        onSuccess: () => {
            refetchTools();
            toast.success('Tool updated');
            setToolEditOpen(false);
            setEditingTool(null);
        },
        onError: (e: Error) => toast.error(`Update failed: ${e.message}`),
    });

    const openToolEdit = (tool: ToolMatrix) => {
        setEditingTool(tool);
        setToolEditForm({
            tool_id: tool.tool_id,
            base_os_family: tool.base_os_family,
            validation_cmd: tool.validation_cmd,
            injection_recipe: tool.injection_recipe,
            runtime_dependencies: [...(tool.runtime_dependencies || [])],
        });
        setEditDepInput('');
        setToolEditOpen(true);
    };

    const handleToolEditSave = () => {
        if (!editingTool) return;
        const data: Record<string, unknown> = {};
        if (toolEditForm.tool_id !== editingTool.tool_id) data.tool_id = toolEditForm.tool_id;
        if (toolEditForm.base_os_family !== editingTool.base_os_family) data.base_os_family = toolEditForm.base_os_family;
        if (toolEditForm.validation_cmd !== editingTool.validation_cmd) data.validation_cmd = toolEditForm.validation_cmd;
        if (toolEditForm.injection_recipe !== editingTool.injection_recipe) data.injection_recipe = toolEditForm.injection_recipe;
        if (JSON.stringify(toolEditForm.runtime_dependencies) !== JSON.stringify(editingTool.runtime_dependencies || []))
            data.runtime_dependencies = toolEditForm.runtime_dependencies;
        if (Object.keys(data).length === 0) {
            toast.info('No changes to save');
            setToolEditOpen(false);
            return;
        }
        editToolMutation.mutate({ id: editingTool.id, data });
    };

    // Approved OS queries and mutations
    const { data: approvedOSList = [] } = useQuery<ApprovedOS[]>({
        queryKey: ['approved-os'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/approved-os');
            return await res.json();
        }
    });

    const addOSMutation = useMutation({
        mutationFn: async (entry: { name: string; image_uri: string; os_family: string }) => {
            const res = await authenticatedFetch('/api/approved-os', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(entry)
            });
            if (!res.ok) {
                const err = await res.json();
                const detail = Array.isArray(err.detail) ? err.detail.map((d: { msg: string }) => d.msg).join(', ') : err.detail;
                throw new Error(detail || 'Failed to create OS entry');
            }
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['approved-os'] });
            toast.success('Approved OS entry created');
            setShowAddOS(false);
            setNewOS({ name: '', image_uri: '', os_family: 'DEBIAN' });
        },
        onError: (e: Error) => toast.error(`Create failed: ${e.message}`),
    });

    const editOSMutation = useMutation({
        mutationFn: async ({ id, data }: { id: string; data: Record<string, unknown> }) => {
            const res = await authenticatedFetch(`/api/approved-os/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to update OS entry');
            }
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['approved-os'] });
            toast.success('OS entry updated');
            setEditingOSId(null);
        },
        onError: (e: Error) => toast.error(`Update failed: ${e.message}`),
    });

    const deleteOSMutation = useMutation({
        mutationFn: async (id: string) => {
            const res = await authenticatedFetch(`/api/approved-os/${id}`, { method: 'DELETE' });
            if (res.status === 409) {
                const err = await res.json();
                throw new Error(err.detail || 'Cannot delete: referenced by a blueprint');
            }
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to delete OS entry');
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['approved-os'] });
            toast.success('OS entry removed');
        },
        onError: (e: Error) => toast.error(e.message),
    });

    const startOSEdit = (os: ApprovedOS) => {
        setEditingOSId(os.id);
        setOsEditForm({ name: os.name, image_uri: os.image_uri, os_family: os.os_family });
    };

    const handleOSEditSave = (os: ApprovedOS) => {
        const data: Record<string, unknown> = {};
        if (osEditForm.name !== os.name) data.name = osEditForm.name;
        if (osEditForm.image_uri !== os.image_uri) data.image_uri = osEditForm.image_uri;
        if (osEditForm.os_family !== os.os_family) data.os_family = osEditForm.os_family;
        if (Object.keys(data).length === 0) {
            toast.info('No changes to save');
            setEditingOSId(null);
            return;
        }
        editOSMutation.mutate({ id: os.id, data });
    };

    const baseUpdatedAt = baseImageData?.base_node_image_updated_at ?? null;
    const runtimeBlueprints = blueprints.filter((b: Blueprint) => b.type === 'RUNTIME');
    const networkBlueprints = blueprints.filter((b: Blueprint) => b.type === 'NETWORK');
    const isLoading = loadingTemplates || loadingBlueprints;

    return (
        <div className="space-y-8 animate-in fade-in duration-500 max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-foreground">Foundry</h1>
                    <p className="text-sm text-muted-foreground mt-1">Compose and build immutable agent environments.</p>
                </div>
                <Button
                    variant="outline"
                    className="bg-secondary border-muted text-muted-foreground hover:text-foreground h-10 px-4 rounded-xl"
                    onClick={() => markBaseUpdatedMutation.mutate()}
                    disabled={markBaseUpdatedMutation.isPending}
                    title="Mark base node image as updated — flags older templates for rebuild"
                >
                    <RefreshCw className="mr-2 h-4 w-4" /> Mark Base Updated
                </Button>
            </div>

            {isLoading ? (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-48 rounded-2xl bg-secondary/50 border border-muted animate-pulse" />
                    ))}
                </div>
            ) : (
                <Tabs defaultValue="templates" className="w-full">
                    <TabsList>
                        <TabsTrigger value="templates">Node Images ({templates.length})</TabsTrigger>
                        <TabsTrigger value="runtime">Runtime Image Recipes ({runtimeBlueprints.length})</TabsTrigger>
                        <TabsTrigger value="network">Network Image Recipes ({networkBlueprints.length})</TabsTrigger>
                        <TabsTrigger value="tools">
                            <Wrench className="mr-1 h-3.5 w-3.5" />
                            Tools ({tools.length})
                        </TabsTrigger>
                        <TabsTrigger value="approved-os">
                            <Monitor className="mr-1 h-3.5 w-3.5" />
                            Approved OS ({approvedOSList.length})
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="templates">
                        <div className="flex justify-end mb-4">
                            <Button
                                className="bg-primary hover:bg-primary/90 text-foreground h-10 px-4 rounded-xl font-bold shadow-lg shadow-primary/10"
                                onClick={() => setIsTemplateOpen(true)}
                            >
                                <Plus className="mr-2 h-4 w-4" /> New Node Image
                            </Button>
                        </div>
                        {templates.length > 0 ? (
                            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                                {templates.map(t => <TemplateCard key={t.id} template={t} baseUpdatedAt={baseUpdatedAt} />)}
                            </div>
                        ) : (
                            <div className="py-20 text-center rounded-2xl border border-dashed border-muted bg-secondary/20">
                                <Boxes className="h-12 w-12 text-muted mx-auto mb-4" />
                                <h3 className="text-muted-foreground font-medium">No node images found</h3>
                                <p className="text-muted-foreground/60 text-sm mt-1">Compose your first node image using image recipes.</p>
                            </div>
                        )}
                    </TabsContent>

                    <TabsContent value="runtime">
                        <div className="flex justify-end mb-4">
                            <Button
                                variant="outline"
                                className="bg-secondary border-muted text-foreground h-10 px-4 rounded-xl"
                                onClick={() => setIsWizardOpen(true)}
                            >
                                <Plus className="mr-2 h-4 w-4" /> New Runtime Image Recipe
                            </Button>
                        </div>
                        {runtimeBlueprints.length > 0 ? (
                            <div className="space-y-3">
                                {runtimeBlueprints.map(b => <BlueprintItem key={b.id} blueprint={b} onEdit={handleEditBlueprint} />)}
                            </div>
                        ) : (
                            <BlueprintEmptyState type="RUNTIME" />
                        )}
                    </TabsContent>

                    <TabsContent value="network">
                        <div className="flex justify-end mb-4">
                            <Button
                                variant="outline"
                                className="bg-secondary border-muted text-foreground h-10 px-4 rounded-xl"
                                onClick={() => setIsWizardOpen(true)}
                            >
                                <Plus className="mr-2 h-4 w-4" /> New Network Image Recipe
                            </Button>
                        </div>
                        {networkBlueprints.length > 0 ? (
                            <div className="space-y-3">
                                {networkBlueprints.map(b => <BlueprintItem key={b.id} blueprint={b} onEdit={handleEditBlueprint} />)}
                            </div>
                        ) : (
                            <BlueprintEmptyState type="NETWORK" />
                        )}
                    </TabsContent>

                    <TabsContent value="tools">
                        <div className="space-y-4">
                            <div className="flex justify-end">
                                <Button
                                    variant="outline"
                                    className="bg-secondary border-muted text-foreground h-10 px-4 rounded-xl"
                                    onClick={() => setShowAddTool(true)}
                                >
                                    <Plus className="mr-2 h-4 w-4" /> Add Tool Entry
                                </Button>
                            </div>

                            {/* Add tool dialog */}
                            <Dialog open={showAddTool} onOpenChange={setShowAddTool}>
                                <DialogContent className="max-w-lg bg-background border-muted text-foreground">
                                    <DialogHeader>
                                        <DialogTitle>Add Tool</DialogTitle>
                                    </DialogHeader>
                                    <div className="grid gap-4 py-2">
                                        <div className="grid gap-1.5">
                                            <Label>Tool ID</Label>
                                            <Input className="bg-secondary border-muted" placeholder="e.g. python-3.11"
                                                value={newTool.tool_id} onChange={e => setNewTool({...newTool, tool_id: e.target.value})} />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>OS Family</Label>
                                            <select className="bg-secondary border border-muted text-foreground rounded-md px-3 py-2 text-sm"
                                                value={newTool.base_os_family}
                                                onChange={e => setNewTool({...newTool, base_os_family: e.target.value as 'DEBIAN' | 'ALPINE'})}>
                                                <option value="DEBIAN">DEBIAN</option>
                                                <option value="ALPINE">ALPINE</option>
                                            </select>
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>Validation Command</Label>
                                            <Input className="bg-secondary border-muted" placeholder="e.g. python --version"
                                                value={newTool.validation_cmd} onChange={e => setNewTool({...newTool, validation_cmd: e.target.value})} />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>Injection Recipe (Dockerfile snippet)</Label>
                                            <textarea className="bg-secondary border border-muted text-foreground rounded-md px-3 py-2 text-sm font-mono h-20 resize-none"
                                                value={newTool.injection_recipe}
                                                onChange={e => setNewTool({...newTool, injection_recipe: e.target.value})}
                                                placeholder="RUN apt-get install -y python3" />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>Runtime Dependencies (tool_ids)</Label>
                                            <div className="flex gap-2">
                                                <Input className="bg-secondary border-muted" placeholder="e.g. python-3.11"
                                                    value={newDepInput} onChange={e => setNewDepInput(e.target.value)}
                                                    onKeyDown={e => {
                                                        if (e.key === 'Enter' && newDepInput) {
                                                            setNewTool({...newTool, runtime_dependencies: [...newTool.runtime_dependencies, newDepInput]});
                                                            setNewDepInput('');
                                                        }
                                                    }} />
                                                <Button type="button" size="icon" onClick={() => {
                                                    if (newDepInput) {
                                                        setNewTool({...newTool, runtime_dependencies: [...newTool.runtime_dependencies, newDepInput]});
                                                        setNewDepInput('');
                                                    }
                                                }}><Plus className="h-4 w-4" /></Button>
                                            </div>
                                            <div className="flex flex-wrap gap-1 mt-1">
                                                {newTool.runtime_dependencies.map(dep => (
                                                    <Badge key={dep} variant="outline" className="cursor-pointer text-xs"
                                                        onClick={() => setNewTool({...newTool, runtime_dependencies: newTool.runtime_dependencies.filter(d => d !== dep)})}>
                                                        {dep} <X className="h-3 w-3 ml-1" />
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                    <DialogFooter>
                                        <Button variant="outline" onClick={() => setShowAddTool(false)}>Cancel</Button>
                                        <Button onClick={() => {
                                            addToolMutation.mutate(newTool);
                                            setShowAddTool(false);
                                            setNewTool({ tool_id: '', base_os_family: 'DEBIAN', validation_cmd: '', injection_recipe: '', runtime_dependencies: [], is_active: true });
                                        }} disabled={!newTool.tool_id || !newTool.validation_cmd}>
                                            Add Entry
                                        </Button>
                                    </DialogFooter>
                                </DialogContent>
                            </Dialog>

                            {/* Edit tool dialog */}
                            <Dialog open={toolEditOpen} onOpenChange={(open) => { setToolEditOpen(open); if (!open) setEditingTool(null); }}>
                                <DialogContent className="max-w-lg bg-background border-muted text-foreground">
                                    <DialogHeader>
                                        <DialogTitle>Edit Tool</DialogTitle>
                                        <DialogDescription className="text-muted-foreground">
                                            Modify tool entry properties. Only changed fields will be sent.
                                        </DialogDescription>
                                    </DialogHeader>
                                    <div className="grid gap-4 py-2">
                                        <div className="grid gap-1.5">
                                            <Label>Tool ID</Label>
                                            <Input className="bg-secondary border-muted"
                                                value={toolEditForm.tool_id}
                                                onChange={e => setToolEditForm({...toolEditForm, tool_id: e.target.value})} />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>OS Family</Label>
                                            <select className="bg-secondary border border-muted text-foreground rounded-md px-3 py-2 text-sm"
                                                value={toolEditForm.base_os_family}
                                                onChange={e => setToolEditForm({...toolEditForm, base_os_family: e.target.value})}>
                                                <option value="DEBIAN">DEBIAN</option>
                                                <option value="ALPINE">ALPINE</option>
                                            </select>
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>Validation Command</Label>
                                            <Input className="bg-secondary border-muted"
                                                value={toolEditForm.validation_cmd}
                                                onChange={e => setToolEditForm({...toolEditForm, validation_cmd: e.target.value})} />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>Injection Recipe (Dockerfile snippet)</Label>
                                            <Textarea className="bg-secondary border-muted font-mono h-20 resize-none"
                                                value={toolEditForm.injection_recipe}
                                                onChange={e => setToolEditForm({...toolEditForm, injection_recipe: e.target.value})} />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>Runtime Dependencies (tool_ids)</Label>
                                            <div className="flex gap-2">
                                                <Input className="bg-secondary border-muted" placeholder="e.g. python-3.11"
                                                    value={editDepInput} onChange={e => setEditDepInput(e.target.value)}
                                                    onKeyDown={e => {
                                                        if (e.key === 'Enter' && editDepInput) {
                                                            setToolEditForm({...toolEditForm, runtime_dependencies: [...toolEditForm.runtime_dependencies, editDepInput]});
                                                            setEditDepInput('');
                                                        }
                                                    }} />
                                                <Button type="button" size="icon" onClick={() => {
                                                    if (editDepInput) {
                                                        setToolEditForm({...toolEditForm, runtime_dependencies: [...toolEditForm.runtime_dependencies, editDepInput]});
                                                        setEditDepInput('');
                                                    }
                                                }}><Plus className="h-4 w-4" /></Button>
                                            </div>
                                            <div className="flex flex-wrap gap-1 mt-1">
                                                {toolEditForm.runtime_dependencies.map(dep => (
                                                    <Badge key={dep} variant="outline" className="cursor-pointer text-xs"
                                                        onClick={() => setToolEditForm({...toolEditForm, runtime_dependencies: toolEditForm.runtime_dependencies.filter(d => d !== dep)})}>
                                                        {dep} <X className="h-3 w-3 ml-1" />
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                    <DialogFooter>
                                        <Button variant="outline" onClick={() => { setToolEditOpen(false); setEditingTool(null); }}>Cancel</Button>
                                        <Button onClick={handleToolEditSave} disabled={editToolMutation.isPending || !toolEditForm.tool_id || !toolEditForm.validation_cmd}>
                                            {editToolMutation.isPending ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</> : 'Save Changes'}
                                        </Button>
                                    </DialogFooter>
                                </DialogContent>
                            </Dialog>

                            {/* Tools table */}
                            <div className="rounded-xl border border-muted overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead className="bg-secondary text-muted-foreground uppercase text-xs">
                                        <tr>
                                            <th className="text-left px-4 py-3">Tool ID</th>
                                            <th className="text-left px-4 py-3">OS Family</th>
                                            <th className="text-left px-4 py-3">Validation Cmd</th>
                                            <th className="text-left px-4 py-3">Runtime Deps</th>
                                            <th className="text-left px-4 py-3">Status</th>
                                            <th className="text-left px-4 py-3">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-muted">
                                        {tools.map(tool => (
                                            <tr key={tool.id} className={`${!tool.is_active ? 'opacity-50' : ''} hover:bg-secondary/50 transition-colors`}>
                                                <td className="px-4 py-3 font-mono text-foreground">{tool.tool_id}</td>
                                                <td className="px-4 py-3">
                                                    <Badge variant="outline" className={tool.base_os_family === 'ALPINE' ? 'border-cyan-600 text-cyan-400' : 'border-amber-600 text-amber-400'}>
                                                        {tool.base_os_family}
                                                    </Badge>
                                                </td>
                                                <td className="px-4 py-3 font-mono text-muted-foreground text-xs">{tool.validation_cmd}</td>
                                                <td className="px-4 py-3">
                                                    <div className="flex flex-wrap gap-1">
                                                        {(tool.runtime_dependencies || []).map(dep => (
                                                            <Badge key={dep} variant="secondary" className="text-xs">{dep}</Badge>
                                                        ))}
                                                        {(!tool.runtime_dependencies || tool.runtime_dependencies.length === 0) && (
                                                            <span className="text-muted-foreground/60 text-xs">none</span>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <Badge variant={tool.is_active ? 'default' : 'secondary'}>
                                                        {tool.is_active ? 'Active' : 'Inactive'}
                                                    </Badge>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <div className="flex gap-1">
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-8 w-8 text-muted-foreground hover:text-foreground"
                                                            onClick={() => openToolEdit(tool)}
                                                        >
                                                            <Pencil className="h-4 w-4" />
                                                        </Button>
                                                        {tool.is_active && (
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="h-8 w-8 text-muted-foreground hover:text-red-400"
                                                                onClick={() => {
                                                                    if (confirm(`Deactivate tool "${tool.tool_id}"? It will be hidden from new blueprints but existing blueprints are unaffected.`)) {
                                                                        deleteToolMutation.mutate(tool.id);
                                                                    }
                                                                }}
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                        {tools.length === 0 && (
                                            <tr>
                                                <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No tool entries found</td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </TabsContent>

                    <TabsContent value="approved-os">
                        <div className="space-y-4">
                            <div className="flex justify-end">
                                <Button
                                    variant="outline"
                                    className="bg-secondary border-muted text-foreground h-10 px-4 rounded-xl"
                                    onClick={() => setShowAddOS(true)}
                                >
                                    <Plus className="mr-2 h-4 w-4" /> Add Approved OS
                                </Button>
                            </div>

                            {/* Add OS dialog */}
                            <Dialog open={showAddOS} onOpenChange={setShowAddOS}>
                                <DialogContent className="max-w-lg bg-background border-muted text-foreground">
                                    <DialogHeader>
                                        <DialogTitle>Add Approved OS</DialogTitle>
                                        <DialogDescription className="text-muted-foreground">
                                            Add a new base OS image to the approved list.
                                        </DialogDescription>
                                    </DialogHeader>
                                    <div className="grid gap-4 py-2">
                                        <div className="grid gap-1.5">
                                            <Label>Name</Label>
                                            <Input className="bg-secondary border-muted" placeholder="e.g. Ubuntu 24.04"
                                                value={newOS.name} onChange={e => setNewOS({...newOS, name: e.target.value})} />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>Image URI</Label>
                                            <Input className="bg-secondary border-muted" placeholder="e.g. docker.io/library/ubuntu:24.04"
                                                value={newOS.image_uri} onChange={e => setNewOS({...newOS, image_uri: e.target.value})} />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <Label>OS Family</Label>
                                            <select className="bg-secondary border border-muted text-foreground rounded-md px-3 py-2 text-sm"
                                                value={newOS.os_family}
                                                onChange={e => setNewOS({...newOS, os_family: e.target.value})}>
                                                <option value="DEBIAN">DEBIAN</option>
                                                <option value="ALPINE">ALPINE</option>
                                            </select>
                                        </div>
                                    </div>
                                    <DialogFooter>
                                        <Button variant="outline" onClick={() => setShowAddOS(false)}>Cancel</Button>
                                        <Button onClick={() => addOSMutation.mutate(newOS)}
                                            disabled={!newOS.name || !newOS.image_uri || addOSMutation.isPending}>
                                            {addOSMutation.isPending ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Adding...</> : 'Add OS Entry'}
                                        </Button>
                                    </DialogFooter>
                                </DialogContent>
                            </Dialog>

                            {/* Approved OS table */}
                            <div className="rounded-xl border border-muted overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead className="bg-secondary text-muted-foreground uppercase text-xs">
                                        <tr>
                                            <th className="text-left px-4 py-3">Name</th>
                                            <th className="text-left px-4 py-3">Image URI</th>
                                            <th className="text-left px-4 py-3">OS Family</th>
                                            <th className="text-left px-4 py-3">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-muted">
                                        {approvedOSList.map(os => (
                                            <tr key={os.id} className="hover:bg-secondary/50 transition-colors">
                                                {editingOSId === os.id ? (
                                                    <>
                                                        <td className="px-4 py-3">
                                                            <Input className="bg-secondary border-muted h-8 text-sm"
                                                                value={osEditForm.name}
                                                                onChange={e => setOsEditForm({...osEditForm, name: e.target.value})} />
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <Input className="bg-secondary border-muted h-8 text-sm"
                                                                value={osEditForm.image_uri}
                                                                onChange={e => setOsEditForm({...osEditForm, image_uri: e.target.value})} />
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <select className="bg-secondary border border-muted text-foreground rounded-md px-2 py-1 text-sm"
                                                                value={osEditForm.os_family}
                                                                onChange={e => setOsEditForm({...osEditForm, os_family: e.target.value})}>
                                                                <option value="DEBIAN">DEBIAN</option>
                                                                <option value="ALPINE">ALPINE</option>
                                                            </select>
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <div className="flex gap-1">
                                                                <Button variant="ghost" size="icon" className="h-8 w-8 text-emerald-500 hover:text-emerald-400"
                                                                    onClick={() => handleOSEditSave(os)}
                                                                    disabled={editOSMutation.isPending}>
                                                                    <Check className="h-4 w-4" />
                                                                </Button>
                                                                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground"
                                                                    onClick={() => setEditingOSId(null)}>
                                                                    <X className="h-4 w-4" />
                                                                </Button>
                                                            </div>
                                                        </td>
                                                    </>
                                                ) : (
                                                    <>
                                                        <td className="px-4 py-3 text-foreground font-medium">{os.name}</td>
                                                        <td className="px-4 py-3 font-mono text-muted-foreground text-xs">{os.image_uri}</td>
                                                        <td className="px-4 py-3">
                                                            <Badge variant="outline" className={os.os_family === 'ALPINE' ? 'border-cyan-600 text-cyan-400' : 'border-amber-600 text-amber-400'}>
                                                                {os.os_family}
                                                            </Badge>
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <div className="flex gap-1">
                                                                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground"
                                                                    onClick={() => startOSEdit(os)}>
                                                                    <Pencil className="h-4 w-4" />
                                                                </Button>
                                                                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-red-400"
                                                                    onClick={() => deleteOSMutation.mutate(os.id)}
                                                                    disabled={deleteOSMutation.isPending}>
                                                                    <Trash2 className="h-4 w-4" />
                                                                </Button>
                                                            </div>
                                                        </td>
                                                    </>
                                                )}
                                            </tr>
                                        ))}
                                        {approvedOSList.length === 0 && (
                                            <tr>
                                                <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                                                    No approved OS entries found. Add one to get started.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </TabsContent>
                </Tabs>
            )}

            <BlueprintWizard
                open={isWizardOpen}
                onOpenChange={(open) => {
                    setIsWizardOpen(open);
                    if (!open) setEditingBlueprint(null);
                }}
                editBlueprint={editingBlueprint}
            />
            <CreateTemplateDialog open={isTemplateOpen} onOpenChange={setIsTemplateOpen} />

        </div>
    );
};

const TemplatesWithFeatureCheck = () => {
    const features = useFeatures();
    if (!features.foundry) {
        return <UpgradePlaceholder feature="Foundry" description="Build and manage custom node images with Image Recipe templates, tool injection, and BOM tracking." />;
    }
    return <Templates />;
};

export default TemplatesWithFeatureCheck;
