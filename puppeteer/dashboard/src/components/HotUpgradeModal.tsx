import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { 
    Zap, 
    ShieldAlert, 
    ChevronRight, 
    Terminal, 
    CheckCircle2, 
    AlertTriangle,
    ArrowRight,
    Loader2
} from 'lucide-react';
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
import { Badge } from '@/components/ui/badge';
import { authenticatedFetch } from '../auth';

interface Capability {
    id: number;
    base_os_family: string;
    tool_id: string;
    injection_recipe: string;
    validation_cmd: string;
}

interface HotUpgradeModalProps {
    node: any;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

const HotUpgradeModal = ({ node, open, onOpenChange }: HotUpgradeModalProps) => {
    const [step, setGate] = useState(1);
    const [matrix, setMatrix] = useState<Capability[]>([]);
    const [selectedTool, setSelectedTool] = useState<Capability | null>(null);
    const [confirmText, setConfirmText] = useState('');
    const [loading, setLoading] = useState(false);
    const [staging, setStaging] = useState(false);

    useEffect(() => {
        if (open) {
            fetchMatrix();
            setGate(1);
            setSelectedTool(null);
            setConfirmText('');
        }
    }, [open]);

    const fetchMatrix = async () => {
        setLoading(true);
        try {
            const res = await authenticatedFetch('/api/capability-matrix');
            if (res.ok) {
                const data = await res.json();
                // Filter by node's OS family if available
                const filtered = node.base_os_family 
                    ? data.filter((c: Capability) => c.base_os_family === node.base_os_family)
                    : data;
                setMatrix(filtered);
            }
        } catch (e) {
            toast.error('Failed to load capability matrix');
        } finally {
            setLoading(false);
        }
    };

    const handleStageUpgrade = async () => {
        if (!selectedTool) return;
        setStaging(true);
        try {
            const res = await authenticatedFetch(`/api/nodes/${node.node_id}/upgrade?capability_id=${selectedTool.id}`, {
                method: 'POST'
            });
            if (res.ok) {
                toast.success(`Upgrade staged for ${node.hostname}`);
                onOpenChange(false);
            } else {
                const err = await res.json();
                toast.error(err.detail || 'Staging failed');
            }
        } catch (e) {
            toast.error('An error occurred');
        } finally {
            setStaging(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="bg-background border-muted text-foreground max-w-2xl overflow-hidden p-0 gap-0">
                <div className="bg-muted/20 px-6 py-4 border-b border-muted">
                    <DialogHeader>
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-primary/10 text-primary">
                                <Zap className="h-5 w-5 fill-current" />
                            </div>
                            <div>
                                <DialogTitle className="text-xl font-bold">Hot-Upgrade Runtime</DialogTitle>
                                <DialogDescription className="text-muted-foreground">
                                    {node.hostname} ({node.base_os_family || 'Generic'})
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                </div>

                <div className="p-6">
                    {/* Step Indicators */}
                    <div className="flex items-center gap-2 mb-8 px-2">
                        {[1, 2, 3].map(i => (
                            <React.Fragment key={i}>
                                <div className={`h-1.5 flex-1 rounded-full transition-colors ${step >= i ? 'bg-primary' : 'bg-muted'}`} />
                                {i < 3 && <ChevronRight className="h-3 w-3 text-muted-foreground/40" />}
                            </React.Fragment>
                        ))}
                    </div>

                    {step === 1 && (
                        <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-1">Select Tool to Push</label>
                                <div className="grid grid-cols-1 gap-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                    {loading ? (
                                        <div className="py-10 text-center text-muted-foreground/60 italic">Syncing Matrix...</div>
                                    ) : matrix.length === 0 ? (
                                        <div className="py-10 text-center text-muted-foreground/60 italic border border-dashed border-muted rounded-lg">
                                            No compatible recipes found for {node.base_os_family}.
                                        </div>
                                    ) : matrix.map(cap => (
                                        <button
                                            key={cap.id}
                                            onClick={() => setSelectedTool(cap)}
                                            className={`flex items-center justify-between p-3 rounded-xl border transition-all text-left group ${
                                                selectedTool?.id === cap.id
                                                    ? 'bg-primary/10 border-primary text-primary shadow-[0_0_15px_rgba(139,92,246,0.1)]'
                                                    : 'bg-card border-muted text-muted-foreground hover:border-muted/60'
                                            }`}
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className={`p-1.5 rounded-lg ${selectedTool?.id === cap.id ? 'bg-primary/20' : 'bg-muted group-hover:bg-muted/70'}`}>
                                                    <Terminal className="h-4 w-4" />
                                                </div>
                                                <span className="font-bold">{cap.tool_id}</span>
                                            </div>
                                            <Badge variant="outline" className={`text-[8px] h-4 ${selectedTool?.id === cap.id ? 'border-primary/30' : 'border-muted'}`}>
                                                {cap.base_os_family}
                                            </Badge>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 2 && selectedTool && (
                        <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                            <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 flex gap-4">
                                <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
                                <div className="space-y-1">
                                    <h4 className="text-sm font-bold text-amber-200">Runtime Mutation Warning</h4>
                                    <p className="text-xs text-amber-200/60 leading-relaxed">
                                        This will inject new logic directly into the node's host environment. While signed, this bypasses the standard container rebuild cycle.
                                    </p>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-1">Recipe Preview (Signed)</label>
                                <div className="bg-black border border-muted rounded-xl p-4 font-mono text-xs text-muted-foreground/60 overflow-auto max-h-[200px]">
                                    {selectedTool.injection_recipe}
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 3 && selectedTool && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                            <div className="text-center space-y-2">
                                <div className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-red-500/10 text-red-500 mb-2">
                                    <ShieldAlert className="h-6 w-6" />
                                </div>
                                <h3 className="text-lg font-bold">Administrative Guard</h3>
                                <p className="text-sm text-muted-foreground max-w-[400px] mx-auto">
                                    To authorize the push of <span className="text-foreground font-bold">{selectedTool.tool_id}</span> to <span className="text-foreground font-bold">{node.hostname}</span>, please type the confirmation string below.
                                </p>
                            </div>

                            <div className="space-y-2">
                                <Input
                                    placeholder="Type UPGRADE to confirm"
                                    value={confirmText}
                                    onChange={e => setConfirmText(e.target.value)}
                                    className="bg-card border-muted text-center font-bold tracking-widest focus:border-red-500/50"
                                />
                            </div>
                        </div>
                    )}
                </div>

                <div className="bg-muted/20 px-6 py-4 flex items-center justify-between border-t border-muted">
                    <Button
                        variant="ghost"
                        onClick={() => step > 1 ? setGate(step - 1) : onOpenChange(false)}
                        className="text-muted-foreground hover:text-foreground"
                    >
                        {step === 1 ? 'Cancel' : 'Back'}
                    </Button>
                    
                    {step < 3 ? (
                        <Button 
                            disabled={step === 1 && !selectedTool}
                            onClick={() => setGate(step + 1)}
                            className="bg-primary hover:bg-primary/90 text-white font-bold"
                        >
                            Continue
                            <ArrowRight className="ml-2 h-4 w-4" />
                        </Button>
                    ) : (
                        <Button 
                            disabled={confirmText !== 'UPGRADE' || staging}
                            onClick={handleStageUpgrade}
                            className="bg-red-600 hover:bg-red-700 text-white font-bold px-8 shadow-lg shadow-red-900/20"
                        >
                            {staging ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Staging...</> : 'Apply Upgrade'}
                        </Button>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default HotUpgradeModal;
