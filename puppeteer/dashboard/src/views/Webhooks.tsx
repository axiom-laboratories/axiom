import { useState } from 'react';
import {
    Plus,
    Webhook,
    Trash2,
    Lock,
    Globe,
    Fingerprint,
    CheckCircle2,
    AlertCircle,
    Copy,
    Eye,
    EyeOff
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authenticatedFetch, getUser } from '../auth';
import { useFeatures } from '../hooks/useFeatures';
import { UpgradePlaceholder } from '../components/UpgradePlaceholder';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface WebhookData {
    id: number;
    url: string;
    events: string;
    active: boolean;
    created_at: string;
    secret: string;
}

const Webhooks = () => {
    const [showModal, setShowModal] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deleteId, setDeleteId] = useState<number | null>(null);
    const [formData, setFormData] = useState({ url: '', events: '*' });
    const [visibleSecrets, setVisibleSecrets] = useState<Record<number, boolean>>({});
    
    const user = getUser();
    const queryClient = useQueryClient();

    const { data: webhooks = [], isLoading } = useQuery<WebhookData[]>({
        queryKey: ['webhooks'],
        queryFn: async () => {
            const res = await authenticatedFetch('/webhooks');
            if (!res.ok) throw new Error("Failed to fetch webhooks");
            return await res.json();
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            const res = await authenticatedFetch(`/webhooks/${id}`, { method: 'DELETE' });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Delete failed");
            }
            return id;
        },
        onSuccess: () => {
            toast.success("Webhook removed");
            queryClient.invalidateQueries({ queryKey: ['webhooks'] });
            setShowDeleteConfirm(false);
            setDeleteId(null);
        },
        onError: (e: Error) => toast.error(`Failed to delete: ${e.message}`),
    });

    const createMutation = useMutation({
        mutationFn: async (data: typeof formData) => {
            const res = await authenticatedFetch('/webhooks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Creation failed");
            }
            return await res.json();
        },
        onSuccess: () => {
            toast.success("Webhook registered successfully");
            setShowModal(false);
            setFormData({ url: '', events: '*' });
            queryClient.invalidateQueries({ queryKey: ['webhooks'] });
        },
        onError: (e: Error) => toast.error(`Registration failed: ${e.message}`),
    });

    const handleDelete = (id: number) => {
        setDeleteId(id);
        setShowDeleteConfirm(true);
    };

    const toggleSecret = (id: number) => {
        setVisibleSecrets(prev => ({ ...prev, [id]: !prev[id] }));
    };

    const copyToClipboard = (text: string, label: string) => {
        navigator.clipboard.writeText(text);
        toast.success(`${label} copied to clipboard`);
    };

    if (user?.role !== 'admin' && user?.role !== 'operator') {
        return (
            <div className="h-[60vh] flex flex-col items-center justify-center text-center space-y-4">
                <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center">
                    <Lock className="h-6 w-6 text-destructive" />
                </div>
                <div>
                    <h3 className="text-lg font-bold text-white">Access Denied</h3>
                    <p className="text-zinc-500">You do not have permission to manage outbound webhooks.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Webhook?</AlertDialogTitle>
                        <AlertDialogDescription>
                            External notifications will no longer be sent to this URL.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => deleteId && deleteMutation.mutate(deleteId)} disabled={deleteMutation.isPending}>
                            {deleteMutation.isPending ? 'Deleting...' : 'Delete Webhook'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-white">Outbound Webhooks</h1>
                    <p className="text-sm text-zinc-500 mt-1">Real-time signed HTTP callbacks for system events.</p>
                </div>
                <Button onClick={() => setShowModal(true)} className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-6 rounded-xl">
                    <Plus className="mr-2 h-4 w-4" />
                    Register Webhook
                </Button>
            </div>

            {isLoading ? (
                <div className="grid gap-6 lg:grid-cols-2">
                    {[1, 2].map(i => (
                        <div key={i} className="h-64 rounded-2xl bg-zinc-900/50 border border-zinc-800 animate-pulse" />
                    ))}
                </div>
            ) : (
                <div className="grid gap-6 lg:grid-cols-2">
                    {webhooks.map(wh => (
                        <Card key={wh.id} className="bg-zinc-925 border-zinc-800/50 flex flex-col hover:border-primary/30 transition-all group overflow-hidden">
                            <CardHeader className="pb-4">
                                <div className="flex items-start justify-between">
                                    <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
                                        <Globe className="h-5 w-5" />
                                    </div>
                                    <Badge variant="outline" className={`text-[10px] font-bold uppercase ${wh.active ? 'border-emerald-500/20 text-emerald-500' : 'border-zinc-800 text-zinc-500'}`}>
                                        {wh.active ? 'Active' : 'Inactive'}
                                    </Badge>
                                </div>
                                <CardTitle className="mt-4 text-white font-bold truncate pr-8" title={wh.url}>{wh.url}</CardTitle>
                                <CardDescription className="flex items-center gap-2 text-xs text-zinc-500">
                                    <Webhook className="h-3 w-3" />
                                    Events: <span className="text-zinc-300">{wh.events === '*' ? 'All Events' : wh.events}</span>
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1 space-y-4">
                                <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 space-y-2">
                                    <div className="flex items-center justify-between">
                                        <Label className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Signing Secret (HMAC-SHA256)</Label>
                                        <div className="flex gap-1">
                                            <Button variant="ghost" size="icon" className="h-6 w-6 text-zinc-500 hover:text-white" onClick={() => toggleSecret(wh.id)}>
                                                {visibleSecrets[wh.id] ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                                            </Button>
                                            <Button variant="ghost" size="icon" className="h-6 w-6 text-zinc-500 hover:text-white" onClick={() => copyToClipboard(wh.secret, 'Secret')}>
                                                <Copy className="h-3 w-3" />
                                            </Button>
                                        </div>
                                    </div>
                                    <p className="font-mono text-xs break-all text-zinc-400">
                                        {visibleSecrets[wh.id] ? wh.secret : '••••••••••••••••••••••••••••••••••••••••••••••••'}
                                    </p>
                                </div>
                                <div className="flex items-center gap-4 text-[10px] text-zinc-500 font-mono">
                                    <span className="flex items-center gap-1"><Fingerprint className="h-3 w-3" /> ID: {wh.id}</span>
                                    <span>Created: {new Date(wh.created_at).toLocaleDateString()}</span>
                                </div>
                            </CardContent>
                            <CardFooter className="bg-white/[0.02] border-t border-zinc-800/50 py-3 flex items-center justify-end">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 text-zinc-500 hover:text-destructive hover:bg-destructive/10"
                                    onClick={() => handleDelete(wh.id)}
                                >
                                    <Trash2 className="mr-2 h-3.5 w-3.5" />
                                    Remove Webhook
                                </Button>
                            </CardFooter>
                        </Card>
                    ))}
                    {webhooks.length === 0 && (
                        <div className="col-span-full py-16 text-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20">
                            <Webhook className="h-12 w-12 text-zinc-800 mx-auto mb-4" />
                            <h3 className="text-zinc-400 font-medium">No external integrations</h3>
                            <p className="text-zinc-600 text-sm max-w-xs mx-auto">Register a URL to start receiving real-time signed event notifications.</p>
                        </div>
                    )}
                </div>
            )}

            <Dialog open={showModal} onOpenChange={setShowModal}>
                <DialogContent className="bg-zinc-925 border-zinc-800 text-white sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle>Register Webhook</DialogTitle>
                        <DialogDescription className="text-zinc-500">
                            Configure an external endpoint to receive system events.
                        </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(formData); }} className="space-y-6 pt-4">
                        <div className="space-y-2">
                            <Label className="text-zinc-400 font-bold uppercase text-xs tracking-widest">Payload URL</Label>
                            <Input
                                placeholder="https://api.your-system.com/webhooks/mop"
                                className="bg-zinc-900 border-zinc-800 h-11"
                                value={formData.url}
                                onChange={e => setFormData({ ...formData, url: e.target.value })}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-zinc-400 font-bold uppercase text-xs tracking-widest">Event Subscriptions</Label>
                            <Input
                                placeholder="* (All) or job:completed, alert:new"
                                className="bg-zinc-900 border-zinc-800 h-11"
                                value={formData.events}
                                onChange={e => setFormData({ ...formData, events: e.target.value })}
                                required
                            />
                            <p className="text-[10px] text-zinc-500">Comma separated event types. Use * for all events.</p>
                        </div>
                        <div className="p-4 rounded-xl bg-primary/5 border border-primary/10 flex gap-3">
                            <Lock className="h-5 w-5 text-primary shrink-0" />
                            <p className="text-xs text-zinc-400 leading-normal">
                                <span className="text-white font-bold">Security Note:</span> A unique signing secret will be generated. Your system should verify the <code className="text-primary">X-MOP-Signature</code> header.
                            </p>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowModal(false)} className="border-zinc-800">Cancel</Button>
                            <Button type="submit" disabled={createMutation.isPending} className="bg-primary hover:bg-primary/90 text-white font-bold">
                                {createMutation.isPending ? 'Registering...' : 'Establish Integration'}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
};

const WebhooksWithFeatureCheck = () => {
    const features = useFeatures();
    if (!features.webhooks) {
        return <UpgradePlaceholder feature="Webhooks" description="Outbound event delivery with HMAC signing, retry logic, and per-event filtering for integration with external systems." />;
    }
    return <Webhooks />;
};

export default WebhooksWithFeatureCheck;
