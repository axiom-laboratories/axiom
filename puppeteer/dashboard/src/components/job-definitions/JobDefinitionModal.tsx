import {
    Plus,
    Code2,
    Info
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from '@/components/ui/select';

interface Signature {
    id: string;
    name: string;
    uploaded_by: string;
}

interface JobDefinitionFormData {
    name: string;
    script_content: string;
    signature: string;
    signature_id: string;
    schedule_cron: string;
    target_node_id: string;
}

interface JobDefinitionModalProps {
    isOpen: boolean;
    onClose: (open: boolean) => void;
    onSubmit: (e: React.FormEvent) => void;
    formData: JobDefinitionFormData;
    setFormData: (data: JobDefinitionFormData) => void;
    signatures: Signature[];
}

const JobDefinitionModal = ({
    isOpen,
    onClose,
    onSubmit,
    formData,
    setFormData,
    signatures
}: JobDefinitionModalProps) => {
    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="bg-zinc-925 border-zinc-800 text-white sm:max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-xl font-bold">
                        <Code2 className="h-5 w-5 text-primary" />
                        Seal & Schedule Payload
                    </DialogTitle>
                    <DialogDescription className="text-zinc-500">
                        Create an immutable, cryptographically signed Python job. Every byte of the script is verified at runtime by the puppet nodes.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={onSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-8 py-6">
                    <div className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="job-name" className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Metadata</Label>
                            <div className="space-y-4">
                                <div className="relative">
                                    <Input
                                        id="job-name"
                                        placeholder="System Monitor Script"
                                        className="bg-zinc-900 border-zinc-800 pl-4 h-11"
                                        value={formData.name}
                                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                                        required
                                    />
                                </div>
                                <div className="relative">
                                    <span className="absolute left-3 top-3.5 text-zinc-600 text-xs font-bold">CRON</span>
                                    <Input
                                        id="job-cron"
                                        placeholder="* * * * *"
                                        className="bg-zinc-900 border-zinc-800 pl-14 h-11 font-mono"
                                        value={formData.schedule_cron}
                                        onChange={e => setFormData({ ...formData, schedule_cron: e.target.value })}
                                        aria-label="Cron schedule"
                                    />
                                </div>
                                <Input
                                    id="job-target"
                                    placeholder="Target Node ID (Optional)"
                                    className="bg-zinc-900 border-zinc-800 h-11 font-mono"
                                    value={formData.target_node_id}
                                    onChange={e => setFormData({ ...formData, target_node_id: e.target.value })}
                                    aria-label="Target Node ID"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="job-signature-id" className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Root of Trust</Label>
                            <Select
                                value={formData.signature_id}
                                onValueChange={(val) => setFormData({ ...formData, signature_id: val })}
                            >
                                <SelectTrigger id="job-signature-id" className="bg-zinc-900 border-zinc-800 h-11">
                                    <SelectValue placeholder="Establish Identity..." />
                                </SelectTrigger>
                                <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
                                    {signatures.map(s => (
                                        <SelectItem key={s.id} value={s.id}>
                                            {s.name} ({s.uploaded_by})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="job-signature" className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Signature Payload (B64)</Label>
                            <Textarea
                                id="job-signature"
                                placeholder="Paste Ed25519/RSA signature..."
                                className="bg-zinc-900 border-zinc-800 h-24 font-mono text-2xs text-zinc-400"
                                value={formData.signature}
                                onChange={e => setFormData({ ...formData, signature: e.target.value })}
                                required
                                aria-describedby="signature-help"
                            />
                            <div className="flex items-start gap-2 p-3 rounded-lg bg-zinc-900 border border-zinc-800" id="signature-help">
                                <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" aria-hidden="true" />
                                <p className="text-2xs text-zinc-500 leading-normal">
                                    Use the system CLI or <code>openssl</code> to sign the script. If the signature doesn't match the script bytes exactly, nodes will reject the payload with a <code>SIGNATURE_INVALID</code> alert.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="job-script" className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Python Payload Source</Label>
                        <div className="relative h-full flex flex-col">
                            <div className="absolute top-3 left-3 h-4 w-4 text-zinc-700 pointer-events-none">
                                <Code2 className="h-full w-full" />
                            </div>
                            <Textarea
                                id="job-script"
                                className="flex-1 min-h-[400px] bg-zinc-950 border-zinc-800 pl-10 pt-3 text-green-500 font-mono text-sm resize-none focus:ring-1 focus:ring-primary/20"
                                placeholder="import os\nprint('Identity verified')"
                                value={formData.script_content}
                                onChange={e => setFormData({ ...formData, script_content: e.target.value })}
                                required
                                aria-label="Python script source code"
                            />
                        </div>
                    </div>

                    <DialogFooter className="col-span-full pt-4 border-t border-zinc-800 mt-2">
                        <Button type="button" variant="ghost" onClick={() => onClose(false)} className="text-zinc-500">Abandon</Button>
                        <Button type="submit" className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-8 rounded-xl ring-2 ring-primary/20 ring-offset-2 ring-offset-zinc-925">
                            Seal and Register
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};

export default JobDefinitionModal;
