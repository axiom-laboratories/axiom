import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ScrollText, Bot } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { authenticatedFetch } from '../auth';
import { useFeatures } from '../hooks/useFeatures';
import { UpgradePlaceholder } from '../components/UpgradePlaceholder';

interface AuditEntry {
    id: number;
    timestamp: string;
    username: string;
    action: string;
    resource_id: string | null;
    detail: Record<string, unknown> | null;
}

const ACTION_COLOR: Record<string, string> = {
    'node:revoke': 'text-amber-400',
    'node:reinstate': 'text-emerald-400',
    'node:delete': 'text-red-400',
    'user:create': 'text-blue-400',
    'user:delete': 'text-red-400',
    'user:role_change': 'text-violet-400',
    'permission:grant': 'text-emerald-400',
    'permission:revoke': 'text-amber-400',
    'job:cancel': 'text-amber-400',
    'key:upload': 'text-blue-400',
    'signature:delete': 'text-red-400',
    'blueprint:delete': 'text-red-400',
    'template:delete': 'text-red-400',
    'template:build': 'text-violet-400',
    'base_image:marked_updated': 'text-emerald-400',
};

const PAGE_SIZE = 100;

const AuditLog = () => {
    const [page, setPage] = useState(0);

    const { data: entries = [], isLoading, isPlaceholderData } = useQuery<AuditEntry[]>({
        queryKey: ['audit-log', page],
        queryFn: async () => {
            try {
                const res = await authenticatedFetch(`/admin/audit-log?limit=${PAGE_SIZE}&skip=${page * PAGE_SIZE}`);
                if (!res.ok) throw new Error('Failed to fetch audit log');
                return await res.json();
            } catch (e) {
                toast.error('Failed to load audit log');
                throw e;
            }
        },
        refetchInterval: 15000,
        placeholderData: (previousData) => previousData,
    });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
                        <ScrollText className="h-5 w-5 text-primary" />
                        Audit Log
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1">Security-relevant actions, most recent first.</p>
                </div>
            </div>

            <div className="rounded-xl border border-muted overflow-hidden bg-background/20">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="bg-secondary border-b border-muted">
                            <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground w-44">Timestamp</th>
                            <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground w-28">User</th>
                            <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground w-40">Action</th>
                            <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground w-40">Resource</th>
                            <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Detail</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading && entries.length === 0 ? (
                            Array.from({ length: 8 }).map((_, i) => (
                                <tr key={i} className="border-b border-muted/50">
                                    {Array.from({ length: 5 }).map((_, j) => (
                                        <td key={j} className="px-4 py-3">
                                            <div className="h-3 rounded bg-muted animate-pulse w-3/4" />
                                        </td>
                                    ))}
                                </tr>
                            ))
                        ) : entries.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-4 py-16 text-center text-muted-foreground/60">
                                    No audit entries yet.
                                </td>
                            </tr>
                        ) : (
                            entries.map(entry => (
                                <tr key={entry.id} className={`border-b border-muted/40 hover:bg-secondary/40 transition-colors ${isPlaceholderData ? 'opacity-50' : ''}`}>
                                    <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                                        {new Date(entry.timestamp).toLocaleString()}
                                    </td>
                                    <td className="px-4 py-2.5 font-mono text-[11px] text-foreground">
                                        {entry.username.startsWith('sp:') ? (
                                            <span className="flex items-center gap-1.5">
                                                <Bot className="h-3.5 w-3.5 text-blue-400" />
                                                <span className="text-blue-300">{entry.username.slice(3)}</span>
                                            </span>
                                        ) : entry.username}
                                    </td>
                                    <td className="px-4 py-2.5 font-mono text-[11px]">
                                        <span className={ACTION_COLOR[entry.action] ?? 'text-muted-foreground'}>
                                            {entry.action}
                                        </span>
                                    </td>
                                    <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground truncate max-w-[160px]">
                                        {entry.resource_id ?? '—'}
                                    </td>
                                    <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground/60 truncate max-w-[300px]">
                                        {entry.detail ? JSON.stringify(entry.detail) : '—'}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
                <div className="flex items-center justify-between px-4 py-3 border-t border-muted bg-secondary/30">
                    <span className="text-xs text-muted-foreground">Page {page + 1}</span>
                    <div className="flex gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 text-xs text-muted-foreground hover:text-foreground"
                            disabled={page === 0}
                            onClick={() => setPage(p => p - 1)}
                        >
                            Previous
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 text-xs text-muted-foreground hover:text-foreground"
                            disabled={entries.length < PAGE_SIZE}
                            onClick={() => setPage(p => p + 1)}
                        >
                            Next
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

const AuditLogWithFeatureCheck = () => {
    const features = useFeatures();
    if (!features.audit) {
        return <UpgradePlaceholder feature="Audit Log" description="Full security audit trail with retention policies, filtering, and export for compliance requirements." />;
    }
    return <AuditLog />;
};

export default AuditLogWithFeatureCheck;
