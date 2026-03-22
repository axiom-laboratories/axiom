import { useState } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { Hash, Layers } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { authenticatedFetch } from '../auth';

interface CreateTemplateDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export const CreateTemplateDialog = ({ open, onOpenChange }: CreateTemplateDialogProps) => {
    const queryClient = useQueryClient();
    const [name, setName] = useState('');
    const [runtimeId, setRuntimeId] = useState('');
    const [networkId, setNetworkId] = useState('');

    const { data: blueprints = [] } = useQuery({
        queryKey: ['blueprints'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/blueprints');
            return await res.json();
        }
    });

    const runtimes = blueprints.filter((b: any) => b.type === 'RUNTIME');
    const networks = blueprints.filter((b: any) => b.type === 'NETWORK');

    const createMutation = useMutation({
        mutationFn: async () => {
            const res = await authenticatedFetch('/api/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    friendly_name: name,
                    runtime_blueprint_id: runtimeId,
                    network_blueprint_id: networkId
                })
            });
            if (!res.ok) throw new Error('Failed to create template');
            return await res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['templates'] });
            onOpenChange(false);
            setName('');
            setRuntimeId('');
            setNetworkId('');
        }
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="bg-zinc-950 border-zinc-800 text-white">
                <DialogHeader>
                    <DialogTitle className="text-xl font-bold">Compose Node Image</DialogTitle>
                    <DialogDescription className="text-zinc-500">
                        Combine environment and network image recipes into a single deployable image.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    <div className="grid gap-2">
                        <Label htmlFor="t-name">Node Image Name</Label>
                        <Input 
                            id="t-name" 
                            value={name} 
                            onChange={(e) => setName(e.target.value)} 
                            placeholder="e.g. finance-production-worker"
                            className="bg-zinc-900 border-zinc-800"
                        />
                    </div>

                    <div className="grid gap-2">
                        <Label>Runtime Image Recipe</Label>
                        <Select value={runtimeId} onValueChange={setRuntimeId}>
                            <SelectTrigger className="bg-zinc-900 border-zinc-800">
                                <SelectValue placeholder="Select a Runtime" />
                            </SelectTrigger>
                            <SelectContent>
                                {runtimes.map((b: any) => (
                                    <SelectItem key={b.id} value={b.id}>{b.name} (v{b.version})</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="grid gap-2">
                        <Label>Network Perimeter</Label>
                        <Select value={networkId} onValueChange={setNetworkId}>
                            <SelectTrigger className="bg-zinc-900 border-zinc-800">
                                <SelectValue placeholder="Select a Perimeter" />
                            </SelectTrigger>
                            <SelectContent>
                                {networks.map((b: any) => (
                                    <SelectItem key={b.id} value={b.id}>{b.name} (v{b.version})</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {runtimeId && networkId && (
                        <div className="p-4 bg-primary/5 rounded-xl border border-primary/20 flex items-start gap-3">
                            <Layers className="h-5 w-5 text-primary mt-0.5" />
                            <div>
                                <div className="text-sm font-bold text-white">Canonical ID Calculation</div>
                                <div className="text-xs text-zinc-500 mt-1 flex items-center gap-1">
                                    <Hash className="h-3 w-3" /> Deterministic hash will be generated upon creation.
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button 
                        onClick={() => createMutation.mutate()} 
                        disabled={!name || !runtimeId || !networkId || createMutation.isPending}
                        className="bg-primary hover:bg-primary/90"
                    >
                        {createMutation.isPending ? 'Composing...' : 'Create Node Image'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
