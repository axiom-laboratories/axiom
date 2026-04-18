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
    BookOpen,
    Copy,
    CheckCheck,
    Terminal
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

const KEYGEN_CMD = `python3 - <<'EOF'
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

key = Ed25519PrivateKey.generate()

with open("signing.key", "wb") as f:
    f.write(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    ))

with open("verification.key", "wb") as f:
    f.write(key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    ))

print("Done. Upload verification.key here, keep signing.key private.")
EOF`;

const SIGN_CMD = `python3 - <<'EOF'
from cryptography.hazmat.primitives import serialization
import base64

YOUR_SCRIPT = "YOUR_SCRIPT.py"

with open("signing.key", "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

script_content = open(YOUR_SCRIPT, "r").read()
sig = private_key.sign(script_content.encode("utf-8"))
print(base64.b64encode(sig).decode())
EOF`;

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    return (
        <button
            onClick={handleCopy}
            className="absolute top-2 right-2 p-1.5 rounded bg-muted hover:bg-muted text-foreground transition-colors"
            title="Copy to clipboard"
        >
            {copied ? <CheckCheck className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
    );
}

const Signatures = () => {
    const [showModal, setShowModal] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [showKeygenGuide, setShowKeygenGuide] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [formData, setFormData] = useState({ name: '', public_key: '' });
    const user = getUser();
    const queryClient = useQueryClient();

    const { data: signatures = [], isLoading } = useQuery<Signature[]>({
        queryKey: ['signatures'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/signatures');
            if (!res.ok) throw new Error("Failed to fetch signatures");
            return await res.json();
        }
    });

    const noKeys = !isLoading && signatures.length === 0;

    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            const res = await authenticatedFetch(`/api/signatures/${id}`, { method: 'DELETE' });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Delete failed");
            }
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
            const res = await authenticatedFetch('/api/signatures', {
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
                    <h3 className="text-lg font-bold text-foreground">Access Denied</h3>
                    <p className="text-muted-foreground">Only system administrators can manage signing keys.</p>
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
                    <h1 className="text-2xl font-bold tracking-tight text-foreground">Signing Keys</h1>
                    <p className="text-sm text-muted-foreground mt-1">Ed25519 public keys for job verification.</p>
                </div>
                <Button onClick={() => setShowModal(true)} className="bg-primary hover:bg-primary/90 text-foreground font-bold h-11 px-6 rounded-xl">
                    <Plus className="mr-2 h-4 w-4" />
                    Register Trusted Key
                </Button>
            </div>

            {noKeys && (
                <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4 flex flex-col md:flex-row md:items-center gap-4">
                    <div className="flex items-start gap-3 flex-1">
                        <div className="mt-0.5 p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 shrink-0">
                            <BookOpen className="h-4 w-4" />
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-indigo-300">Getting Started — No signing keys registered</p>
                            <p className="text-xs text-muted-foreground mt-1">
                                All jobs must be signed before dispatch. Generate an Ed25519 keypair, upload the public key here,
                                then sign your scripts with the private key before submitting.
                            </p>
                        </div>
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        className="border-indigo-500/40 text-indigo-300 hover:bg-indigo-500/10 shrink-0 font-bold"
                        onClick={() => setShowKeygenGuide(true)}
                    >
                        <Terminal className="mr-2 h-3.5 w-3.5" />
                        How to generate a key
                    </Button>
                </div>
            )}

            {isLoading ? (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-48 rounded-2xl bg-secondary/50 border border-muted animate-pulse" />
                    ))}
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {signatures.map(sig => (
                        <Card key={sig.id} className="bg-card border-muted/50 flex flex-col hover:border-primary/30 transition-all group">
                            <CardHeader className="pb-4">
                                <div className="flex items-start justify-between">
                                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                                        <ShieldCheck className="h-5 w-5" />
                                    </div>
                                    <Badge variant="outline" className="text-xs font-mono border-muted text-muted-foreground uppercase">
                                        Active
                                    </Badge>
                                </div>
                                <CardTitle className="mt-4 text-foreground font-bold">{sig.name}</CardTitle>
                                <CardDescription className="flex items-center gap-1 text-xs text-muted-foreground font-mono">
                                    UID: {sig.id.substring(0, 8)}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1">
                                <div className="relative group/key">
                                    <Textarea
                                        readOnly
                                        value={sig.public_key}
                                        className="h-24 bg-secondary border-muted text-xs font-mono text-muted-foreground resize-none focus-visible:ring-0"
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent flex items-end justify-center pb-2 opacity-0 group-hover/key:opacity-100 transition-opacity">
                                        <Button variant="ghost" size="sm" className="h-7 text-xs text-foreground hover:bg-white/10 uppercase tracking-widest font-bold">
                                            <ExternalLink className="mr-1 h-3 w-3" />
                                            View Full PEM
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                            <CardFooter className="bg-white/[0.02] border-t border-muted/50 py-3 flex items-center justify-between">
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <User className="h-3 w-3" />
                                    {sig.uploaded_by}
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 text-muted-foreground/60 hover:text-destructive hover:bg-destructive/10"
                                    onClick={() => handleDelete(sig.id)}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </CardFooter>
                        </Card>
                    ))}
                    {signatures.length === 0 && (
                        <div className="col-span-full py-12 text-center rounded-2xl border border-dashed border-muted bg-secondary/20">
                            <Key className="h-12 w-12 text-muted mx-auto mb-4" />
                            <h3 className="text-muted-foreground font-medium">No trust established</h3>
                            <p className="text-muted-foreground/60 text-sm">Upload a public key to begin validating puppet jobs.</p>
                        </div>
                    )}
                </div>
            )}

            {/* Key generation guide modal */}
            <Dialog open={showKeygenGuide} onOpenChange={setShowKeygenGuide}>
                <DialogContent className="bg-card border-muted text-foreground sm:max-w-[620px]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Terminal className="h-5 w-5 text-indigo-400" />
                            Generate a signing keypair
                        </DialogTitle>
                        <DialogDescription className="text-muted-foreground">
                            Three steps: generate a keypair, register the public key here, sign your scripts before dispatch.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-5 pt-2">
                        <div>
                            <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">Step 1 — Generate keypair (run once, keep signing.key private)</p>
                            <div className="relative">
                                <pre className="bg-secondary border border-muted rounded-lg p-3 text-xs font-mono text-foreground overflow-x-auto whitespace-pre">{KEYGEN_CMD}</pre>
                                <CopyButton text={KEYGEN_CMD} />
                            </div>
                        </div>
                        <div>
                            <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">Step 2 — Register the public key</p>
                            <p className="text-xs text-muted-foreground">
                                Copy the contents of <code className="font-mono text-indigo-300 bg-muted px-1 py-0.5 rounded">verification.key</code> and
                                click <strong className="text-foreground/80">Register Trusted Key</strong> above to upload it.
                            </p>
                        </div>
                        <div>
                            <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">Step 3 — Sign a script before dispatch</p>
                            <div className="relative">
                                <pre className="bg-secondary border border-muted rounded-lg p-3 text-xs font-mono text-foreground overflow-x-auto whitespace-pre">{SIGN_CMD}</pre>
                                <CopyButton text={SIGN_CMD} />
                            </div>
                            <p className="text-xs text-muted-foreground mt-2">
                                Paste the printed base64 string into the <strong className="text-foreground">Signature</strong> field when dispatching a job.
                            </p>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowKeygenGuide(false)} className="border-muted">Close</Button>
                        <Button onClick={() => { setShowKeygenGuide(false); setShowModal(true); }} className="bg-primary hover:bg-primary/90 text-foreground font-bold">
                            Register Key Now
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={showModal} onOpenChange={setShowModal}>
                <DialogContent className="bg-card border-muted text-foreground sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle>Register Trusted Key</DialogTitle>
                        <DialogDescription className="text-muted-foreground">
                            Provide a PEM-formatted public key to enable code signing validation.
                        </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleUpload} className="space-y-6 pt-4">
                        <div className="space-y-2">
                            <Label className="text-muted-foreground font-bold uppercase text-xs tracking-widest">Key Identifier</Label>
                            <Input
                                placeholder="e.g. Master Build Pipeline"
                                className="bg-secondary border-muted h-11"
                                value={formData.name}
                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-muted-foreground font-bold uppercase text-xs tracking-widest">Public Key Content (PEM)</Label>
                            <div className="relative">
                                <div className="absolute top-3 left-3 h-4 w-4 text-muted-foreground/60">
                                    <Shield className="h-full w-full" />
                                </div>
                                <Textarea
                                    placeholder="-----BEGIN PUBLIC KEY-----"
                                    className="bg-secondary border-muted min-h-[200px] pl-10 pt-3 font-mono text-sm text-green-500 placeholder:text-muted-foreground/40"
                                    value={formData.public_key}
                                    onChange={e => setFormData({ ...formData, public_key: e.target.value })}
                                    required
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowModal(false)} className="border-muted">Cancel</Button>
                            <Button type="submit" disabled={uploadMutation.isPending} className="bg-primary hover:bg-primary/90 text-foreground font-bold">
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
