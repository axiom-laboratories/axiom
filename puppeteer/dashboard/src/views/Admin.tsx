import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Cpu,
    ShieldAlert,
    Key,
    Zap,
    Copy,
    CheckCircle2,
    RefreshCcw,
    Lock,
    Terminal,
    AlertCircle,
    AlertTriangle,
    Database,
    Plus,
    Trash2,
    Upload,
    Download,
    Package,
    Check,
    Loader2,
    ShieldCheck,
    Search,
    ChevronLeft,
    ChevronRight,
    GitBranch,
    RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from '@/components/ui/tabs';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from '@/components/ui/dialog';
import {
    AlertDialog,
    AlertDialogContent,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogCancel,
    AlertDialogAction,
} from '@/components/ui/alert-dialog';
import { Label } from '@/components/ui/label';
import { authenticatedFetch, getUser } from '../auth';
import { useLicence } from '../hooks/useLicence';
import { useFeatures } from '../hooks/useFeatures';
import { useWebSocket, LicenceStatusChangeData } from '../hooks/useWebSocket';
import { UpgradePlaceholder } from '../components/UpgradePlaceholder';
import { LicenceStatus } from '../components/LicenceStatus';
import { LicenceReloadButton } from '../components/LicenceReloadButton';
import { GracePeriodBanner } from '../components/GracePeriodBanner';
import { MirrorHealthBanner } from '../components/MirrorHealthBanner';
import { useSystemHealth } from '../hooks/useSystemHealth';
import { DependencyTreeModal } from '../components/foundry/DependencyTreeModal';

// --- Sub-components for Admin ---

function formatExpiryDate(days: number): string {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

const STATUS_BADGE: Record<string, string> = {
    valid:   'bg-emerald-500/20 text-emerald-400',
    grace:   'bg-amber-500/20 text-amber-400',
    expired: 'bg-red-500/20 text-red-400',
    ce:      'bg-muted/50 text-muted-foreground',
};

const STATUS_LABEL: Record<string, string> = {
    valid: 'Active', grace: 'Grace Period', expired: 'Expired', ce: 'Community',
};

const LicenceSection = () => {
    const licence = useLicence();
    const { isEnterprise, status, tier, days_until_expiry, node_limit, customer_id } = licence;

    const expiryValue = status === 'expired'
        ? 'Expired'
        : formatExpiryDate(days_until_expiry);

    const expiryClass = status === 'expired'
        ? 'text-red-400'
        : days_until_expiry < 30
        ? 'text-amber-400'
        : 'text-foreground';

    return (
        <div className="rounded-xl border border-muted bg-background p-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">Licence</h2>
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Edition</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        isEnterprise
                            ? 'bg-indigo-500/20 text-indigo-400'
                            : 'bg-muted/50 text-muted-foreground'
                    }`}>
                        {isEnterprise ? 'Enterprise' : 'Community'}
                    </span>
                </div>
                <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Status</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${STATUS_BADGE[status] ?? STATUS_BADGE.ce}`}>
                        {STATUS_LABEL[status] ?? status}
                    </span>
                </div>
                {isEnterprise && customer_id && (
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Customer</span>
                        <span className="text-sm text-foreground font-mono">{customer_id}</span>
                    </div>
                )}
                {isEnterprise && (
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Expires</span>
                        <span className={`text-sm ${expiryClass}`}>
                            {expiryValue}
                        </span>
                    </div>
                )}
                {isEnterprise && node_limit > 0 && (
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Node limit</span>
                        <span className="text-sm text-foreground">{node_limit}</span>
                    </div>
                )}
                {!isEnterprise && (
                    <p className="text-sm text-muted-foreground">
                        Set <code className="text-foreground">AXIOM_LICENCE_KEY</code> environment variable to enable Enterprise Edition features.
                    </p>
                )}
            </div>
        </div>
    );
};

// Licence tab content component with WebSocket updates
const LicenceTabContent = () => {
    const queryClient = useQueryClient();
    const licence = useLicence();
    const [lastReloadTime, setLastReloadTime] = useState<string | null>(null);

    // Subscribe to licence status changes via WebSocket
    const handleLicenceStatusChanged = (data: LicenceStatusChangeData) => {
        // Invalidate the licence query to trigger a refresh
        queryClient.invalidateQueries({ queryKey: ['licence'] });
        setLastReloadTime(new Date().toLocaleTimeString());
        toast.info(`Licence updated: ${data.old_status} → ${data.new_status}`);
    };

    // Setup WebSocket listener
    useWebSocket(() => {}, handleLicenceStatusChanged);

    const expiryDate = licence.status !== 'expired' && licence.status !== 'ce'
        ? new Date(Date.now() + licence.days_until_expiry * 24 * 60 * 60 * 1000).toLocaleDateString(
            undefined,
            { year: 'numeric', month: 'short', day: 'numeric' }
          )
        : undefined;

    return (
        <div className="space-y-6">
            {licence.status === 'grace' && (
                <GracePeriodBanner
                    daysRemaining={licence.days_until_expiry}
                    expiryDate={expiryDate}
                    onDismiss={() => setLastReloadTime(new Date().toLocaleTimeString())}
                />
            )}

            <div className="flex items-center justify-between mb-4">
                <div>
                    <h2 className="text-lg font-semibold text-foreground">Licence Management</h2>
                    <p className="text-sm text-muted-foreground mt-1">View and manage your licence status and settings.</p>
                </div>
                <LicenceReloadButton
                    isAdmin={true}
                    onReloadSuccess={() => {
                        queryClient.invalidateQueries({ queryKey: ['licence'] });
                        setLastReloadTime(new Date().toLocaleTimeString());
                    }}
                />
            </div>

            <LicenceStatus
                status={licence.status}
                tier={licence.tier}
                organization={licence.customer_id || undefined}
                customerID={licence.customer_id || undefined}
                nodeLimit={licence.node_limit}
                daysUntilExpiry={licence.days_until_expiry}
                expiryDate={expiryDate}
                lastReloadTime={lastReloadTime ? `${lastReloadTime}` : undefined}
            />
        </div>
    );
};

const TriggerManager = () => {
    const queryClient = useQueryClient();
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [newTrigger, setNewTrigger] = useState({ name: '', slug: '', job_definition_id: '' });
    const [isDisableConfirmOpen, setIsDisableConfirmOpen] = useState(false);
    const [pendingToggleTrigger, setPendingToggleTrigger] = useState<any>(null);
    const [isRotateConfirmOpen, setIsRotateConfirmOpen] = useState(false);
    const [isTokenRevealOpen, setIsTokenRevealOpen] = useState(false);
    const [newToken, setNewToken] = useState<string | null>(null);
    const [pendingRotateTrigger, setPendingRotateTrigger] = useState<any>(null);

    const { data: triggers = [] } = useQuery({
        queryKey: ['automation-triggers'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/admin/triggers');
            return res.json();
        }
    });

    const { data: jobDefs = [] } = useQuery({
        queryKey: ['job-definitions'],
        queryFn: async () => {
            const res = await authenticatedFetch('/job-definitions');
            return res.json();
        }
    });

    const createMutation = useMutation({
        mutationFn: async (payload: any) => {
            const res = await authenticatedFetch('/api/admin/triggers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['automation-triggers'] });
            toast.success('Trigger registered');
            setIsCreateOpen(false);
            setNewTrigger({ name: '', slug: '', job_definition_id: '' });
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            await authenticatedFetch(`/api/admin/triggers/${id}`, { method: 'DELETE' });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['automation-triggers'] });
            toast.success('Trigger removed');
        }
    });

    const toggleMutation = useMutation({
        mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }) => {
            const res = await authenticatedFetch(`/api/admin/triggers/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active })
            });
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['automation-triggers'] });
            toast.success('Trigger updated');
            setIsDisableConfirmOpen(false);
        }
    });

    const rotateMutation = useMutation({
        mutationFn: async (id: string) => {
            const res = await authenticatedFetch(`/api/admin/triggers/${id}/regenerate-token`, {
                method: 'POST'
            });
            return res.json();
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['automation-triggers'] });
            setNewToken(data.secret_token);
            setIsRotateConfirmOpen(false);
            setIsTokenRevealOpen(true);
            toast.success('Token regenerated');
        }
    });

    const copyCurl = (trigger: any) => {
        const baseUrl = window.location.origin;
        const curl = `curl -X POST "${baseUrl}/api/trigger/${trigger.slug}" \\
  -H "X-MOP-Trigger-Key: ${trigger.secret_token}" \\
  -H "Content-Type: application/json" \\
  -d '{"ref": "main", "actor": "github-actions"}'`;
        navigator.clipboard.writeText(curl);
        toast.success('Curl command copied to clipboard');
    };

    return (
        <div className="space-y-6">
            <Card className="bg-card border-muted/50">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="text-foreground font-bold flex items-center gap-2">
                            <Zap className="h-5 w-5 text-primary fill-current" />
                            Automation Triggers
                        </CardTitle>
                        <CardDescription>Headless endpoints for CI/CD integrations.</CardDescription>
                    </div>
                    <Button onClick={() => setIsCreateOpen(true)} size="sm" className="bg-primary hover:bg-primary/90 text-foreground font-bold">
                        <Plus className="mr-2 h-4 w-4" /> Create Trigger
                    </Button>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader className="bg-background/50">
                            <TableRow className="border-muted">
                                <TableHead className="text-muted-foreground">Name</TableHead>
                                <TableHead className="text-muted-foreground">Slug</TableHead>
                                <TableHead className="text-muted-foreground">Target Job</TableHead>
                                <TableHead className="text-muted-foreground">Status</TableHead>
                                <TableHead className="text-muted-foreground text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {triggers.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="py-16 text-center">
                                        <div className="flex flex-col items-center gap-3">
                                            <Zap className="h-8 w-8 text-muted-foreground/40" />
                                            <p className="text-foreground font-medium">No triggers yet.</p>
                                            <p className="text-muted-foreground text-sm max-w-xs">
                                                Triggers are secure webhooks that let external systems (GitHub Actions, scripts) fire jobs.
                                            </p>
                                            <Button size="sm" className="mt-2 bg-primary hover:bg-primary/90 text-foreground font-bold"
                                                onClick={() => setIsCreateOpen(true)}>
                                                <Plus className="mr-2 h-4 w-4" /> Create Trigger
                                            </Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                triggers.map((t: any) => (
                                    <TableRow key={t.id} className="border-muted group hover:bg-white/[0.02]">
                                        <TableCell className="text-foreground font-medium">{t.name}</TableCell>
                                        <TableCell className="font-mono text-muted-foreground text-xs">/api/trigger/{t.slug}</TableCell>
                                        <TableCell className="text-muted-foreground text-xs">
                                            {jobDefs.find((j: any) => j.id === t.job_definition_id)?.name || t.job_definition_id}
                                        </TableCell>
                                        <TableCell>
                                            {t.is_active ? (
                                                <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">Active</Badge>
                                            ) : (
                                                <Badge className="bg-muted/10 text-muted-foreground border-muted/20">Inactive</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right flex justify-end gap-2">
                                            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground gap-2" onClick={() => copyCurl(t)}>
                                                <Copy className="h-3 w-3" /> Copy Curl
                                            </Button>
                                            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground gap-2"
                                                onClick={() => { navigator.clipboard.writeText(t.secret_token); toast.success('Token copied'); }}>
                                                <Key className="h-3 w-3" /> Copy Token
                                            </Button>
                                            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-amber-400 gap-2"
                                                onClick={() => {
                                                    if (t.is_active) {
                                                        setPendingToggleTrigger(t);
                                                        setIsDisableConfirmOpen(true);
                                                    } else {
                                                        toggleMutation.mutate({ id: t.id, is_active: true });
                                                    }
                                                }}>
                                                <RefreshCcw className="h-3 w-3" /> {t.is_active ? 'Disable' : 'Enable'}
                                            </Button>
                                            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-amber-400 gap-2"
                                                onClick={() => { setPendingRotateTrigger(t); setIsRotateConfirmOpen(true); }}>
                                                <Lock className="h-3 w-3" /> Rotate Key
                                            </Button>
                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground/60 hover:text-red-400" onClick={() => deleteMutation.mutate(t.id)}>
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogContent className="bg-card border-muted text-foreground">
                    <DialogHeader>
                        <DialogTitle>Create Automation Trigger</DialogTitle>
                        <DialogDescription>Define a secure webhook for external systems.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Display Name</Label>
                            <Input 
                                placeholder="GitHub Actions Deployment" 
                                value={newTrigger.name}
                                onChange={e => setNewTrigger({...newTrigger, name: e.target.value})}
                                className="bg-background border-muted"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>URL Slug</Label>
                            <Input 
                                placeholder="deploy-prod" 
                                value={newTrigger.slug}
                                onChange={e => setNewTrigger({...newTrigger, slug: e.target.value})}
                                className="bg-background border-muted font-mono"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Target Job Definition</Label>
                            <Select value={newTrigger.job_definition_id} onValueChange={v => setNewTrigger({...newTrigger, job_definition_id: v})}>
                                <SelectTrigger className="bg-background border-muted">
                                    <SelectValue placeholder="Select a job to trigger..." />
                                </SelectTrigger>
                                <SelectContent className="bg-secondary border-muted text-foreground">
                                    {jobDefs.map((j: any) => (
                                        <SelectItem key={j.id} value={j.id}>{j.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
                        <Button 
                            disabled={!newTrigger.name || !newTrigger.slug || !newTrigger.job_definition_id}
                            onClick={() => createMutation.mutate(newTrigger)}
                            className="bg-primary hover:bg-primary/90 text-foreground font-bold"
                        >
                            Register Trigger
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <AlertDialog open={isDisableConfirmOpen} onOpenChange={setIsDisableConfirmOpen}>
                <AlertDialogContent className="bg-card border-muted text-foreground">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Disable this trigger?</AlertDialogTitle>
                        <AlertDialogDescription className="text-muted-foreground">
                            Disabling this trigger will prevent new jobs from being fired. Continue?
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel className="bg-muted border-muted text-foreground hover:bg-muted">Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => pendingToggleTrigger && toggleMutation.mutate({ id: pendingToggleTrigger.id, is_active: false })}
                            className="bg-amber-600 hover:bg-amber-700 text-foreground">
                            Disable Trigger
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <AlertDialog open={isRotateConfirmOpen} onOpenChange={setIsRotateConfirmOpen}>
                <AlertDialogContent className="bg-card border-muted text-foreground">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Rotate trigger token?</AlertDialogTitle>
                        <AlertDialogDescription className="text-muted-foreground">
                            This will invalidate the current token. Existing integrations will break until updated.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel className="bg-muted border-muted text-foreground hover:bg-muted">Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => pendingRotateTrigger && rotateMutation.mutate(pendingRotateTrigger.id)}
                            className="bg-amber-600 hover:bg-amber-700 text-foreground">
                            Rotate Token
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <Dialog open={isTokenRevealOpen} onOpenChange={setIsTokenRevealOpen}>
                <DialogContent className="bg-card border-muted text-foreground max-w-lg">
                    <DialogHeader>
                        <div className="flex items-center gap-2 text-emerald-500 mb-2">
                            <CheckCircle2 className="h-6 w-6" />
                            <DialogTitle>New Token Generated</DialogTitle>
                        </div>
                        <DialogDescription className="text-muted-foreground">
                            This is the only time you'll see this token. Copy it now.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex gap-3">
                            <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
                            <p className="text-xs text-amber-200/80">
                                Store this token securely. Loss requires another rotation.
                            </p>
                        </div>
                        <div className="space-y-2">
                            <Label className="text-muted-foreground">Secret Token</Label>
                            <div className="flex gap-2">
                                <Input readOnly value={newToken || ''} className="bg-background border-muted font-mono text-xs" />
                                <Button size="icon" variant="outline"
                                    onClick={() => { navigator.clipboard.writeText(newToken || ''); toast.success('Token copied'); }}>
                                    <Copy className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button className="w-full bg-foreground hover:bg-white text-background font-bold"
                            onClick={() => setIsTokenRevealOpen(false)}>
                            I have saved the token
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

const BOMExplorer = () => {
    const [search, setSearch] = useState('');
    const { data: results = [], isLoading } = useQuery({
        queryKey: ['package-search', search],
        queryFn: async () => {
            if (!search) return [];
            const res = await authenticatedFetch(`/api/foundry/search-packages?q=${search}`);
            return res.json();
        },
        enabled: search.length > 2
    });

    return (
        <Card className="bg-card border-muted/50">
            <CardHeader>
                <CardTitle className="text-foreground font-bold flex items-center gap-2">
                    <Search className="h-5 w-5 text-primary" />
                    BOM Explorer
                </CardTitle>
                <CardDescription>Search for specific package versions across all baked images.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input 
                        placeholder="Search package name (e.g. cryptography, requests)..." 
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="pl-10 bg-background border-muted"
                    />
                </div>

                <div className="rounded-xl border border-muted overflow-hidden">
                    <Table>
                        <TableHeader className="bg-background/50">
                            <TableRow className="border-muted">
                                <TableHead className="text-muted-foreground">Type</TableHead>
                                <TableHead className="text-muted-foreground">Package</TableHead>
                                <TableHead className="text-muted-foreground">Version</TableHead>
                                <TableHead className="text-muted-foreground">Template ID</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {isLoading ? (
                                <TableRow><TableCell colSpan={4} className="py-12 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto text-primary/50" /></TableCell></TableRow>
                            ) : results.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={4} className="py-12 text-center text-muted-foreground">
                                        {search.length > 2 ? 'No results found.' : 'Enter at least 3 characters to search.'}
                                    </TableCell>
                                </TableRow>
                            ) : (
                                results.map((r: any) => (
                                    <TableRow key={r.id} className="border-muted hover:bg-white/[0.02]">
                                        <TableCell><Badge variant="outline" className="text-[10px]">{r.type.toUpperCase()}</Badge></TableCell>
                                        <TableCell className="text-foreground font-medium">{r.name}</TableCell>
                                        <TableCell className="font-mono text-muted-foreground text-xs">{r.version}</TableCell>
                                        <TableCell className="text-muted-foreground font-mono text-[10px]">{r.template_id}</TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>
        </Card>
    );
};

const RolloutManager = () => {
    const queryClient = useQueryClient();
    const [selectedToolId, setSelectedToolId] = useState<string>('');
    const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());
    const [rolloutStatus, setRolloutStatus] = useState<'idle' | 'running' | 'complete'>('idle');

    const { data: matrix = [] } = useQuery({
        queryKey: ['capability-matrix'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/capability-matrix');
            if (!res.ok) return [];
            return res.json();
        }
    });

    const { data: nodes = [] } = useQuery({
        queryKey: ['nodes'],
        queryFn: async () => {
            const res = await authenticatedFetch('/nodes');
            return res.json();
        }
    });

    const toggleNode = (id: string) => {
        const next = new Set(selectedNodes);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedNodes(next);
    };

    const handleBatchUpgrade = async () => {
        if (!selectedToolId || selectedNodes.size === 0) return;
        setRolloutStatus('running');
        let success = 0;
        let failed = 0;

        for (const nodeId of selectedNodes) {
            try {
                const res = await authenticatedFetch(`/api/nodes/${nodeId}/upgrade?capability_id=${selectedToolId}`, {
                    method: 'POST'
                });
                if (res.ok) success++;
                else failed++;
            } catch {
                failed++;
            }
        }

        setRolloutStatus('complete');
        queryClient.invalidateQueries({ queryKey: ['nodes'] });
        toast.success(`Rollout complete: ${success} started, ${failed} failed`);
    };

    const selectedTool = matrix.find((m: any) => String(m.id) === selectedToolId);

    return (
        <div className="space-y-6">
            <Card className="bg-card border-muted/50">
                <CardHeader>
                    <CardTitle className="text-foreground font-bold flex items-center gap-2">
                        <Package className="h-5 w-5 text-primary" />
                        Staged Rollout
                    </CardTitle>
                    <CardDescription>Push a capability update to multiple nodes simultaneously.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-1">1. Select Target Tool</label>
                        <Select value={selectedToolId} onValueChange={setSelectedToolId}>
                            <SelectTrigger className="bg-background border-muted">
                                <SelectValue placeholder="Choose a tool recipe..." />
                            </SelectTrigger>
                            <SelectContent className="bg-secondary border-muted text-foreground">
                                {matrix.map((m: any) => (
                                    <SelectItem key={m.id} value={String(m.id)}>{m.tool_id} ({m.base_os_family})</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-1">2. Select Target Nodes</label>
                        <div className="rounded-xl border border-muted bg-background overflow-hidden">
                            <Table>
                                <TableHeader className="bg-secondary/50">
                                    <TableRow className="border-muted">
                                        <TableHead className="w-12"></TableHead>
                                        <TableHead className="text-muted-foreground">Hostname</TableHead>
                                        <TableHead className="text-muted-foreground">OS</TableHead>
                                        <TableHead className="text-muted-foreground">Tags</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {nodes.filter((n: any) => !selectedTool || n.base_os_family === selectedTool.base_os_family).map((n: any) => (
                                        <TableRow 
                                            key={n.node_id} 
                                            className={`border-muted cursor-pointer transition-colors ${selectedNodes.has(n.node_id) ? 'bg-primary/5' : 'hover:bg-white/[0.02]'}`}
                                            onClick={() => toggleNode(n.node_id)}
                                        >
                                            <TableCell>
                                                <div className={`h-4 w-4 rounded border flex items-center justify-center transition-all ${selectedNodes.has(n.node_id) ? 'bg-primary border-primary' : 'border-muted bg-secondary'}`}>
                                                    {selectedNodes.has(n.node_id) && <Check className="h-3 w-3 text-foreground stroke-[3]" />}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-foreground font-medium">{n.hostname}</TableCell>
                                            <TableCell><Badge variant="outline" className="text-[8px]">{n.base_os_family}</Badge></TableCell>
                                            <TableCell>
                                                <div className="flex gap-1">
                                                    {n.tags?.slice(0, 2).map((t: string) => (
                                                        <span key={t} className="text-[8px] text-muted-foreground">{t}</span>
                                                    ))}
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    </div>
                </CardContent>
                <CardFooter className="bg-secondary/30 border-t border-muted flex items-center justify-between py-4">
                    <div className="text-xs text-muted-foreground">
                        {selectedNodes.size} nodes selected for rollout
                    </div>
                    <Button 
                        disabled={!selectedToolId || selectedNodes.size === 0 || rolloutStatus === 'running'}
                        onClick={handleBatchUpgrade}
                        className="bg-primary hover:bg-primary/90 text-foreground font-bold px-8"
                    >
                        {rolloutStatus === 'running' ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Executing...</> : 'Initiate Rollout'}
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
};

const CapabilityMatrixManager = () => {
    const queryClient = useQueryClient();
    const { data: matrix = [] } = useQuery({
        queryKey: ['capability-matrix'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/capability-matrix');
            if (!res.ok) return [];
            return res.json();
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            await authenticatedFetch(`/api/capability-matrix/${id}`, { method: 'DELETE' });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['capability-matrix'] });
            toast.success('Tool recipe removed');
        }
    });

    return (
        <Card className="bg-card border-muted/50">
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle className="text-foreground font-bold">Tool Registry</CardTitle>
                    <CardDescription>Injection recipes for Puppet runtimes.</CardDescription>
                </div>
                <Button size="sm" className="bg-primary hover:bg-primary/90 text-foreground font-bold">
                    <Plus className="mr-2 h-4 w-4" /> Register Tool
                </Button>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader className="bg-background/50">
                        <TableRow className="border-muted">
                            <TableHead className="text-muted-foreground">OS Family</TableHead>
                            <TableHead className="text-muted-foreground">Tool ID</TableHead>
                            <TableHead className="text-muted-foreground">Recipe</TableHead>
                            <TableHead className="text-muted-foreground text-right">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {matrix.map((item: any) => (
                            <TableRow key={item.id} className="border-muted group hover:bg-white/[0.02]">
                                <TableCell><Badge variant="outline">{item.base_os_family}</Badge></TableCell>
                                <TableCell className="font-mono text-foreground text-xs">{item.tool_id}</TableCell>
                                <TableCell className="max-w-[300px] truncate font-mono text-[10px] text-muted-foreground">
                                    {item.injection_recipe}
                                </TableCell>
                                <TableCell className="text-right">
                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground/60 hover:text-red-400" onClick={() => deleteMutation.mutate(item.id)}>
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
};

const ArtifactVault = () => {
    const queryClient = useQueryClient();
    const { data: artifacts = [] } = useQuery({
        queryKey: ['artifacts'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/artifacts');
            if (!res.ok) return [];
            return res.json();
        }
    });

    const uploadMutation = useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append('file', file);
            const res = await authenticatedFetch('/api/artifacts', {
                method: 'POST',
                body: formData
            });
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['artifacts'] });
            toast.success('Artifact stored in vault');
        }
    });

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            uploadMutation.mutate(e.target.files[0]);
        }
    };

    return (
        <Card className="bg-card border-muted/50">
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle className="text-foreground font-bold text-xl flex items-center gap-2">
                        <Database className="h-5 w-5 text-primary" />
                        Artifact Vault
                    </CardTitle>
                    <CardDescription>Secure binary storage for node-side upgrades.</CardDescription>
                </div>
                <div className="flex gap-2">
                    <input type="file" id="artifact-upload" className="hidden" onChange={handleFileUpload} />
                    <Button 
                        size="sm" 
                        className="bg-muted hover:bg-muted text-foreground font-bold"
                        onClick={() => document.getElementById('artifact-upload')?.click()}
                        disabled={uploadMutation.isPending}
                    >
                        <Upload className="mr-2 h-4 w-4" /> {uploadMutation.isPending ? 'Storing...' : 'Upload Binary'}
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader className="bg-background/50">
                        <TableRow className="border-muted">
                            <TableHead className="text-muted-foreground">Filename</TableHead>
                            <TableHead className="text-muted-foreground">Size</TableHead>
                            <TableHead className="text-muted-foreground">SHA256</TableHead>
                            <TableHead className="text-muted-foreground text-right">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {artifacts.map((item: any) => (
                            <TableRow key={item.id} className="border-muted group">
                                <TableCell className="text-foreground font-medium flex items-center gap-2">
                                    <Package className="h-3.5 w-3.5 text-muted-foreground" />
                                    {item.filename}
                                </TableCell>
                                <TableCell className="text-xs text-muted-foreground">{(item.size_bytes / 1024 / 1024).toFixed(2)} MB</TableCell>
                                <TableCell className="font-mono text-[10px] text-muted-foreground/60 truncate max-w-[120px]">{item.sha256}</TableCell>
                                <TableCell className="text-right">
                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground/60 hover:text-foreground" asChild>
                                        <a href={`/api/artifacts/${item.id}/download`} download>
                                            <Download className="h-4 w-4" />
                                        </a>
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
};

const MirrorStatusBadge = ({ status }: { status: string }) => {
    switch (status) {
        case 'MIRRORED':
            return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 gap-1"><Check className="h-3 w-3" /> Mirrored</Badge>;
        case 'FAILED':
            return <Badge className="bg-red-500/10 text-red-500 border-red-500/20 gap-1"><AlertCircle className="h-3 w-3" /> Failed</Badge>;
        default:
            return <Badge variant="outline" className="text-muted-foreground gap-1 animate-pulse"><RefreshCcw className="h-3 w-3" /> Pending</Badge>;
    }
};

const SmelterRegistryManager = () => {
    const queryClient = useQueryClient();
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [newIngredient, setNewIngredient] = useState({ name: '', version_constraint: '', sha256: '', os_family: 'DEBIAN' });
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [uploadingId, setUploadingId] = useState<string | null>(null);
    const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
    const [selectedIngredient, setSelectedIngredient] = useState<{ id: string; name: string } | null>(null);
    const [discoveringId, setDiscoveringId] = useState<string | null>(null);
    const [mirrorForm, setMirrorForm] = useState<{ pypi_mirror_url: string; apt_mirror_url: string }>({
        pypi_mirror_url: '',
        apt_mirror_url: '',
    });

    const { data: ingredients = [] } = useQuery({
        queryKey: ['smelter-ingredients'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/smelter/ingredients');
            if (!res.ok) return [];
            return res.json();
        }
    });

    const { data: health = { pypi_online: false, apt_online: false, disk_used_gb: 0, disk_total_gb: 0 } } = useQuery({
        queryKey: ['smelter-health'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/smelter/mirror-health');
            if (!res.ok) return { pypi_online: false, apt_online: false, disk_used_gb: 0, disk_total_gb: 0 };
            return res.json();
        },
        refetchInterval: 30000
    });

    // scaleHealth type: { is_postgres: boolean, pool_size: number|null, checked_out: number|null, available: number|null, overflow: number|null, apscheduler_jobs: number, pending_job_depth: number } | null
    const { data: scaleHealth } = useQuery({
        queryKey: ['scale-health'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/health/scale');
            if (!res.ok) return null;
            return res.json();
        },
        refetchInterval: 30000
    });

    const uploadMutation = useMutation({
        mutationFn: async ({ id, file }: { id: string, file: File }) => {
            const formData = new FormData();
            formData.append('file', file);
            const res = await authenticatedFetch(`/api/smelter/ingredients/${id}/upload`, {
                method: 'POST',
                body: formData
            });
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['smelter-ingredients'] });
            toast.success('Package uploaded successfully');
            setUploadingId(null);
        },
        onError: () => {
            toast.error('Upload failed');
            setUploadingId(null);
        }
    });

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, id: string) => {
        const file = e.target.files?.[0];
        if (file) {
            setUploadingId(id);
            uploadMutation.mutate({ id, file });
        }
    };

    const { data: config = { smelter_enforcement_mode: 'WARNING' } } = useQuery({
        queryKey: ['smelter-config'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/smelter/config');
            return res.json();
        }
    });

    const createMutation = useMutation({
        mutationFn: async (payload: any) => {
            const res = await authenticatedFetch('/api/smelter/ingredients', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['smelter-ingredients'] });
            toast.success('Ingredient approved');
            setIsCreateOpen(false);
            setNewIngredient({ name: '', version_constraint: '', sha256: '', os_family: 'DEBIAN' });
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            await authenticatedFetch(`/api/smelter/ingredients/${id}`, { method: 'DELETE' });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['smelter-ingredients'] });
            toast.success('Ingredient removed');
        }
    });

    const updateConfigMutation = useMutation({
        mutationFn: async (mode: string) => {
            const res = await authenticatedFetch('/api/smelter/config', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ smelter_enforcement_mode: mode })
            });
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['smelter-config'] });
            toast.success('Enforcement mode updated');
        }
    });

    const discoverMutation = useMutation({
        mutationFn: async (ingredientId: string) => {
            const res = await authenticatedFetch(`/api/smelter/ingredients/${ingredientId}/discover`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approve_all: true })
            });
            if (!res.ok) throw new Error('Discovery failed');
            return res.json();
        },
        onSuccess: (data) => {
            toast.success(data.toast_message);
            queryClient.invalidateQueries({ queryKey: ['smelter-ingredients'] });
            setDiscoveringId(null);
        },
        onError: (error: any) => {
            toast.error(`Discovery failed: ${error.message}`);
            setDiscoveringId(null);
        }
    });

    const scanMutation = useMutation({
        mutationFn: async () => {
            const res = await authenticatedFetch('/api/smelter/scan', { method: 'POST' });
            if (!res.ok) throw new Error('Scan failed');
            return res.json();
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['smelter-ingredients'] });
            toast.success(`Scan complete: ${data.vulnerable} vulnerable packages found.`);
        },
        onError: () => toast.error('Vulnerability scan failed')
    });

    const { data: mirrorConfigData } = useQuery({
        queryKey: ['mirror-config'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/admin/mirror-config');
            return res.json() as Promise<{ pypi_mirror_url: string; apt_mirror_url: string }>;
        },
    });

    useEffect(() => {
        if (mirrorConfigData) {
            setMirrorForm({
                pypi_mirror_url: mirrorConfigData.pypi_mirror_url,
                apt_mirror_url: mirrorConfigData.apt_mirror_url,
            });
        }
    }, [mirrorConfigData]);

    const updateMirrorConfigMutation = useMutation({
        mutationFn: async (payload: { pypi_mirror_url?: string; apt_mirror_url?: string }) => {
            const res = await authenticatedFetch('/api/admin/mirror-config', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['mirror-config'] });
            toast.success('Mirror source settings saved');
        },
        onError: () => toast.error('Failed to save mirror settings'),
    });

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="bg-card border-muted/50 lg:col-span-2">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="text-foreground font-bold flex items-center gap-2">
                                <Package className="h-5 w-5 text-primary" />
                                Approved Ingredients
                            </CardTitle>
                            <CardDescription>Vetted packages allowed in Puppet images.</CardDescription>
                        </div>
                        <div className="flex gap-2">
                            <Button 
                                variant="outline" 
                                size="sm" 
                                className="border-muted text-muted-foreground hover:text-foreground"
                                onClick={() => scanMutation.mutate()}
                                disabled={scanMutation.isPending || ingredients.length === 0}
                            >
                                {scanMutation.isPending ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Scanning...</>
                                ) : (
                                    <><ShieldCheck className="mr-2 h-4 w-4" /> Scan for Vulnerabilities</>
                                )}
                            </Button>
                            <Button onClick={() => setIsCreateOpen(true)} size="sm" className="bg-primary hover:bg-primary/90 text-foreground font-bold">
                                <Plus className="mr-2 h-4 w-4" /> Approve Package
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader className="bg-background/50">
                                <TableRow className="border-muted">
                                    <TableHead className="text-muted-foreground">OS</TableHead>
                                    <TableHead className="text-muted-foreground">Name</TableHead>
                                    <TableHead className="text-muted-foreground">Version</TableHead>
                                    <TableHead className="text-muted-foreground">Mirror</TableHead>
                                    <TableHead className="text-muted-foreground">CVEs</TableHead>
                                    <TableHead className="text-muted-foreground">Security</TableHead>
                                    <TableHead className="text-muted-foreground text-right">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {ingredients.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="py-12 text-center text-muted-foreground">
                                            No approved ingredients yet.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    ingredients.map((i: any) => (
                                        <React.Fragment key={i.id}>
                                        <TableRow className={`border-muted group hover:bg-white/[0.02] ${discoveringId === i.id ? 'opacity-60' : ''}`}>
                                            <TableCell><Badge variant="outline" className="text-[10px]">{i.os_family}</Badge></TableCell>
                                            <TableCell className="text-foreground font-medium">{i.name}</TableCell>
                                            <TableCell className="font-mono text-muted-foreground text-xs">{i.version_constraint}</TableCell>
                                            <TableCell><MirrorStatusBadge status={i.mirror_status} /></TableCell>
                                            <TableCell>
                                                {i.total_cve_count > 0 ? (
                                                    <button
                                                        onClick={() => setSelectedIngredient({ id: i.id, name: i.name })}
                                                        className={`inline-flex items-center gap-1 px-2 py-1 rounded text-sm font-medium cursor-pointer hover:opacity-80 transition-opacity ${
                                                            i.worst_severity === 'CRITICAL' ? 'bg-red-100 text-red-900 dark:bg-red-900 dark:text-red-100' :
                                                            i.worst_severity === 'HIGH' ? 'bg-orange-100 text-orange-900 dark:bg-orange-900 dark:text-orange-100' :
                                                            i.worst_severity === 'MEDIUM' ? 'bg-yellow-100 text-yellow-900 dark:bg-yellow-900 dark:text-yellow-100' :
                                                            'bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-100'
                                                        }`}
                                                    >
                                                        {i.worst_severity === 'CRITICAL' ? '🟥' : i.worst_severity === 'HIGH' ? '🟧' : i.worst_severity === 'MEDIUM' ? '🟨' : '🟦'}
                                                        {i.total_cve_count}
                                                    </button>
                                                ) : (
                                                    <div className="inline-flex items-center gap-1 text-green-600 dark:text-green-400 text-sm font-medium">
                                                        ✅ Clean
                                                    </div>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                {i.is_vulnerable ? (
                                                    <Badge className="bg-red-500/10 text-red-500 border-red-500/20 gap-1">
                                                        <ShieldAlert className="h-3 w-3" /> Vulnerable
                                                    </Badge>
                                                ) : (
                                                    <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 gap-1">
                                                        <CheckCircle2 className="h-3 w-3" /> Secure
                                                    </Badge>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-right flex items-center justify-end gap-1">
                                                <input
                                                    type="file"
                                                    ref={fileInputRef}
                                                    style={{ display: 'none' }}
                                                    onChange={(e) => handleFileChange(e, i.id)}
                                                />
                                                {i.mirror_log && (
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className={`h-8 w-8 ${expandedLogId === i.id ? 'text-primary' : 'text-muted-foreground/60 hover:text-foreground'}`}
                                                        title="Show sync log"
                                                        onClick={() => setExpandedLogId(expandedLogId === i.id ? null : i.id)}
                                                    >
                                                        <Terminal className="h-4 w-4" />
                                                    </Button>
                                                )}
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 text-muted-foreground hover:text-primary"
                                                    disabled={uploadingId === i.id}
                                                    onClick={() => {
                                                        const el = document.createElement('input');
                                                        el.type = 'file';
                                                        el.onchange = (e: any) => handleFileChange(e, i.id);
                                                        el.click();
                                                    }}
                                                >
                                                    {uploadingId === i.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 text-muted-foreground hover:text-primary"
                                                    title="View dependency tree"
                                                    onClick={() => setSelectedIngredient({ id: i.id, name: i.name })}
                                                >
                                                    <Tree className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 text-muted-foreground hover:text-primary"
                                                    disabled={discoveringId === i.id}
                                                    title="Resolve and auto-approve transitive dependencies"
                                                    onClick={() => {
                                                        setDiscoveringId(i.id);
                                                        discoverMutation.mutate(i.id);
                                                    }}
                                                >
                                                    {discoveringId === i.id ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <RefreshCw className="h-4 w-4" />
                                                    )}
                                                </Button>
                                                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground/60 hover:text-red-400" onClick={() => deleteMutation.mutate(i.id)}>
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                        {i.mirror_log && expandedLogId === i.id && (
                                            <TableRow className="border-muted bg-background/40">
                                                <TableCell colSpan={7} className="py-2">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
                                                        <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Sync Log</span>
                                                    </div>
                                                    <pre className="text-[10px] text-muted-foreground font-mono whitespace-pre-wrap bg-secondary rounded p-2 max-h-48 overflow-y-auto border border-muted">{i.mirror_log}</pre>
                                                </TableCell>
                                            </TableRow>
                                        )}
                                        </React.Fragment>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                <div className="space-y-6">
                    <Card className="bg-card border-muted/50">
                        <CardHeader>
                            <CardTitle className="text-foreground font-bold flex items-center gap-2">
                                <Database className="h-5 w-5 text-primary" />
                                Repository Health
                            </CardTitle>
                            <CardDescription>Status of local package mirrors.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-muted-foreground">PyPI Server</span>
                                <Badge className={health.pypi_online ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"}>
                                    {health.pypi_online ? "ONLINE" : "OFFLINE"}
                                </Badge>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-muted-foreground">APT Mirror</span>
                                <Badge className={health.apt_online ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"}>
                                    {health.apt_online ? "ONLINE" : "OFFLINE"}
                                </Badge>
                            </div>
                            <div className="space-y-1.5">
                                <div className="flex items-center justify-between text-[10px]">
                                    <span className="text-muted-foreground uppercase tracking-wider font-bold">Disk Usage</span>
                                    <span className="text-muted-foreground">{health.disk_used_gb} / {health.disk_total_gb} GB</span>
                                </div>
                                <div className="h-1.5 w-full bg-background rounded-full overflow-hidden border border-white/5">
                                    <div
                                        className="h-full bg-primary transition-all duration-500"
                                        style={{ width: `${(health.disk_used_gb / health.disk_total_gb) * 100}%` }}
                                    />
                                </div>
                            </div>
                            {/* DB Pool + Scheduler metrics */}
                            <div className="pt-2 border-t border-muted/50 space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-muted-foreground">Pool checkout</span>
                                    <span className="text-xs text-foreground font-mono">
                                        {scaleHealth
                                            ? scaleHealth.is_postgres
                                                ? `${scaleHealth.checked_out} / ${scaleHealth.pool_size}`
                                                : 'N/A (SQLite)'
                                            : '—'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-muted-foreground">Pending jobs</span>
                                    <span className="text-xs text-foreground font-mono">
                                        {scaleHealth != null ? scaleHealth.pending_job_depth : '—'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-muted-foreground">APScheduler</span>
                                    <span className="text-xs text-foreground font-mono">
                                        {scaleHealth != null ? `${scaleHealth.apscheduler_jobs} jobs active` : '—'}
                                    </span>
                                </div>
                            </div>
                            <div className="pt-2 border-t border-muted/50">
                                <a
                                    href={`${window.location.protocol}//${window.location.hostname}:8081`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-2 text-xs text-muted-foreground hover:text-primary transition-colors"
                                >
                                    <Database className="h-3.5 w-3.5" />
                                    Browse raw file repository
                                </a>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-card border-muted/50 h-fit">
                    <CardHeader>
                        <CardTitle className="text-foreground font-bold flex items-center gap-2">
                            <ShieldAlert className="h-5 w-5 text-primary" />
                            Enforcement
                        </CardTitle>
                        <CardDescription>Configure how Smelter handles unapproved ingredients.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label className="text-muted-foreground">Enforcement Mode</Label>
                            <Select 
                                value={config.smelter_enforcement_mode} 
                                onValueChange={(v) => updateConfigMutation.mutate(v)}
                            >
                                <SelectTrigger className="bg-background border-muted">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-secondary border-muted text-foreground">
                                    <SelectItem value="WARNING">WARNING (Log & Badge)</SelectItem>
                                    <SelectItem value="STRICT">STRICT (Block Build)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="p-3 rounded-lg bg-secondary/50 border border-muted text-[11px] text-muted-foreground leading-relaxed">
                            {config.smelter_enforcement_mode === 'STRICT' ? (
                                <p><span className="text-red-400 font-bold">STRICT MODE:</span> Any blueprint containing ingredients not in the approved list will be rejected by the Foundry.</p>
                            ) : (
                                <p><span className="text-amber-400 font-bold">WARNING MODE:</span> Unapproved builds will proceed but will be marked as "Non-Compliant" in the dashboard.</p>
                            )}
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-card border-muted/50">
                    <CardHeader>
                        <CardTitle className="text-foreground font-bold flex items-center gap-2">
                            <RefreshCcw className="h-5 w-5 text-primary" />
                            Mirror Source Settings
                        </CardTitle>
                        <CardDescription>Configure upstream mirror source URLs.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label className="text-muted-foreground text-xs uppercase font-bold tracking-wider">PyPI Index URL</Label>
                            <Input
                                className="bg-background border-muted font-mono text-xs"
                                value={mirrorForm.pypi_mirror_url}
                                onChange={(e) => setMirrorForm(prev => ({ ...prev, pypi_mirror_url: e.target.value }))}
                                placeholder="http://pypi:8080/simple"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-muted-foreground text-xs uppercase font-bold tracking-wider">APT Mirror URL</Label>
                            <Input
                                className="bg-background border-muted font-mono text-xs"
                                value={mirrorForm.apt_mirror_url}
                                onChange={(e) => setMirrorForm(prev => ({ ...prev, apt_mirror_url: e.target.value }))}
                                placeholder="http://mirror/apt"
                            />
                        </div>
                        <Button
                            size="sm"
                            className="w-full bg-primary hover:bg-primary/90 text-foreground font-bold"
                            disabled={updateMirrorConfigMutation.isPending}
                            onClick={() => updateMirrorConfigMutation.mutate(mirrorForm)}
                        >
                            {updateMirrorConfigMutation.isPending ? (
                                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                            ) : (
                                'Save Mirror Settings'
                            )}
                        </Button>
                    </CardContent>
                </Card>
            </div>
        </div>

            <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogContent className="bg-card border-muted text-foreground">
                    <DialogHeader>
                        <DialogTitle>Approve Package</DialogTitle>
                        <DialogDescription>Add a vetted package to the allowed catalog.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>OS Family</Label>
                                <Select value={newIngredient.os_family} onValueChange={v => setNewIngredient({...newIngredient, os_family: v})}>
                                    <SelectTrigger className="bg-background border-muted">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="bg-secondary border-muted text-foreground">
                                        <SelectItem value="DEBIAN">DEBIAN</SelectItem>
                                        <SelectItem value="ALPINE">ALPINE</SelectItem>
                                        <SelectItem value="FEDORA">FEDORA</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label>Package Name</Label>
                                <Input 
                                    placeholder="cryptography" 
                                    value={newIngredient.name}
                                    onChange={e => setNewIngredient({...newIngredient, name: e.target.value})}
                                    className="bg-background border-muted"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Version Constraint</Label>
                            <Input 
                                placeholder=">=42.0.0" 
                                value={newIngredient.version_constraint}
                                onChange={e => setNewIngredient({...newIngredient, version_constraint: e.target.value})}
                                className="bg-background border-muted font-mono"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>SHA256 (Optional)</Label>
                            <Input 
                                placeholder="64-char hex string" 
                                value={newIngredient.sha256}
                                onChange={e => setNewIngredient({...newIngredient, sha256: e.target.value})}
                                className="bg-background border-muted font-mono text-xs"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
                        <Button 
                            disabled={!newIngredient.name || !newIngredient.version_constraint}
                            onClick={() => createMutation.mutate(newIngredient)}
                            className="bg-primary hover:bg-primary/90 text-foreground font-bold"
                        >
                            Approve Package
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <DependencyTreeModal
                open={!!selectedIngredient}
                ingredient_id={selectedIngredient?.id || ""}
                ingredient_name={selectedIngredient?.name || ""}
                onOpenChange={(open) => !open && setSelectedIngredient(null)}
            />
        </div>
    );
};

const Admin = () => {
    const { isEnterprise } = useLicence();
    const features = useFeatures();
    const { health } = useSystemHealth();
    const [joinToken, setJoinToken] = useState<string | null>(null);
    const [pubKey, setPubKey] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    // Tab scroll state
    const tabsRef = useRef<HTMLDivElement>(null);
    const [canScrollLeft, setCanScrollLeft] = useState(false);
    const [canScrollRight, setCanScrollRight] = useState(false);

    const updateScrollArrows = () => {
        const el = tabsRef.current;
        if (!el) return;
        setCanScrollLeft(el.scrollLeft > 0);
        setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
    };

    useEffect(() => {
        updateScrollArrows();
        const el = tabsRef.current;
        if (!el) return;
        const ro = new ResizeObserver(updateScrollArrows);
        ro.observe(el);
        el.addEventListener('scroll', updateScrollArrows);
        return () => { ro.disconnect(); el.removeEventListener('scroll', updateScrollArrows); };
    }, [isEnterprise]);

    const scrollTabs = (dir: 'left' | 'right') => {
        tabsRef.current?.scrollBy({ left: dir === 'left' ? -200 : 200, behavior: 'smooth' });
    };

    // Data Retention state
    const [retentionDays, setRetentionDays] = useState<number>(14);
    const [retentionEligible, setRetentionEligible] = useState<number>(0);
    const [retentionPinned, setRetentionPinned] = useState<number>(0);
    const [retentionInput, setRetentionInput] = useState<number>(14);

    useEffect(() => {
        authenticatedFetch('/api/admin/retention')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data) {
                    setRetentionDays(data.retention_days ?? 14);
                    setRetentionInput(data.retention_days ?? 14);
                    setRetentionEligible(data.eligible_count ?? 0);
                    setRetentionPinned(data.pinned_count ?? 0);
                }
            })
            .catch(() => {/* non-critical */});
    }, []);

    const handleSaveRetention = async () => {
        try {
            const res = await authenticatedFetch('/api/admin/retention', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ retention_days: retentionInput }),
            });
            if (res.ok) {
                const data = await res.json();
                setRetentionDays(data.retention_days ?? retentionInput);
                setRetentionEligible(data.eligible_count ?? retentionEligible);
                setRetentionPinned(data.pinned_count ?? retentionPinned);
                toast.success('Retention period saved');
            } else {
                toast.error('Failed to save retention period');
            }
        } catch {
            toast.error('Failed to save retention period');
        }
    };
    void retentionDays; // used via retentionInput display

    const generateToken = async () => {
        try {
            setIsGenerating(true);
            const res = await authenticatedFetch('/admin/generate-token', { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                setJoinToken(data.token);
                toast.success('Join token generated successfully');
            } else {
                toast.error('Token generation failed');
            }
        } catch (error) {
            toast.error('An error occurred during token generation');
        } finally {
            setIsGenerating(false);
        }
    };

    const uploadKey = async () => {
        try {
            setIsUploading(true);
            const res = await authenticatedFetch('/admin/upload-key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key_content: pubKey })
            });
            if (res.ok) {
                setPubKey('');
                toast.success('Public key stored successfully');
            } else {
                toast.error('Failed to store public key');
            }
        } catch (e) {
            toast.error('An error occurred during key upload');
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-foreground">Admin</h1>
                <p className="text-sm text-muted-foreground mt-1">System configuration and node onboarding.</p>
            </div>

            <MirrorHealthBanner
                isEE={isEnterprise}
                mirrorsAvailable={health?.mirrors_available ?? true}
            />

            {getUser()?.role === 'admin' && <LicenceSection />}

            <Tabs defaultValue="onboarding" className="space-y-6">
                <div className="relative flex items-center">
                    {canScrollLeft && (
                        <button
                            onClick={() => scrollTabs('left')}
                            className="absolute left-0 z-10 h-9 w-8 flex items-center justify-center bg-secondary/90 backdrop-blur border border-muted rounded-lg shadow-sm hover:bg-muted transition-colors"
                            aria-label="Scroll tabs left"
                        >
                            <ChevronLeft className="h-4 w-4 text-muted-foreground" />
                        </button>
                    )}
                <TabsList
                    ref={tabsRef}
                    className="bg-secondary border border-muted p-1 h-11 w-full justify-start overflow-x-auto scrollbar-hide"
                    style={{ scrollbarWidth: 'none' }}
                >
                    <TabsTrigger value="onboarding" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">Onboarding</TabsTrigger>
                    {features.foundry && (
                        <TabsTrigger value="smelter" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">Smelter Registry</TabsTrigger>
                    )}
                    {features.foundry && (
                        <TabsTrigger value="bom" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">BOM Explorer</TabsTrigger>
                    )}
                    {features.foundry && (
                        <TabsTrigger value="matrix" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">Tools</TabsTrigger>
                    )}
                    {features.foundry && (
                        <TabsTrigger value="vault" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">Artifact Vault</TabsTrigger>
                    )}
                    {features.foundry && (
                        <TabsTrigger value="rollouts" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">Rollouts</TabsTrigger>
                    )}
                    {features.triggers && (
                        <TabsTrigger value="automation" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">Automation</TabsTrigger>
                    )}
                    {!isEnterprise && (
                        <TabsTrigger value="enterprise" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">+ Enterprise</TabsTrigger>
                    )}
                    <TabsTrigger value="licence" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">Licence</TabsTrigger>
                    <TabsTrigger value="data" className="px-6 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-foreground font-bold">Data</TabsTrigger>
                </TabsList>
                    {canScrollRight && (
                        <button
                            onClick={() => scrollTabs('right')}
                            className="absolute right-0 z-10 h-9 w-8 flex items-center justify-center bg-secondary/90 backdrop-blur border border-muted rounded-lg shadow-sm hover:bg-muted transition-colors"
                            aria-label="Scroll tabs right"
                        >
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        </button>
                    )}
                </div>

                <TabsContent value="onboarding" className="space-y-8">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        {/* Node Onboarding */}
                        <Card className="bg-card border-muted/50 flex flex-col shadow-none">
                            <CardHeader>
                                <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                                    <Cpu className="h-5 w-5 text-primary" />
                                </div>
                                <CardTitle className="text-xl font-bold text-foreground">Node Enrollment</CardTitle>
                                <CardDescription className="text-muted-foreground">
                                    Generate secure, short-lived tokens to register new puppets into the mesh.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1 space-y-6">
                                <div className="p-4 rounded-xl bg-secondary/50 border border-muted text-sm text-muted-foreground leading-relaxed">
                                    <ShieldAlert className="h-4 w-4 text-primary inline mr-2 mb-1" />
                                    Join tokens are one-time use and expire after 24 hours. Ensure the target node has the control plane's public CA certificate installed.
                                </div>

                                {!joinToken ? (
                                    <Button
                                        onClick={generateToken}
                                        disabled={isGenerating}
                                        className="w-full h-12 bg-primary hover:bg-primary/90 text-foreground font-bold rounded-xl shadow-lg shadow-primary/10 transition-all active:scale-[0.98]"
                                    >
                                        <Zap className="mr-2 h-4 w-4 fill-current" />
                                        {isGenerating ? 'Securing...' : 'Generate Join Token'}
                                    </Button>
                                ) : (
                                    <div className="space-y-4 animate-in slide-in-from-bottom-2">
                                        <div className="space-y-2">
                                            <label className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Active Join Token</label>
                                            <div className="flex gap-2">
                                                <div className="flex-1 h-12 bg-secondary border border-primary/30 rounded-xl flex items-center px-4 font-mono text-primary font-bold overflow-hidden truncate">
                                                    {joinToken}
                                                </div>
                                                <Button
                                                    variant="outline"
                                                    className="h-12 w-12 border-muted bg-secondary p-0"
                                                    onClick={() => navigator.clipboard.writeText(joinToken || '')}
                                                    aria-label="Copy join token"
                                                >
                                                    <Copy className="h-4 w-4 text-muted-foreground" />
                                                </Button>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-green-500 font-bold uppercase tracking-tighter">
                                            <CheckCircle2 className="h-3 w-3" />
                                            Token ready for deployment
                                        </div>
                                        <Button
                                            variant="link"
                                            onClick={() => setJoinToken(null)}
                                            className="text-muted-foreground/60 p-0 h-auto text-xs hover:text-muted-foreground"
                                        >
                                            <RefreshCcw className="mr-1 h-3 w-3" />
                                            Revoke & Create New
                                        </Button>
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {/* Key Management */}
                        <Card className="bg-card border-muted/50 flex flex-col shadow-none">
                            <CardHeader>
                                <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                                    <Key className="h-5 w-5 text-primary" />
                                </div>
                                <CardTitle className="text-xl font-bold text-foreground">Security Root of Trust</CardTitle>
                                <CardDescription className="text-muted-foreground">
                                    Rotate the Master Public Key used by puppets to verify the signature of every dispatched job.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1 space-y-4">
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <label htmlFor="master-public-key" className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Master Public Key (PEM)</label>
                                        <Badge variant="outline" className="h-5 px-1.5 text-xs border-muted text-muted-foreground/60">Rotation Required</Badge>
                                    </div>
                                    <div className="relative group/pk">
                                        <Terminal className="absolute top-3 left-3 h-4 w-4 text-muted-foreground/60" />
                                        <Textarea
                                            id="master-public-key"
                                            value={pubKey}
                                            onChange={e => setPubKey(e.target.value)}
                                            placeholder="-----BEGIN PUBLIC KEY-----"
                                            className="min-h-[160px] pl-10 bg-secondary border-muted text-green-500 font-mono text-sm placeholder:text-muted-foreground/40 focus:ring-primary/20 transition-all"
                                        />
                                        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-background to-transparent pointer-events-none rounded-b-xl" />
                                    </div>
                                </div>

                                <Button
                                    onClick={uploadKey}
                                    disabled={isUploading || !pubKey}
                                    className="w-full h-12 bg-muted hover:bg-muted border border-muted text-foreground font-bold rounded-xl transition-all disabled:opacity-50"
                                >
                                    <Lock className="mr-2 h-4 w-4" />
                                    {isUploading ? 'Updating Root...' : 'Upload Root Key'}
                                </Button>

                                <p className="text-xs text-muted-foreground/60 text-center flex items-center justify-center gap-1">
                                    <AlertCircle className="h-3 w-3" />
                                    Changing this key will break validation for all existing nodes until they are updated.
                                </p>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {features.foundry && (
                    <TabsContent value="smelter">
                        <SmelterRegistryManager />
                    </TabsContent>
                )}

                {features.foundry && (
                    <TabsContent value="bom">
                        <BOMExplorer />
                    </TabsContent>
                )}

                {features.foundry && (
                    <TabsContent value="matrix">
                        <CapabilityMatrixManager />
                    </TabsContent>
                )}

                {features.foundry && (
                    <TabsContent value="vault">
                        <ArtifactVault />
                    </TabsContent>
                )}

                {features.foundry && (
                    <TabsContent value="rollouts">
                        <RolloutManager />
                    </TabsContent>
                )}

                {features.triggers && (
                    <TabsContent value="automation">
                        <TriggerManager />
                    </TabsContent>
                )}

                {!isEnterprise && (
                    <TabsContent value="enterprise" className="space-y-6">
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                            <UpgradePlaceholder
                                feature="Smelter Registry"
                                description="Vetted ingredient catalog with CVE scanning and STRICT/WARNING enforcement for Foundry builds."
                            />
                            <UpgradePlaceholder
                                feature="BOM Explorer"
                                description="Inspect the bill-of-materials for every built puppet image — packages, layers, and provenance."
                            />
                            <UpgradePlaceholder
                                feature="Tools"
                                description="Capability matrix editor for fine-grained control over what each node can execute."
                            />
                            <UpgradePlaceholder
                                feature="Artifact Vault"
                                description="Encrypted artefact storage attached to job runs — persist outputs, binaries, and reports."
                            />
                            <UpgradePlaceholder
                                feature="Rollouts"
                                description="Staged rollout manager — deploy job definitions to node cohorts with automated health gating."
                            />
                            <UpgradePlaceholder
                                feature="Automation"
                                description="Trigger chains and event-driven automation — fire jobs in response to webhooks or schedule cascades."
                            />
                        </div>
                    </TabsContent>
                )}

                <TabsContent value="licence" className="space-y-6">
                    <LicenceTabContent />
                </TabsContent>

                <TabsContent value="data" className="space-y-6">
                    <div className="bg-muted/50 rounded-lg p-6 border border-muted">
                        <h3 className="text-sm font-semibold text-foreground mb-4">Data Retention</h3>
                        <div className="space-y-3">
                            <div className="flex items-center gap-4">
                                <label className="text-sm text-muted-foreground w-40">Retention period</label>
                                <input
                                    type="number"
                                    min={1}
                                    value={retentionInput}
                                    onChange={e => setRetentionInput(parseInt(e.target.value) || 1)}
                                    className="w-24 bg-secondary border border-muted rounded px-3 py-1.5 text-sm text-foreground"
                                />
                                <span className="text-sm text-muted-foreground">days</span>
                                <button
                                    onClick={handleSaveRetention}
                                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-xs text-foreground"
                                >
                                    Save
                                </button>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Next pruning: ~{retentionEligible} records eligible · {retentionPinned} pinned (excluded)
                            </p>
                        </div>
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default Admin;
