import { useState } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { Plus, X, Globe, Cpu, ShieldCheck } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { authenticatedFetch } from '../auth';

interface CreateBlueprintDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export const CreateBlueprintDialog = ({ open, onOpenChange }: CreateBlueprintDialogProps) => {
    const queryClient = useQueryClient();
    const [type, setType] = useState<'RUNTIME' | 'NETWORK'>('RUNTIME');
    const [name, setName] = useState('');
    
    // Runtime Fields
    const [baseOs, setBaseOs] = useState('debian:12-slim');
    const [selectedTools, setSelectedTools] = useState<string[]>([]);
    const [packages, setPackages] = useState<string[]>([]);
    const [newPackage, setNewPackage] = useState('');

    // Network Fields
    const [policy, setPolicy] = useState<'STRICT_DENY' | 'LOG_ONLY'>('STRICT_DENY');
    const [managementBypass] = useState(true);
    const [egressRules, setEgressRules] = useState<{type: string, value: string, port: number, desc: string}[]>([]);
    const [newRule, setNewRule] = useState({type: 'url', value: '', port: 443, desc: ''});

    const { data: matrix = [] } = useQuery({
        queryKey: ['capability-matrix'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/capability-matrix');
            return await res.json();
        }
    });

    const createMutation = useMutation({
        mutationFn: async () => {
            const definition = type === 'RUNTIME' ? {
                base_os: baseOs,
                tools: selectedTools.map(id => ({ id, version: 'latest' })),
                packages: { python: packages }
            } : {
                egress_rules: egressRules,
                policy: policy,
                management_bypass: managementBypass
            };

            const res = await authenticatedFetch('/api/blueprints', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, name, definition })
            });
            if (!res.ok) throw new Error('Failed to create blueprint');
            return await res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['blueprints'] });
            onOpenChange(false);
            resetForm();
        }
    });

    const resetForm = () => {
        setName('');
        setSelectedTools([]);
        setPackages([]);
        setEgressRules([]);
    };

    const addPackage = () => {
        if (newPackage && !packages.includes(newPackage)) {
            setPackages([...packages, newPackage]);
            setNewPackage('');
        }
    };

    const addRule = () => {
        if (newRule.value) {
            setEgressRules([...egressRules, newRule]);
            setNewRule({type: 'url', value: '', port: 443, desc: ''});
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl bg-zinc-950 border-zinc-800 text-white">
                <DialogHeader>
                    <DialogTitle className="text-xl font-bold">Create New Blueprint</DialogTitle>
                    <DialogDescription className="text-zinc-500">
                        Define a reusable environment or network perimeter.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    <div className="flex gap-2 p-1 bg-zinc-900 rounded-lg">
                        <Button 
                            variant={type === 'RUNTIME' ? 'default' : 'ghost'} 
                            className="flex-1"
                            onClick={() => setType('RUNTIME')}
                        >
                            <Cpu className="mr-2 h-4 w-4" /> Runtime
                        </Button>
                        <Button 
                            variant={type === 'NETWORK' ? 'default' : 'ghost'} 
                            className="flex-1"
                            onClick={() => setType('NETWORK')}
                        >
                            <Globe className="mr-2 h-4 w-4" /> Network
                        </Button>
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="name">Blueprint Name</Label>
                        <Input 
                            id="name" 
                            value={name} 
                            onChange={(e) => setName(e.target.value)} 
                            placeholder="e.g. Finance-Python-3.11"
                            className="bg-zinc-900 border-zinc-800"
                        />
                    </div>

                    {type === 'RUNTIME' ? (
                        <>
                            <div className="grid gap-2">
                                <Label>Base OS</Label>
                                <Select value={baseOs} onValueChange={setBaseOs}>
                                    <SelectTrigger className="bg-zinc-900 border-zinc-800">
                                        <SelectValue placeholder="Select OS" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="debian:12-slim">Debian 12 Slim</SelectItem>
                                        <SelectItem value="alpine:3.19">Alpine 3.19</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="grid gap-2">
                                <Label>Tools (from Matrix)</Label>
                                <div className="flex flex-wrap gap-2 p-3 bg-zinc-900 rounded-md border border-zinc-800">
                                    {matrix.map((entry: any) => (
                                        <Badge 
                                            key={entry.tool_id}
                                            variant={selectedTools.includes(entry.tool_id) ? 'default' : 'outline'}
                                            className="cursor-pointer"
                                            onClick={() => {
                                                if (selectedTools.includes(entry.tool_id)) {
                                                    setSelectedTools(selectedTools.filter(id => id !== entry.tool_id));
                                                } else {
                                                    setSelectedTools([...selectedTools, entry.tool_id]);
                                                }
                                            }}
                                        >
                                            {entry.tool_id}
                                        </Badge>
                                    ))}
                                </div>
                            </div>

                            <div className="grid gap-2">
                                <Label>Python Packages (PIP)</Label>
                                <div className="flex gap-2">
                                    <Input 
                                        value={newPackage} 
                                        onChange={(e) => setNewPackage(e.target.value)} 
                                        placeholder="e.g. pandas==2.1.0"
                                        className="bg-zinc-900 border-zinc-800"
                                    />
                                    <Button onClick={addPackage} type="button" size="icon">
                                        <Plus className="h-4 w-4" />
                                    </Button>
                                </div>
                                <div className="flex flex-wrap gap-2 mt-2">
                                    {packages.map(p => (
                                        <Badge key={p} variant="secondary" className="bg-zinc-800 text-zinc-300">
                                            {p} <X className="ml-1 h-3 w-3 cursor-pointer" onClick={() => setPackages(packages.filter(i => i !== p))} />
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="grid gap-2">
                                <Label>Policy Mode</Label>
                                <Select value={policy} onValueChange={(v: any) => setPolicy(v)}>
                                    <SelectTrigger className="bg-zinc-900 border-zinc-800">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="STRICT_DENY">Strict Deny (Whitelisted Only)</SelectItem>
                                        <SelectItem value="LOG_ONLY">Log Only (Alert on Egress)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="flex items-center gap-2 p-3 bg-zinc-900 rounded-md border border-zinc-800">
                                <ShieldCheck className="h-4 w-4 text-green-500" />
                                <div className="flex-1 text-sm">Management Bypass (Always allow Puppeteer API)</div>
                                <div className="text-xs text-zinc-500 font-bold uppercase">Enabled</div>
                            </div>

                            <div className="grid gap-2">
                                <Label>Egress Rules</Label>
                                <div className="grid grid-cols-4 gap-2">
                                    <Select value={newRule.type} onValueChange={(v) => setNewRule({...newRule, type: v})}>
                                        <SelectTrigger className="bg-zinc-900 border-zinc-800"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="url">URL</SelectItem>
                                            <SelectItem value="ip">IP/CIDR</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <Input 
                                        className="col-span-2 bg-zinc-900 border-zinc-800" 
                                        placeholder="Host/IP" 
                                        value={newRule.value}
                                        onChange={(e) => setNewRule({...newRule, value: e.target.value})}
                                    />
                                    <Button onClick={addRule} type="button">Add</Button>
                                </div>
                                <div className="space-y-2 mt-2">
                                    {egressRules.map((rule, idx) => (
                                        <div key={idx} className="flex items-center justify-between p-2 bg-zinc-900 rounded border border-zinc-800 text-sm">
                                            <div className="flex gap-4">
                                                <Badge className="bg-primary/20 text-primary border-0 capitalize">{rule.type}</Badge>
                                                <span>{rule.value}:{rule.port}</span>
                                            </div>
                                            <X className="h-4 w-4 text-zinc-500 cursor-pointer" onClick={() => setEgressRules(egressRules.filter((_, i) => i !== idx))} />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button 
                        onClick={() => createMutation.mutate()} 
                        disabled={!name || createMutation.isPending}
                        className="bg-primary hover:bg-primary/90"
                    >
                        {createMutation.isPending ? 'Creating...' : 'Create Blueprint'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
