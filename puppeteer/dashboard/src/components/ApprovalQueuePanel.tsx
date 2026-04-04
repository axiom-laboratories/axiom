import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Loader2, AlertCircle, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { authenticatedFetch } from '../auth';
import { getUser } from '../auth';

interface ScriptAnalysisRequest {
    id: string;
    requester_id: string;
    requester_username?: string;
    package_name: string;
    ecosystem: string;
    detected_import: string;
    status: 'PENDING' | 'APPROVED' | 'REJECTED';
    created_at: string;
    reviewed_at?: string;
    reviewed_by?: string;
    review_reason?: string;
}

interface ApprovalQueuePanelProps {
    onRefresh?: () => void;
}

export const ApprovalQueuePanel: React.FC<ApprovalQueuePanelProps> = ({ onRefresh }) => {
    const [selectedStatus, setSelectedStatus] = useState<'all' | 'pending' | 'approved' | 'rejected'>('pending');
    const [rejectDialogOpen, setRejectDialogOpen] = useState<boolean>(false);
    const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
    const [rejectReason, setRejectReason] = useState<string>('');
    const queryClient = useQueryClient();
    const user = getUser();
    const isAdmin = user?.role === 'admin';

    // Permission gate
    if (!isAdmin) {
        return (
            <div className="p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
                <div className="flex gap-3">
                    <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                    <div className="text-sm text-amber-800 dark:text-amber-300">
                        Admin access required to review script analysis requests
                    </div>
                </div>
            </div>
        );
    }

    // Fetch requests based on selected status filter
    const { data: requests = [], isLoading, error } = useQuery({
        queryKey: ['script-analysis-requests', selectedStatus],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (selectedStatus !== 'all') {
                params.append('status', selectedStatus.toUpperCase());
            }

            const response = await authenticatedFetch(
                `/api/analyzer/requests?${params.toString()}`
            );

            if (!response.ok) {
                throw new Error('Failed to load requests');
            }

            return response.json() as Promise<ScriptAnalysisRequest[]>;
        },
        staleTime: 30000, // 30 seconds
    });

    // Approve mutation
    const approveMutation = useMutation({
        mutationFn: async (requestId: string) => {
            const response = await authenticatedFetch(
                `/api/analyzer/requests/${requestId}/approve`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                }
            );

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Approval failed' }));
                throw new Error(error.detail || 'Approval failed');
            }

            return response.json();
        },
        onSuccess: () => {
            toast.success('Package approved successfully');
            queryClient.invalidateQueries({ queryKey: ['script-analysis-requests'] });
            onRefresh?.();
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : 'Approval failed';
            toast.error(message);
        },
    });

    // Reject mutation
    const rejectMutation = useMutation({
        mutationFn: async (requestId: string) => {
            const response = await authenticatedFetch(
                `/api/analyzer/requests/${requestId}/reject`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        reason: rejectReason || undefined,
                    }),
                }
            );

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Rejection failed' }));
                throw new Error(error.detail || 'Rejection failed');
            }

            return response.json();
        },
        onSuccess: () => {
            toast.success('Package rejected');
            setRejectDialogOpen(false);
            setSelectedRequestId(null);
            setRejectReason('');
            queryClient.invalidateQueries({ queryKey: ['script-analysis-requests'] });
            onRefresh?.();
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : 'Rejection failed';
            toast.error(message);
        },
    });

    const handleApprove = (requestId: string) => {
        approveMutation.mutate(requestId);
    };

    const handleRejectClick = (requestId: string) => {
        setSelectedRequestId(requestId);
        setRejectReason('');
        setRejectDialogOpen(true);
    };

    const handleRejectConfirm = () => {
        if (selectedRequestId) {
            rejectMutation.mutate(selectedRequestId);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    const pendingCount = requests.filter(r => r.status === 'PENDING').length;

    return (
        <div className="space-y-6">
            <Tabs
                value={selectedStatus}
                onValueChange={(val) => setSelectedStatus(val as any)}
            >
                <TabsList>
                    <TabsTrigger value="all">
                        All Requests
                        {requests.length > 0 && (
                            <Badge variant="secondary" className="ml-2">
                                {requests.length}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="pending">
                        Pending
                        {pendingCount > 0 && (
                            <Badge className="ml-2 bg-blue-600">
                                {pendingCount}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="approved">
                        Approved
                        {requests.filter(r => r.status === 'APPROVED').length > 0 && (
                            <Badge variant="secondary" className="ml-2">
                                {requests.filter(r => r.status === 'APPROVED').length}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="rejected">
                        Rejected
                        {requests.filter(r => r.status === 'REJECTED').length > 0 && (
                            <Badge variant="secondary" className="ml-2">
                                {requests.filter(r => r.status === 'REJECTED').length}
                            </Badge>
                        )}
                    </TabsTrigger>
                </TabsList>

                <TabsContent value={selectedStatus} className="space-y-4">
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : error ? (
                        <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex gap-3">
                            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
                            <div className="text-sm text-red-800 dark:text-red-300">
                                Failed to load requests
                            </div>
                        </div>
                    ) : requests.length === 0 ? (
                        <div className="text-center py-12">
                            <p className="text-muted-foreground">
                                {selectedStatus === 'pending'
                                    ? 'All caught up! No pending requests.'
                                    : 'No requests yet.'}
                            </p>
                        </div>
                    ) : (
                        <div className="border border-muted rounded-lg overflow-hidden">
                            <table className="w-full text-sm">
                                <thead className="bg-muted/50 border-b border-muted">
                                    <tr>
                                        <th className="px-4 py-3 text-left font-medium">Requester</th>
                                        <th className="px-4 py-3 text-left font-medium">Package</th>
                                        <th className="px-4 py-3 text-left font-medium">Ecosystem</th>
                                        <th className="px-4 py-3 text-left font-medium">Import/Command</th>
                                        <th className="px-4 py-3 text-left font-medium">Status</th>
                                        <th className="px-4 py-3 text-left font-medium">Requested</th>
                                        <th className="px-4 py-3 text-left font-medium">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-muted">
                                    {requests.map((request) => (
                                        <tr key={request.id} className="hover:bg-muted/50 transition-colors">
                                            <td className="px-4 py-3 font-medium text-sm">
                                                {request.requester_username || 'Unknown'}
                                            </td>
                                            <td className="px-4 py-3 font-medium">{request.package_name}</td>
                                            <td className="px-4 py-3">
                                                <Badge variant="outline">{request.ecosystem}</Badge>
                                            </td>
                                            <td className="px-4 py-3 text-xs text-muted-foreground">
                                                {request.detected_import}
                                            </td>
                                            <td className="px-4 py-3">
                                                {request.status === 'PENDING' && (
                                                    <Badge className="bg-blue-600">Pending</Badge>
                                                )}
                                                {request.status === 'APPROVED' && (
                                                    <Badge className="bg-green-600">Approved</Badge>
                                                )}
                                                {request.status === 'REJECTED' && (
                                                    <Badge className="bg-red-600">Rejected</Badge>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 text-xs text-muted-foreground">
                                                {formatDate(request.created_at)}
                                            </td>
                                            <td className="px-4 py-3">
                                                {request.status === 'PENDING' && (
                                                    <div className="flex gap-2">
                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            onClick={() => handleApprove(request.id)}
                                                            disabled={approveMutation.isPending}
                                                            className="text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-950/30"
                                                        >
                                                            {approveMutation.isPending ? (
                                                                <Loader2 className="h-3 w-3 animate-spin" />
                                                            ) : (
                                                                <Check className="h-3 w-3" />
                                                            )}
                                                            Approve
                                                        </Button>
                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            onClick={() => handleRejectClick(request.id)}
                                                            disabled={rejectMutation.isPending}
                                                            className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30"
                                                        >
                                                            {rejectMutation.isPending ? (
                                                                <Loader2 className="h-3 w-3 animate-spin" />
                                                            ) : (
                                                                <X className="h-3 w-3" />
                                                            )}
                                                            Reject
                                                        </Button>
                                                    </div>
                                                )}
                                                {request.status === 'APPROVED' && (
                                                    <div className="text-xs text-muted-foreground">
                                                        By {request.reviewed_by}
                                                        <br />
                                                        {request.reviewed_at && formatDate(request.reviewed_at)}
                                                    </div>
                                                )}
                                                {request.status === 'REJECTED' && (
                                                    <div
                                                        className="text-xs text-red-600 dark:text-red-400 cursor-help"
                                                        title={request.review_reason || 'No reason provided'}
                                                    >
                                                        Rejected by {request.reviewed_by}
                                                        {request.review_reason && (
                                                            <>
                                                                <br />
                                                                {request.review_reason}
                                                            </>
                                                        )}
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </TabsContent>
            </Tabs>

            {/* Reject Confirmation Dialog */}
            <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Reject Package Request</DialogTitle>
                        <DialogDescription>
                            Are you sure? The operator will see the rejection reason if provided.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        <Textarea
                            placeholder="Rejection reason (optional)"
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            className="h-24"
                        />
                    </div>

                    <DialogFooter className="gap-2">
                        <Button
                            variant="outline"
                            onClick={() => setRejectDialogOpen(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleRejectConfirm}
                            disabled={rejectMutation.isPending}
                            className="bg-red-600 hover:bg-red-700"
                        >
                            {rejectMutation.isPending ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Rejecting...
                                </>
                            ) : (
                                'Reject'
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};
