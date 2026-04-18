import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
    Bot,
    Plus,
    Trash2,
    Copy,
    RotateCcw,
    MoreHorizontal,
    Shield,
    Pencil,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Eye,
    EyeOff
} from 'lucide-react';

import { authenticatedFetch, getUser } from '../auth';
import { useFeatures } from '../hooks/useFeatures';
import { UpgradePlaceholder } from '../components/UpgradePlaceholder';

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription
} from '@/components/ui/dialog';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle
} from '@/components/ui/alert-dialog';
import {
    Select,
    SelectTrigger,
    SelectValue,
    SelectContent,
    SelectItem
} from '@/components/ui/select';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { Textarea } from '@/components/ui/textarea';

interface ServicePrincipal {
    id: string;
    name: string;
    description: string | null;
    role: string;
    client_id: string;
    is_active: boolean;
    created_by: string;
    last_used_at: string | null;
    expires_at: string | null;
    created_at: string;
}

interface NewServicePrincipalResponse extends ServicePrincipal {
    client_secret: string;
}

const ServicePrincipals: React.FC = () => {
    const user = getUser();
    const queryClient = useQueryClient();

    // Dialog States
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
    const [isCredentialsDialogOpen, setIsCredentialsDialogOpen] = useState(false);
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
    const [isRotateAlertDialogOpen, setIsRotateAlertDialogOpen] = useState(false);
    const [isDeleteAlertDialogOpen, setIsDeleteAlertDialogOpen] = useState(false);

    // Form States
    const [newSP, setNewSP] = useState({
        name: '',
        description: '',
        role: 'operator',
        expires_in_days: ''
    });
    const [createdCredentials, setCreatedCredentials] = useState<{ client_id: string; client_secret: string } | null>(null);
    const [editingSP, setEditingSP] = useState<ServicePrincipal | null>(null);
    const [selectedSPId, setSelectedSPId] = useState<string | null>(null);

    // Queries
    const { data: servicePrincipals, isLoading } = useQuery<ServicePrincipal[]>({
        queryKey: ['service-principals'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/admin/service-principals');
            if (!res.ok) throw new Error('Failed to fetch service principals');
            return res.json();
        },
        enabled: user?.role === 'admin'
    });

    // Mutations
    const createMutation = useMutation({
        mutationFn: async (data: any) => {
            const res = await authenticatedFetch('/api/admin/service-principals', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...data,
                    expires_in_days: data.expires_in_days ? parseInt(data.expires_in_days) : null
                })
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to create service principal');
            }
            return res.json();
        },
        onSuccess: (data: NewServicePrincipalResponse) => {
            queryClient.invalidateQueries({ queryKey: ['service-principals'] });
            setCreatedCredentials({
                client_id: data.client_id,
                client_secret: data.client_secret
            });
            setIsCreateDialogOpen(false);
            setIsCredentialsDialogOpen(true);
            toast.success('Service principal created successfully');
            setNewSP({ name: '', description: '', role: 'operator', expires_in_days: '' });
        },
        onError: (error: Error) => {
            toast.error(error.message);
        }
    });

    const updateMutation = useMutation({
        mutationFn: async ({ id, data }: { id: string; data: any }) => {
            const res = await authenticatedFetch(`/api/admin/service-principals/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!res.ok) throw new Error('Failed to update service principal');
            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['service-principals'] });
            setIsEditDialogOpen(false);
            setEditingSP(null);
            toast.success('Service principal updated');
        }
    });

    const rotateMutation = useMutation({
        mutationFn: async (id: string) => {
            const res = await authenticatedFetch(`/api/admin/service-principals/${id}/rotate-secret`, {
                method: 'POST'
            });
            if (!res.ok) throw new Error('Failed to rotate secret');
            return res.json();
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['service-principals'] });
            setCreatedCredentials(data);
            setIsCredentialsDialogOpen(true);
            toast.success('Secret rotated successfully');
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            const res = await authenticatedFetch(`/api/admin/service-principals/${id}`, {
                method: 'DELETE'
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to delete service principal');
            }
            return true;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['service-principals'] });
            toast.success('Service principal deleted');
        },
        onError: (error: Error) => {
            toast.error(error.message);
        }
    });

    if (user?.role !== 'admin') {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Card className="w-full max-w-md border-muted bg-background">
                    <CardHeader>
                        <div className="flex items-center gap-2 text-red-500 mb-2">
                            <Shield className="h-6 w-6" />
                            <CardTitle>Access Denied</CardTitle>
                        </div>
                        <CardDescription className="text-muted-foreground">
                            You do not have the required permissions to manage service principals.
                            Please contact an administrator if you believe this is an error.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button variant="outline" className="w-full border-muted hover:bg-muted text-foreground" onClick={() => window.history.back()}>
                            Go Back
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const copyToClipboard = (text: string, label: string) => {
        navigator.clipboard.writeText(text);
        toast.success(`${label} copied to clipboard`);
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return 'Never';
        return new Date(dateStr).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const formatRelativeTime = (dateStr: string | null) => {
        if (!dateStr) return 'Never';
        const date = new Date(dateStr);
        const now = new Date();
        const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
                        <Bot className="h-8 w-8 text-blue-500" />
                        Service Principals
                    </h1>
                    <p className="text-muted-foreground">
                        Machine-to-machine credentials for CI/CD and automation
                    </p>
                </div>
                <Button 
                    onClick={() => setIsCreateDialogOpen(true)}
                    className="bg-blue-600 hover:bg-blue-700 text-foreground"
                >
                    <Plus className="mr-2 h-4 w-4" />
                    Create Service Principal
                </Button>
            </div>

            {/* Main Content */}
            <Card className="border-muted bg-card overflow-hidden">
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-muted bg-muted/50">
                                    <th className="px-6 py-4 text-sm font-medium text-muted-foreground">Name</th>
                                    <th className="px-6 py-4 text-sm font-medium text-muted-foreground">Client ID</th>
                                    <th className="px-6 py-4 text-sm font-medium text-muted-foreground">Role</th>
                                    <th className="px-6 py-4 text-sm font-medium text-muted-foreground">Status</th>
                                    <th className="px-6 py-4 text-sm font-medium text-muted-foreground">Last Used</th>
                                    <th className="px-6 py-4 text-sm font-medium text-muted-foreground">Expires</th>
                                    <th className="px-6 py-4 text-sm font-medium text-muted-foreground text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-muted">
                                {isLoading ? (
                                    [...Array(3)].map((_, i) => (
                                        <tr key={i} className="animate-pulse">
                                            <td colSpan={7} className="px-6 py-8 text-center bg-background/20" />
                                        </tr>
                                    ))
                                ) : servicePrincipals?.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="px-6 py-12 text-center text-muted-foreground">
                                            No service principals found. Create one to get started.
                                        </td>
                                    </tr>
                                ) : (
                                    servicePrincipals?.map((sp) => (
                                        <tr key={sp.id} className="hover:bg-background/50 transition-colors group">
                                            <td className="px-6 py-4">
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-foreground">{sp.name}</span>
                                                    {sp.description && (
                                                        <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                                                            {sp.description}
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    <code className="text-xs font-mono text-muted-foreground bg-background px-1.5 py-0.5 rounded border border-muted">
                                                        {sp.client_id.substring(0, 12)}...
                                                    </code>
                                                    <Button 
                                                        variant="ghost" 
                                                        size="icon" 
                                                        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                                                        onClick={() => copyToClipboard(sp.client_id, 'Client ID')}
                                                    >
                                                        <Copy className="h-3 w-3" />
                                                    </Button>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <Badge
                                                    variant="outline"
                                                    className={
                                                        sp.role === 'admin' ? 'border-red-500/50 text-red-500' :
                                                        sp.role === 'operator' ? 'border-blue-500/50 text-blue-500' :
                                                        'border-muted-foreground/50 text-muted-foreground'
                                                    }
                                                >
                                                    {sp.role}
                                                </Badge>
                                            </td>
                                            <td className="px-6 py-4">
                                                {sp.is_active ? (
                                                    <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hover:bg-emerald-500/10">
                                                        Active
                                                    </Badge>
                                                ) : (
                                                    <Badge className="bg-red-500/10 text-red-500 border-red-500/20 hover:bg-red-500/10">
                                                        Disabled
                                                    </Badge>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-muted-foreground">
                                                {formatRelativeTime(sp.last_used_at)}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-muted-foreground">
                                                {formatDate(sp.expires_at)}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild>
                                                        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
                                                            <MoreHorizontal className="h-4 w-4" />
                                                        </Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end" className="bg-card border-muted text-foreground">
                                                        <DropdownMenuItem 
                                                            onClick={() => {
                                                                setEditingSP(sp);
                                                                setIsEditDialogOpen(true);
                                                            }}
                                                            className="focus:bg-muted cursor-pointer"
                                                        >
                                                            <Pencil className="mr-2 h-4 w-4" /> Edit
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem 
                                                            onClick={() => {
                                                                setSelectedSPId(sp.id);
                                                                setIsRotateAlertDialogOpen(true);
                                                            }}
                                                            className="focus:bg-muted text-amber-500 cursor-pointer"
                                                        >
                                                            <RotateCcw className="mr-2 h-4 w-4" /> Rotate Secret
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem 
                                                            onClick={() => {
                                                                setSelectedSPId(sp.id);
                                                                setIsDeleteAlertDialogOpen(true);
                                                            }}
                                                            className="focus:bg-muted text-red-500 cursor-pointer"
                                                        >
                                                            <Trash2 className="mr-2 h-4 w-4" /> Delete
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>

            {/* Create Dialog */}
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
                <DialogContent className="bg-card border-muted text-foreground">
                    <DialogHeader>
                        <DialogTitle>Create Service Principal</DialogTitle>
                        <DialogDescription className="text-muted-foreground">
                            Create a new automated identity for API access.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Name</Label>
                            <Input 
                                id="name" 
                                placeholder="e.g. CI/CD Pipeline"
                                value={newSP.name}
                                onChange={(e) => setNewSP({ ...newSP, name: e.target.value })}
                                className="bg-background border-muted"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="description">Description (Optional)</Label>
                            <Textarea 
                                id="description" 
                                placeholder="Purpose of this service principal"
                                value={newSP.description}
                                onChange={(e) => setNewSP({ ...newSP, description: e.target.value })}
                                className="bg-background border-muted"
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="role">Role</Label>
                                <Select 
                                    value={newSP.role} 
                                    onValueChange={(v) => setNewSP({ ...newSP, role: v })}
                                >
                                    <SelectTrigger id="role" className="bg-background border-muted">
                                        <SelectValue placeholder="Select role" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-card border-muted text-foreground">
                                        <SelectItem value="viewer">Viewer</SelectItem>
                                        <SelectItem value="operator">Operator</SelectItem>
                                        <SelectItem value="admin">Admin</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="expires">Expires (Days)</Label>
                                <Input 
                                    id="expires" 
                                    type="number"
                                    placeholder="Never"
                                    value={newSP.expires_in_days}
                                    onChange={(e) => setNewSP({ ...newSP, expires_in_days: e.target.value })}
                                    className="bg-background border-muted"
                                />
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)} className="border-muted text-foreground">
                            Cancel
                        </Button>
                        <Button 
                            disabled={!newSP.name || createMutation.isPending}
                            onClick={() => createMutation.mutate(newSP)}
                            className="bg-blue-600 hover:bg-blue-700 text-foreground"
                        >
                            {createMutation.isPending ? 'Creating...' : 'Create Principal'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Credentials Success Dialog */}
            <Dialog open={isCredentialsDialogOpen} onOpenChange={setIsCredentialsDialogOpen}>
                <DialogContent className="bg-card border-muted text-foreground max-w-lg">
                    <DialogHeader>
                        <div className="flex items-center gap-2 text-emerald-500 mb-2">
                            <CheckCircle2 className="h-6 w-6" />
                            <DialogTitle>Credentials Generated</DialogTitle>
                        </div>
                        <DialogDescription className="text-muted-foreground">
                            Copy these credentials now. For security, the secret will **not** be shown again.
                        </DialogDescription>
                    </DialogHeader>
                    
                    <div className="space-y-4 py-4">
                        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex gap-3">
                            <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
                            <p className="text-xs text-amber-200/80">
                                Store these in a secure vault like HashiCorp Vault, GitHub Secrets, or 1Password. 
                                Loss of the secret requires a rotation.
                            </p>
                        </div>

                        <div className="space-y-2">
                            <Label className="text-muted-foreground">Client ID</Label>
                            <div className="flex gap-2">
                                <Input 
                                    readOnly 
                                    value={createdCredentials?.client_id || ''} 
                                    className="bg-background border-muted font-mono text-xs" 
                                />
                                <Button size="icon" variant="outline" onClick={() => copyToClipboard(createdCredentials?.client_id || '', 'Client ID')}>
                                    <Copy className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label className="text-muted-foreground">Client Secret</Label>
                            <div className="flex gap-2">
                                <Input 
                                    readOnly 
                                    type="password"
                                    value={createdCredentials?.client_secret || ''} 
                                    className="bg-background border-muted font-mono text-xs" 
                                />
                                <Button size="icon" variant="outline" onClick={() => copyToClipboard(createdCredentials?.client_secret || '', 'Client Secret')}>
                                    <Copy className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    </div>
                    
                    <DialogFooter>
                        <Button 
                            className="w-full bg-foreground hover:bg-white text-background font-bold"
                            onClick={() => setIsCredentialsDialogOpen(false)}
                        >
                            I have saved the credentials
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Edit Dialog */}
            <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
                <DialogContent className="bg-card border-muted text-foreground">
                    <DialogHeader>
                        <DialogTitle>Edit Service Principal</DialogTitle>
                    </DialogHeader>
                    {editingSP && (
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="edit-name">Name</Label>
                                <Input 
                                    id="edit-name" 
                                    value={editingSP.name}
                                    onChange={(e) => setEditingSP({ ...editingSP, name: e.target.value })}
                                    className="bg-background border-muted"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="edit-description">Description</Label>
                                <Textarea 
                                    id="edit-description" 
                                    value={editingSP.description || ''}
                                    onChange={(e) => setEditingSP({ ...editingSP, description: e.target.value })}
                                    className="bg-background border-muted"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="edit-role">Role</Label>
                                    <Select 
                                        value={editingSP.role} 
                                        onValueChange={(v) => setEditingSP({ ...editingSP, role: v })}
                                    >
                                        <SelectTrigger id="edit-role" className="bg-background border-muted">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-card border-muted text-foreground">
                                            <SelectItem value="viewer">Viewer</SelectItem>
                                            <SelectItem value="operator">Operator</SelectItem>
                                            <SelectItem value="admin">Admin</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Status</Label>
                                    <Button
                                        variant={editingSP.is_active ? "outline" : "destructive"}
                                        className={`w-full ${editingSP.is_active ? 'border-emerald-500/50 text-emerald-500 hover:bg-emerald-500/10' : ''}`}
                                        onClick={() => setEditingSP({ ...editingSP, is_active: !editingSP.is_active })}
                                    >
                                        {editingSP.is_active ? 'Active' : 'Disabled'}
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsEditDialogOpen(false)} className="border-muted">
                            Cancel
                        </Button>
                        <Button 
                            disabled={updateMutation.isPending}
                            onClick={() => updateMutation.mutate({ 
                                id: editingSP!.id, 
                                data: {
                                    name: editingSP!.name,
                                    description: editingSP!.description,
                                    role: editingSP!.role,
                                    is_active: editingSP!.is_active
                                }
                            })}
                            className="bg-blue-600 hover:bg-blue-700 text-foreground"
                        >
                            Save Changes
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Rotate Secret Confirmation */}
            <AlertDialog open={isRotateAlertDialogOpen} onOpenChange={setIsRotateAlertDialogOpen}>
                <AlertDialogContent className="bg-card border-muted text-foreground">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Rotate Client Secret?</AlertDialogTitle>
                        <AlertDialogDescription className="text-muted-foreground">
                            This will immediately invalidate the current secret. Any applications using it will lose access until updated. This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel className="bg-muted border-muted text-foreground hover:bg-muted">Cancel</AlertDialogCancel>
                        <AlertDialogAction 
                            onClick={() => selectedSPId && rotateMutation.mutate(selectedSPId)}
                            className="bg-amber-600 hover:bg-amber-700 text-foreground"
                        >
                            Rotate Secret
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Delete Confirmation */}
            <AlertDialog open={isDeleteAlertDialogOpen} onOpenChange={setIsDeleteAlertDialogOpen}>
                <AlertDialogContent className="bg-card border-muted text-foreground">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Service Principal?</AlertDialogTitle>
                        <AlertDialogDescription className="text-muted-foreground">
                            This will permanently delete the identity and all its credentials. Any automation using this principal will fail.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel className="bg-muted border-muted text-foreground hover:bg-muted">Cancel</AlertDialogCancel>
                        <AlertDialogAction 
                            onClick={() => selectedSPId && deleteMutation.mutate(selectedSPId)}
                            className="bg-red-600 hover:bg-red-700 text-foreground"
                        >
                            Delete Permanently
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
};

const ServicePrincipalsWithFeatureCheck = () => {
    const features = useFeatures();
    if (!features.service_principals) {
        return <UpgradePlaceholder feature="Service Principals" description="Machine-to-machine authentication with client credentials for CI/CD pipeline integration." />;
    }
    return <ServicePrincipals />;
};

export default ServicePrincipalsWithFeatureCheck;
