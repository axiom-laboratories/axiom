import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Network, Plus, Trash2, Save, X } from 'lucide-react';
import { 
    Dialog, 
    DialogContent, 
    DialogHeader, 
    DialogTitle, 
    DialogFooter,
    DialogDescription
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authenticatedFetch } from '../auth';

interface NetworkMount {
    name: string;
    remote_path: string;
}

interface ManageMountsModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

const ManageMountsModal = ({ open, onOpenChange }: ManageMountsModalProps) => {
    const [mounts, setMounts] = useState<NetworkMount[]>([]);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (open) {
            fetchMounts();
        }
    }, [open]);

    const fetchMounts = async () => {
        setLoading(true);
        try {
            const res = await authenticatedFetch('/config/mounts');
            if (res.ok) {
                const data = await res.json();
                setMounts(data);
            }
        } catch (e) {
            toast.error('Failed to fetch network mounts');
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setMounts([...mounts, { name: '', remote_path: '' }]);
    };

    const handleRemove = (index: number) => {
        setMounts(mounts.filter((_, i) => i !== index));
    };

    const handleChange = (index: number, field: keyof NetworkMount, value: string) => {
        const nextMounts = [...mounts];
        nextMounts[index] = { ...nextMounts[index], [field]: value };
        setMounts(nextMounts);
    };

    const handleSave = async () => {
        // Simple validation
        if (mounts.some(m => !m.name || !m.remote_path)) {
            toast.error('All mounts must have a name and path');
            return;
        }

        setSaving(true);
        try {
            const res = await authenticatedFetch('/config/mounts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mounts })
            });
            if (res.ok) {
                toast.success('Network mounts updated successfully');
                onOpenChange(false);
            } else {
                const err = await res.json();
                toast.error(err.detail || 'Failed to update mounts');
            }
        } catch (e) {
            toast.error('An error occurred while saving');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="bg-background border-muted text-foreground max-w-2xl">
                <DialogHeader>
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                            <Network className="h-5 w-5" />
                        </div>
                        <DialogTitle className="text-xl font-bold">Network Mounts</DialogTitle>
                    </div>
                    <DialogDescription className="text-muted-foreground">
                        Configure global SMB or NFS shares that will be automatically mounted by all Puppets in the mesh.
                    </DialogDescription>
                </DialogHeader>

                <div className="py-4 space-y-4 max-h-[50vh] overflow-y-auto pr-2">
                    {loading ? (
                        <div className="py-10 text-center text-muted-foreground animate-pulse">Loading configurations...</div>
                    ) : mounts.length === 0 ? (
                        <div className="py-10 text-center rounded-xl border border-dashed border-muted bg-muted/10">
                            <p className="text-muted-foreground italic text-sm">No mounts configured.</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {mounts.map((mount, index) => (
                                <div key={index} className="flex items-end gap-3 p-3 rounded-lg bg-card border border-muted group transition-all hover:border-muted/60">
                                    <div className="flex-1 space-y-1.5">
                                        <Label className="text-[10px] uppercase font-bold text-muted-foreground px-1">Internal Name</Label>
                                        <Input
                                            placeholder="e.g. data-share"
                                            value={mount.name}
                                            onChange={(e) => handleChange(index, 'name', e.target.value)}
                                            className="bg-background border-muted h-9 text-sm"
                                        />
                                    </div>
                                    <div className="flex-[2] space-y-1.5">
                                        <Label className="text-[10px] uppercase font-bold text-muted-foreground px-1">Remote Path</Label>
                                        <Input
                                            placeholder="e.g. //192.168.1.50/storage"
                                            value={mount.remote_path}
                                            onChange={(e) => handleChange(index, 'remote_path', e.target.value)}
                                            className="bg-background border-muted h-9 text-sm font-mono"
                                        />
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => handleRemove(index)}
                                        className="h-9 w-9 text-muted-foreground/60 hover:text-red-400 hover:bg-red-500/10"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <DialogFooter className="flex items-center justify-between border-t border-muted pt-4 mt-2">
                    <Button
                        variant="outline"
                        onClick={handleAdd}
                        disabled={loading || saving}
                        className="bg-card border-muted text-muted-foreground hover:text-foreground"
                    >
                        <Plus className="mr-2 h-4 w-4" />
                        Add Mount
                    </Button>
                    <div className="flex gap-2">
                        <Button variant="ghost" onClick={() => onOpenChange(false)} className="text-muted-foreground">
                            Cancel
                        </Button>
                        <Button
                            onClick={handleSave}
                            disabled={loading || saving}
                            className="bg-primary hover:bg-primary/90 text-white font-bold px-6"
                        >
                            {saving ? 'Saving...' : 'Save Changes'}
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default ManageMountsModal;
