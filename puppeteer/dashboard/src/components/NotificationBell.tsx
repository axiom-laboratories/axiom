import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, AlertTriangle, Info, ShieldAlert, CheckCircle2, X } from 'lucide-react';
import { toast } from 'sonner';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { authenticatedFetch } from '../auth';
import { useWebSocket } from '../hooks/useWebSocket';

interface Alert {
    id: number;
    type: string;
    severity: string;
    message: string;
    resource_id?: string;
    created_at: string;
    acknowledged: boolean;
}

const SeverityIcon = ({ severity }: { severity: string }) => {
    switch (severity.toUpperCase()) {
        case 'CRITICAL': return <AlertTriangle className="h-4 w-4 text-red-500" />;
        case 'WARNING': return <AlertTriangle className="h-4 w-4 text-amber-500" />;
        case 'SECURITY': return <ShieldAlert className="h-4 w-4 text-purple-500" />;
        default: return <Info className="h-4 w-4 text-blue-500" />;
    }
};

export function NotificationBell() {
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);

    const { data: alerts = [], refetch } = useQuery<Alert[]>({
        queryKey: ['alerts', 'unacknowledged'],
        queryFn: async () => {
            const res = await authenticatedFetch('/api/alerts?unacknowledged_only=true');
            if (!res.ok) return [];
            return res.json();
        },
        refetchInterval: 30000, // Fallback poll every 30s
    });

    const acknowledge = useMutation({
        mutationFn: async (id: number) => {
            await authenticatedFetch(`/api/alerts/${id}/acknowledge`, { method: 'POST' });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['alerts'] });
        },
    });

    // Real-time updates via WebSocket
    useWebSocket((event, data: any) => {
        if (event === 'alert:new') {
            queryClient.invalidateQueries({ queryKey: ['alerts'] });
            
            // Show real-time toast
            const severity = data.severity?.toUpperCase() || 'INFO';
            const message = data.message || 'New system alert';
            
            if (severity === 'CRITICAL' || severity === 'SECURITY') {
                toast.error(message, {
                    description: 'Critical system event detected',
                    duration: 10000,
                });
            } else if (severity === 'WARNING') {
                toast.warning(message, {
                    duration: 6000,
                });
            } else {
                toast.info(message);
            }
        }
    });

    const unreadCount = alerts.length;

    return (
        <DropdownMenu open={open} onOpenChange={setOpen}>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="relative rounded-full hover:bg-zinc-800">
                    <Bell className="h-5 w-5 text-zinc-400" />
                    {unreadCount > 0 && (
                        <span className="absolute top-2 right-2 flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                        </span>
                    )}
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80 bg-zinc-900 border-zinc-800 p-0 shadow-2xl">
                <div className="flex items-center justify-between p-4">
                    <DropdownMenuLabel className="text-white font-bold p-0">Notifications</DropdownMenuLabel>
                    {unreadCount > 0 && (
                        <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/20 text-[10px] px-1.5 py-0">
                            {unreadCount} New
                        </Badge>
                    )}
                </div>
                <DropdownMenuSeparator className="bg-zinc-800" />
                
                <div className="max-h-[400px] overflow-y-auto">
                    {alerts.length === 0 ? (
                        <div className="p-8 text-center text-zinc-500 text-sm">
                            <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-20" />
                            No new notifications
                        </div>
                    ) : (
                        alerts.map((alert) => (
                            <div key={alert.id} className="p-4 border-b border-zinc-800 last:border-0 hover:bg-zinc-800/50 transition-colors group">
                                <div className="flex gap-3">
                                    <div className="mt-1">
                                        <SeverityIcon severity={alert.severity} />
                                    </div>
                                    <div className="flex-1 space-y-1">
                                        <p className="text-sm text-zinc-200 leading-snug">
                                            {alert.message}
                                        </p>
                                        <div className="flex items-center justify-between">
                                            <span className="text-[10px] text-zinc-500">
                                                {new Date(alert.created_at).toLocaleTimeString()}
                                            </span>
                                            <button 
                                                onClick={() => acknowledge.mutate(alert.id)}
                                                className="text-[10px] font-bold text-primary hover:text-primary/80 opacity-0 group-hover:opacity-100 transition-opacity"
                                            >
                                                Mark as Read
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
                
                {alerts.length > 0 && (
                    <>
                        <DropdownMenuSeparator className="bg-zinc-800" />
                        <div className="p-2">
                            <Button variant="ghost" className="w-full text-xs text-zinc-500 hover:text-white" onClick={() => setOpen(false)}>
                                Close
                            </Button>
                        </div>
                    </>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
