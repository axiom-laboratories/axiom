import { useState } from 'react';
import {
    Cpu,
    ShieldAlert,
    Key,
    Zap,
    Code2,
    Copy,
    CheckCircle2,
    RefreshCcw,
    Lock,
    Terminal,
    AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { authenticatedFetch } from '../auth';

const Admin = () => {
    const [joinToken, setJoinToken] = useState<string | null>(null);
    const [pubKey, setPubKey] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    const generateToken = async () => {
        try {
            setIsGenerating(true);
            const res = await authenticatedFetch('/admin/generate-token', { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                setJoinToken(data.token);
            } else {
                console.error('Token generation failed');
            }
        } catch (error) {
            console.error(error);
        } finally {
            setIsGenerating(false);
        }
    };

    const uploadKey = async () => {
        try {
            setIsUploading(true);
            const res = await authenticatedFetch('/admin/upload-key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key_content: pubKey })
            });
            if (res.ok) {
                setPubKey('');
                alert('Key stored successfully');
            }
        } catch (e) {
            console.error(e);
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Admin Console</h1>
                <p className="text-zinc-500">System-wide configuration, node onboarding, and master security policy.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Node Onboarding */}
                <Card className="bg-zinc-925 border-zinc-800/50 flex flex-col">
                    <CardHeader>
                        <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                            <Cpu className="h-5 w-5 text-primary" />
                        </div>
                        <CardTitle className="text-xl font-bold text-white">Node Onboarding</CardTitle>
                        <CardDescription className="text-zinc-500">
                            Generate secure, short-lived tokens to register new puppets into the mesh.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="flex-1 space-y-6">
                        <div className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800 text-sm text-zinc-400 leading-relaxed">
                            <ShieldAlert className="h-4 w-4 text-primary inline mr-2 mb-1" />
                            Join tokens are one-time use and expire after 24 hours. Ensure the target node has the control plane's public CA certificate installed.
                        </div>

                        {!joinToken ? (
                            <Button
                                onClick={generateToken}
                                disabled={isGenerating}
                                className="w-full h-12 bg-primary hover:bg-primary/90 text-white font-bold rounded-xl shadow-lg shadow-primary/10 transition-all active:scale-[0.98]"
                            >
                                <Zap className="mr-2 h-4 w-4 fill-current" />
                                {isGenerating ? 'Securing...' : 'Generate Join Token'}
                            </Button>
                        ) : (
                            <div className="space-y-4 animate-in slide-in-from-bottom-2">
                                <div className="space-y-2">
                                    <label className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Active Join Token</label>
                                    <div className="flex gap-2">
                                        <div className="flex-1 h-12 bg-zinc-900 border border-primary/30 rounded-xl flex items-center px-4 font-mono text-primary font-bold overflow-hidden truncate">
                                            {joinToken}
                                        </div>
                                        <Button
                                            variant="outline"
                                            className="h-12 w-12 border-zinc-800 bg-zinc-900 p-0"
                                            onClick={() => navigator.clipboard.writeText(joinToken || '')}
                                        >
                                            <Copy className="h-4 w-4 text-zinc-400" />
                                        </Button>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 text-2xs text-green-500 font-bold uppercase tracking-tighter">
                                    <CheckCircle2 className="h-3 w-3" />
                                    Token ready for deployment
                                </div>
                                <Button
                                    variant="link"
                                    onClick={() => setJoinToken(null)}
                                    className="text-zinc-600 p-0 h-auto text-xs hover:text-zinc-400"
                                >
                                    <RefreshCcw className="mr-1 h-3 w-3" />
                                    Revoke & Create New
                                </Button>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Key Management */}
                <Card className="bg-zinc-925 border-zinc-800/50 flex flex-col">
                    <CardHeader>
                        <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                            <Key className="h-5 w-5 text-primary" />
                        </div>
                        <CardTitle className="text-xl font-bold text-white">Security Root of Trust</CardTitle>
                        <CardDescription className="text-zinc-500">
                            Rotate the Master Public Key used by puppets to verify the signature of every dispatched job.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="flex-1 space-y-4">
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <label className="text-2xs font-bold text-zinc-500 uppercase tracking-widest">Master Public Key (PEM)</label>
                                <Badge variant="outline" className="h-5 px-1.5 text-2xs border-zinc-800 text-zinc-600">Rotation Required</Badge>
                            </div>
                            <div className="relative group/pk">
                                <Terminal className="absolute top-3 left-3 h-4 w-4 text-zinc-600" />
                                <Textarea
                                    value={pubKey}
                                    onChange={e => setPubKey(e.target.value)}
                                    placeholder="-----BEGIN PUBLIC KEY-----"
                                    className="min-h-[160px] pl-10 bg-zinc-900 border-zinc-800 text-green-500 font-mono text-sm placeholder:text-zinc-700 focus:ring-primary/20 transition-all"
                                />
                                <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-zinc-900 to-transparent pointer-events-none rounded-b-xl" />
                            </div>
                        </div>

                        <Button
                            onClick={uploadKey}
                            disabled={isUploading || !pubKey}
                            className="w-full h-12 bg-zinc-100 hover:bg-white text-black font-bold rounded-xl transition-all disabled:opacity-50"
                        >
                            <Lock className="mr-2 h-4 w-4" />
                            {isUploading ? 'Updating Root...' : 'Upload Root Key'}
                        </Button>

                        <p className="text-2xs text-zinc-600 text-center flex items-center justify-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            Changing this key will break validation for all existing nodes until they are updated.
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default Admin;
