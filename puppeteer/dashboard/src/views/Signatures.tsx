import { useState } from 'react';
import {
    Plus,
    Shield,
    Key,
    Trash2,
    User,
    ExternalLink,
    Lock,
    ShieldCheck,
    AlertCircle
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
import { Textarea } from '@/components/ui/textarea';
import { authenticatedFetch, getUser } from '../auth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface Signature {
    id: string;
    name: string;
    public_key: string;
    uploaded_by: string;
}

const Signatures = () => {
    const [showModal, setShowModal] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [formData, setFormData] = useState({ name: '', public_key: '' });
    const user = getUser();
    const queryClient = useQueryClient();

    const { data: signatures = [], isLoading } = useQuery<Signature[]>({
        queryKey: ['signatures'],
        queryFn: async () => {
            const res = await authenticatedFetch('/signatures');
            if (!res.ok) throw new Error("Failed to fetch signatures");
            return await res.json();
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            const res = await authenticatedFetch(`/signatures/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error("Delete failed");
            return id;
        },
        onSuccess: () => {
            toast.success("Signing key removed from registry");
            queryClient.invalidateQueries({ queryKey: ['signatures'] });
            setShowDeleteConfirm(false);
            setDeleteId(null);
        },
        onError: (e: Error) => toast.error(`Failed to delete key: ${e.message}`),
    });

    const uploadMutation = useMutation({
        mutationFn: async (data: typeof formData) => {
            const res = await authenticatedFetch('/signatures', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Upload failed");
            }
            return await res.json();
        },
        onSuccess: () => {
            toast.success("Public key stored successfully");
            setShowModal(false);
            setFormData({ name: '', public_key: '' });
            queryClient.invalidateQueries({ queryKey: ['signatures'] });
        },
        onError: (e: Error) => toast.error(`Registration failed: ${e.message}`),
    });

    const handleDelete = (id: string) => {
        setDeleteId(id);
        setShowDeleteConfirm(true);
    };

    const handleConfirmDelete = () => {
        if (deleteId) deleteMutation.mutate(deleteId);
    };

    const handleUpload = (e: React.FormEvent) => {
        e.preventDefault();
        uploadMutation.mutate(formData);
    };

    if (user?.role !== 'admin') {
        return (
            <div className="h-[60vh] flex flex-col items-center justify-center text-center space-y-4">
                <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center">
                    <Lock className="h-6 w-6 text-destructive" />
                </div>
                <div>
                    <h3 className="text-lg font-bold text-white">Access Denied</h3>
                    <p className="text-zinc-500">Only system administrators can manage signing keys.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Signing Key?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure? Jobs using this key will fail validation. This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleConfirmDelete} disabled={deleteMutation.isPending}>
                            {deleteMutation.isPending ? 'Deleting...' : 'Delete Key'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-white">Signing Keys</h1>
                    <p className="text-sm text-zinc-500 mt-1">Ed25519 public keys for job verification.</p>
                </div>
                <Button onClick={() => setShowModal(true)} className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-6 rounded-xl">
                    <Plus className="mr-2 h-4 w-4" />
                    Register Trusted Key
                </Button>
            </div>

            {isLoading ? (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-48 rounded-2xl bg-zinc-900/50 border border-zinc-800 animate-pulse" />
                    ))}
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {signatures.map(sig => (
                        <Card key={sig.id} className="bg-zinc-925 border-zinc-800/50 flex flex-col hover:border-primary/30 transition-all group">
                            <CardHeader className="pb-4">
                                <div className="flex items-start justify-between">
                                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                                        <ShieldCheck className="h-5 w-5" />
                                    </div>
                                    <Badge variant="outline" className="text-xs font-mono border-zinc-800 text-zinc-500 uppercase">
                                        Active
                                    </Badge>
                                </div>
                                <CardTitle className="mt-4 text-white font-bold">{sig.name}</CardTitle>
                                <CardDescription className="flex items-center gap-1 text-xs text-zinc-500 font-mono">
                                    UID: {sig.id.substring(0, 8)}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1">
                                <div className="relative group/key">
                                    <Textarea
                                        readOnly
                                        value={sig.public_key}
                                        className="h-24 bg-zinc-900 border-zinc-800 text-xs font-mono text-zinc-400 resize-none focus-visible:ring-0"
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-zinc-900/80 to-transparent flex items-end justify-center pb-2 opacity-0 group-hover/key:opacity-100 transition-opacity">
                                        <Button variant="ghost" size="sm" className="h-7 text-xs text-white hover:bg-white/10 uppercase tracking-widest font-bold">
                                            <ExternalLink className="mr-1 h-3 w-3" />
                                            View Full PEM
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                            <CardFooter className="bg-white/[0.02] border-t border-zinc-800/50 py-3 flex items-center justify-between">
                                <div className="flex items-center gap-2 text-xs text-zinc-500">
                                    <User className="h-3 w-3" />
                                    {sig.uploaded_by}
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 text-zinc-600 hover:text-destructive hover:bg-destructive/10"
                                    onClick={() => handleDelete(sig.id)}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </CardFooter>
                        </Card>
                    ))}
                    {signatures.length === 0 && (
                        <div className="col-span-full py-12 text-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20">
                            <Key className="h-12 w-12 text-zinc-800 mx-auto mb-4" />
                            <h3 className="text-zinc-400 font-medium">No trust established</h3>
                            <p className="text-zinc-600 text-sm">Upload a public key to begin validating puppet jobs.</p>
                        </div>
                    )}
                </div>
            )}

            <Dialog open={showModal} onOpenChange={setShowModal}>
                <DialogContent className="bg-zinc-925 border-zinc-800 text-white sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle>Register Trusted Key</DialogTitle>
                        <DialogDescription className="text-zinc-500">
                            Provide a PEM-formatted public key to enable code signing validation.
                        </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleUpload} className="space-y-6 pt-4">
                        <div className="space-y-2">
                            <Label className="text-zinc-400 font-bold uppercase text-xs tracking-widest">Key Identifier</Label>
                            <Input
                                placeholder="e.g. Master Build Pipeline"
                                className="bg-zinc-900 border-zinc-800 h-11"
                                value={formData.name}
                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-zinc-400 font-bold uppercase text-xs tracking-widest">Public Key Content (PEM)</Label>
                            <div className="relative">
                                <div className="absolute top-3 left-3 h-4 w-4 text-zinc-600">
                                    <Shield className="h-full w-full" />
                                </div>
                                <Textarea
                                    placeholder="-----BEGIN PUBLIC KEY-----"
                                    className="bg-zinc-900 border-zinc-800 min-h-[200px] pl-10 pt-3 font-mono text-sm text-green-500 placeholder:text-zinc-700"
                                    value={formData.public_key}
                                    onChange={e => setFormData({ ...formData, public_key: e.target.value })}
                                    required
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowModal(false)} className="border-zinc-800">Cancel</Button>
                            <Button type="submit" disabled={uploadMutation.isPending} className="bg-primary hover:bg-primary/90 text-white font-bold">
                                {uploadMutation.isPending ? 'Verifying...' : 'Establish Trust'}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default Signatures;
