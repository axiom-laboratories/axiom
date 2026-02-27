import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Boxes, Hammer, CheckCircle2, Clock, AlertCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { authenticatedFetch } from '../auth';

interface Template {
    id: string;
    friendly_name: string;
    canonical_id: string;
    last_built_image?: string;
    last_built_at?: string;
    runtime_blueprint_id: string;
    network_blueprint_id: string;
}

const TemplateCard = ({ template }: { template: Template }) => {
    const queryClient = useQueryClient();
    const [buildStatus, setBuildStatus] = useState<'idle' | 'building' | 'success' | 'failed'>('idle');

    const buildMutation = useMutation({
        mutationFn: async () => {
            const res = await authenticatedFetch(`/api/templates/${template.id}/build`, { method: 'POST' });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Build failed');
            }
            return await res.json();
        },
        onMutate: () => setBuildStatus('building'),
        onSuccess: () => {
            setBuildStatus('success');
            queryClient.invalidateQueries({ queryKey: ['templates'] });
        },
        onError: () => setBuildStatus('failed'),
    });

    return (
        <Card className="bg-zinc-925 border-zinc-800/50 hover:border-primary/30 transition-all flex flex-col">
            <CardHeader>
                <div className="flex items-start justify-between">
                    <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                        <Boxes className="h-5 w-5 text-primary" />
                    </div>
                    <Badge variant="outline" className="font-mono text-2xs border-zinc-800 text-zinc-500">
                        {template.canonical_id}
                    </Badge>
                </div>
                <CardTitle className="mt-4 text-white font-bold">{template.friendly_name}</CardTitle>
                <CardDescription className="text-zinc-500 text-xs">
                    {template.last_built_image
                        ? `Last: ${template.last_built_image.split('/').pop()}`
                        : 'Never built'}
                </CardDescription>
            </CardHeader>
            <CardContent className="flex-1">
                {buildStatus === 'success' && (
                    <div className="flex items-center gap-2 text-xs text-green-500 font-bold uppercase tracking-tighter animate-in fade-in">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Build succeeded
                    </div>
                )}
                {buildStatus === 'failed' && (
                    <div className="flex items-center gap-2 text-xs text-red-500 font-bold uppercase tracking-tighter animate-in fade-in">
                        <AlertCircle className="h-3.5 w-3.5" /> Build failed
                    </div>
                )}
                {buildStatus === 'idle' && template.last_built_at && (
                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                        <Clock className="h-3 w-3" />
                        {new Date(template.last_built_at).toLocaleString()}
                    </div>
                )}
            </CardContent>
            <CardFooter className="bg-white/[0.02] border-t border-zinc-800/50 pt-4">
                <Button
                    onClick={() => buildMutation.mutate()}
                    disabled={buildStatus === 'building'}
                    className="w-full h-10 bg-primary hover:bg-primary/90 text-white font-bold rounded-xl shadow-lg shadow-primary/10"
                >
                    {buildStatus === 'building' ? (
                        <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Building...</>
                    ) : (
                        <><Hammer className="mr-2 h-4 w-4" /> Build Image</>
                    )}
                </Button>
            </CardFooter>
        </Card>
    );
};

const Templates = () => {
    const { data: templates = [], isLoading } = useQuery<Template[]>({
        queryKey: ['templates'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/templates');
            if (!res.ok) throw new Error('Failed to fetch templates');
            return await res.json();
        }
    });

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Puppet Templates</h1>
                <p className="text-zinc-500">Build and manage puppet environment images via the Foundry.</p>
            </div>

            {isLoading ? (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-56 rounded-2xl bg-zinc-900/50 border border-zinc-800 animate-pulse" />
                    ))}
                </div>
            ) : templates.length > 0 ? (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {templates.map(t => <TemplateCard key={t.id} template={t} />)}
                </div>
            ) : (
                <div className="col-span-full py-16 text-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20">
                    <Boxes className="h-12 w-12 text-zinc-800 mx-auto mb-4" />
                    <h3 className="text-zinc-400 font-medium">No templates found</h3>
                    <p className="text-zinc-600 text-sm mt-1">
                        Create a Blueprint and Template via the API to get started.
                    </p>
                </div>
            )}
        </div>
    );
};

export default Templates;
