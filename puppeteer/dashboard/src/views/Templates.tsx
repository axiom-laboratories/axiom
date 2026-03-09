import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Boxes, CheckCircle2, Clock, AlertCircle, Loader2, Plus, Cpu, Globe, Zap, Trash2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
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
import { authenticatedFetch } from '../auth';
import { CreateBlueprintDialog } from '../components/CreateBlueprintDialog';
import { CreateTemplateDialog } from '../components/CreateTemplateDialog';

interface Template {
    id: string;
    friendly_name: string;
    canonical_id: string;
    last_built_image?: string;
    last_built_at?: string;
    runtime_blueprint_id: string;
    network_blueprint_id: string;
}

interface Blueprint {
    id: string;
    type: 'RUNTIME' | 'NETWORK';
    name: string;
    definition: any;
    version: number;
    created_at: string;
}

const TemplateCard = ({ template, baseUpdatedAt }: { template: Template; baseUpdatedAt: string | null }) => {
    const queryClient = useQueryClient();
    const [buildStatus, setBuildStatus] = useState<'idle' | 'building' | 'success' | 'failed'>('idle');
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [showBuildDetails, setShowBuildDetails] = useState(false);

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
            toast.success(`Template ${template.friendly_name} deleted`);
            queryClient.invalidateQueries({ queryKey: ['templates'] });
        },
        onError: (e: Error) => toast.error(`Delete failed: ${e.message}`),
    });

    return (
        <>
            <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Template?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete {template.friendly_name}? This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => deleteMutation.mutate()}
                            className="bg-red-600 hover:bg-red-700 text-white"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <Dialog open={showBuildDetails} onOpenChange={setShowBuildDetails}>
                <DialogContent className="bg-zinc-950 border-zinc-800 text-white max-w-3xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <AlertCircle className="h-5 w-5 text-red-500" />
                            Build Failure Details
                        </DialogTitle>
                        <DialogDescription className="text-zinc-500">
                            Last 250 characters of the build process output.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="mt-4 p-4 rounded-lg bg-black border border-zinc-800 font-mono text-xs text-red-400/90 whitespace-pre-wrap break-all overflow-auto max-h-[40vh]">
                        {template.status || 'No output captured.'}
                    </div>
                    <DialogFooter>
                        <Button onClick={() => setShowBuildDetails(false)}>Close</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Card className="bg-zinc-925 border-zinc-800/50 hover:border-primary/30 transition-all flex flex-col shadow-none">
                <CardHeader className="pb-4">
                    <div className="flex items-start justify-between">
                        <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                            <Boxes className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex items-center gap-1.5">
                            {isStale && (
                                <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-400 py-0 px-1.5 h-5">
                                    <RefreshCw className="h-2.5 w-2.5 mr-1" />Rebuild recommended
                                </Badge>
                            )}
                            <Badge variant="outline" className="font-mono text-[10px] border-zinc-800 text-zinc-500 py-0 px-1.5 h-5">
                                {template.canonical_id}
                            </Badge>
                        </div>
                    </div>
                    <CardTitle className="mt-4 text-white font-bold">{template.friendly_name}</CardTitle>
                    <CardDescription className="text-zinc-500 text-xs truncate">
                        {template.last_built_image
                            ? `Image: ${template.last_built_image}`
                            : 'Never built'}
                    </CardDescription>
                </CardHeader>
                <CardContent className="flex-1 pb-4">
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
                                className="h-auto p-0 text-[10px] text-zinc-500 hover:text-zinc-300 justify-start"
                                onClick={() => setShowBuildDetails(true)}
                            >
                                View Details
                            </Button>
                        </div>
                    )}                    {buildStatus === 'idle' && template.last_built_at && (
                        <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-medium">
                            <Clock className="h-3 w-3" />
                            {new Date(template.last_built_at).toLocaleString()}
                        </div>
                    )}
                </CardContent>
                <CardFooter className="bg-white/[0.01] border-t border-zinc-800/50 pt-4 gap-2">
                    <Button
                        onClick={() => buildMutation.mutate()}
                        disabled={buildStatus === 'building'}
                        className="flex-1 h-9 bg-primary hover:bg-primary/90 text-white font-bold rounded-lg transition-all"
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
                        className="h-9 w-9 text-zinc-600 hover:text-red-400 hover:bg-red-500/10 rounded-lg"
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

const BlueprintItem = ({ blueprint }: { blueprint: Blueprint }) => {
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
            toast.success(`Blueprint ${blueprint.name} deleted`);
            queryClient.invalidateQueries({ queryKey: ['blueprints'] });
        },
        onError: (e: Error) => toast.error(`Delete failed: ${e.message}`),
    });

    return (
        <>
            <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Blueprint?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete {blueprint.name}? If it is used by any template, deletion will fail.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => deleteMutation.mutate()}
                            className="bg-red-600 hover:bg-red-700 text-white"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <div className="group flex items-center justify-between p-4 bg-zinc-925 border border-zinc-800/50 rounded-xl hover:border-primary/20 transition-all">
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
                            <h4 className="text-sm font-bold text-white">{blueprint.name}</h4>
                            <Badge variant="outline" className="text-[10px] h-4 px-1 border-zinc-800 text-zinc-500">v{blueprint.version}</Badge>
                        </div>
                        <p className="text-xs text-zinc-500 mt-0.5">
                            {blueprint.type === 'RUNTIME'
                                ? `OS: ${blueprint.definition.base_os} | ${blueprint.definition.tools?.length || 0} tools`
                                : `${blueprint.definition.egress_rules?.length || 0} egress rules | Mode: ${blueprint.definition.policy}`
                            }
                        </p>
                    </div>
                </div>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="text-zinc-500 hover:text-white"
                        onClick={() => setJsonOpen(true)}
                    >
                        View JSON
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-zinc-600 hover:text-red-400 hover:bg-red-500/10 rounded-lg"
                        onClick={() => setShowDeleteConfirm(true)}
                        disabled={deleteMutation.isPending}
                    >
                        <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                </div>
            </div>

            <Dialog open={jsonOpen} onOpenChange={setJsonOpen}>
                <DialogContent className="bg-zinc-900 border-zinc-800 max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="text-white">{blueprint.name} — Definition</DialogTitle>
                    </DialogHeader>
                    <pre className="text-xs text-green-400 font-mono bg-zinc-950 rounded-lg p-4 overflow-auto max-h-[60vh] whitespace-pre-wrap">
                        {JSON.stringify(blueprint.definition, null, 2)}
                    </pre>
                </DialogContent>
            </Dialog>
        </>
    );
};

const BlueprintEmptyState = ({ type }: { type: 'RUNTIME' | 'NETWORK' }) => (
    <div className="py-20 text-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20">
        {type === 'RUNTIME' ? (
            <Cpu className="h-12 w-12 text-zinc-800 mx-auto mb-4" />
        ) : (
            <Globe className="h-12 w-12 text-zinc-800 mx-auto mb-4" />
        )}
        <h3 className="text-zinc-400 font-medium">No {type.toLowerCase()} blueprints found</h3>
        <p className="text-zinc-600 text-sm mt-1">Create a {type.toLowerCase()} blueprint to get started.</p>
    </div>
);

const Templates = () => {
    const queryClient = useQueryClient();
    const [isTemplateOpen, setIsTemplateOpen] = useState(false);
    const [blueprintDialogType, setBlueprintDialogType] = useState<'RUNTIME' | 'NETWORK' | undefined>();
    const [blueprintDialogOpen, setBlueprintDialogOpen] = useState(false);

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

    const baseUpdatedAt = baseImageData?.base_node_image_updated_at ?? null;
    const runtimeBlueprints = blueprints.filter((b: Blueprint) => b.type === 'RUNTIME');
    const networkBlueprints = blueprints.filter((b: Blueprint) => b.type === 'NETWORK');
    const isLoading = loadingTemplates || loadingBlueprints;

    return (
        <div className="space-y-8 animate-in fade-in duration-500 max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-white">Foundry</h1>
                    <p className="text-sm text-zinc-500 mt-1">Compose and build immutable agent environments.</p>
                </div>
                <Button
                    variant="outline"
                    className="bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white h-10 px-4 rounded-xl"
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
                        <div key={i} className="h-48 rounded-2xl bg-zinc-900/50 border border-zinc-800 animate-pulse" />
                    ))}
                </div>
            ) : (
                <Tabs defaultValue="templates" className="w-full">
                    <TabsList>
                        <TabsTrigger value="templates">Templates ({templates.length})</TabsTrigger>
                        <TabsTrigger value="runtime">Runtime Blueprints ({runtimeBlueprints.length})</TabsTrigger>
                        <TabsTrigger value="network">Network Blueprints ({networkBlueprints.length})</TabsTrigger>
                    </TabsList>

                    <TabsContent value="templates">
                        <div className="flex justify-end mb-4">
                            <Button
                                className="bg-primary hover:bg-primary/90 text-white h-10 px-4 rounded-xl font-bold shadow-lg shadow-primary/10"
                                onClick={() => setIsTemplateOpen(true)}
                            >
                                <Plus className="mr-2 h-4 w-4" /> New Template
                            </Button>
                        </div>
                        {templates.length > 0 ? (
                            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                                {templates.map(t => <TemplateCard key={t.id} template={t} baseUpdatedAt={baseUpdatedAt} />)}
                            </div>
                        ) : (
                            <div className="py-20 text-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20">
                                <Boxes className="h-12 w-12 text-zinc-800 mx-auto mb-4" />
                                <h3 className="text-zinc-400 font-medium">No templates found</h3>
                                <p className="text-zinc-600 text-sm mt-1">Compose your first template using blueprints.</p>
                            </div>
                        )}
                    </TabsContent>

                    <TabsContent value="runtime">
                        <div className="flex justify-end mb-4">
                            <Button
                                variant="outline"
                                className="bg-zinc-900 border-zinc-800 text-white h-10 px-4 rounded-xl"
                                onClick={() => { setBlueprintDialogType('RUNTIME'); setBlueprintDialogOpen(true); }}
                            >
                                <Plus className="mr-2 h-4 w-4" /> New Runtime Blueprint
                            </Button>
                        </div>
                        {runtimeBlueprints.length > 0 ? (
                            <div className="space-y-3">
                                {runtimeBlueprints.map(b => <BlueprintItem key={b.id} blueprint={b} />)}
                            </div>
                        ) : (
                            <BlueprintEmptyState type="RUNTIME" />
                        )}
                    </TabsContent>

                    <TabsContent value="network">
                        <div className="flex justify-end mb-4">
                            <Button
                                variant="outline"
                                className="bg-zinc-900 border-zinc-800 text-white h-10 px-4 rounded-xl"
                                onClick={() => { setBlueprintDialogType('NETWORK'); setBlueprintDialogOpen(true); }}
                            >
                                <Plus className="mr-2 h-4 w-4" /> New Network Blueprint
                            </Button>
                        </div>
                        {networkBlueprints.length > 0 ? (
                            <div className="space-y-3">
                                {networkBlueprints.map(b => <BlueprintItem key={b.id} blueprint={b} />)}
                            </div>
                        ) : (
                            <BlueprintEmptyState type="NETWORK" />
                        )}
                    </TabsContent>
                </Tabs>
            )}

            <CreateBlueprintDialog
                open={blueprintDialogOpen}
                onOpenChange={setBlueprintDialogOpen}
                presetType={blueprintDialogType}
            />
            <CreateTemplateDialog open={isTemplateOpen} onOpenChange={setIsTemplateOpen} />
        </div>
    );
};

export default Templates;
