import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../auth'; // Assume this handles mixed TS/JS or define types if needed
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Copy, Check, Download } from 'lucide-react';

interface AddNodeModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

const AddNodeModal = ({ open, onOpenChange }: AddNodeModalProps) => {
    const [token, setToken] = useState('');
    const [count, setCount] = useState(1);
    const [loading, setLoading] = useState(true);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        if (open) {
            setLoading(true);
            const genToken = async () => {
                try {
                    const res = await authenticatedFetch('/admin/generate-token', {
                        method: 'POST'
                    });
                    if (res.ok) {
                        const data = await res.json();
                        setToken(data.token);
                    }
                } catch (e) {
                    console.error("Token Gen Failed", e);
                } finally {
                    setLoading(false);
                }
            };
            genToken();
        }
    }, [open]);

    const handleCopy = () => {
        const baseUrl = import.meta.env.VITE_API_URL || window.location.origin;
        const cmd = `iex (irm "${baseUrl}/installer") -Role Node -Token "${token}" -Count ${count}`;
        navigator.clipboard.writeText(cmd);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleDownload = () => {
        const baseUrl = import.meta.env.VITE_API_URL || window.location.origin;
        window.location.href = `${baseUrl}/installer`;
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Deploy New Nodes</DialogTitle>
                    <DialogDescription>
                        Generate a secure bootstrap token to enroll new workers into the mesh.
                    </DialogDescription>
                </DialogHeader>

                {loading ? (
                    <div className="py-8 text-center text-muted-foreground">Generating Secure Token...</div>
                ) : (
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="count" className="text-right">
                                Scale Count
                            </Label>
                            <Input
                                id="count"
                                type="number"
                                value={count}
                                onChange={(e) => setCount(parseInt(e.target.value) || 1)}
                                className="col-span-3"
                                min={1}
                                max={50}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Option A: One-Liner (Recommended)</Label>
                            <div className="relative rounded-md bg-muted p-4 pr-12 font-mono text-sm break-all">
                                {`iex (irm "${import.meta.env.VITE_API_URL || window.location.origin}/installer") -Role Node -Token "${token}" -Count ${count}`}
                                <Button
                                    size="icon"
                                    variant="ghost"
                                    className="absolute right-2 top-2 h-8 w-8 text-muted-foreground hover:text-foreground"
                                    onClick={handleCopy}
                                >
                                    {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                                    <span className="sr-only">Copy</span>
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>Option B: Manual Download</Label>
                            <div className="flex items-center gap-4">
                                <Button variant="secondary" onClick={handleDownload}>
                                    <Download className="mr-2 h-4 w-4" />
                                    Download Script
                                </Button>
                                <span className="text-xs text-muted-foreground">
                                    Run: <code>.\install_universal.ps1 -Role Node -Token ...</code>
                                </span>
                            </div>
                        </div>
                    </div>
                )}
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default AddNodeModal;
