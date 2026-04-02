import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, Terminal } from 'lucide-react';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { authenticatedFetch } from '../auth';
import JobDefinitionList from '../components/job-definitions/JobDefinitionList';
import JobDefinitionModal from '../components/job-definitions/JobDefinitionModal';
import { ExecutionLogModal } from '../components/ExecutionLogModal';
import HealthTab from '../components/job-definitions/HealthTab';
import TemplatesTab from '../components/TemplatesTab';

interface EditingJob {
    id: string;
    name: string;
    script_content: string;
    signature_id: string;
    signature_payload: string;
    status: string;
    pushed_by: string | null;
    schedule_cron: string | null;
    target_node_id: string | null;
    target_tags: string[] | null;
    capability_requirements: Record<string, string> | null;
}

const EMPTY_FORM = {
    name: '',
    script_content: '',
    signature: '',
    signature_id: '',
    schedule_cron: '* * * * *',
    target_node_id: '',
    target_tags: '',
    capability_requirements: '',
    allow_overlap: false,
    dispatch_timeout_minutes: null as number | null,
};

const DefinitionHistoryPanel = ({ definitionId, onOpenRun }: {
    definitionId: string;
    onOpenRun: (jobRunId: string | null, executionId: number) => void;
}) => {
    const { data: executions, isLoading } = useQuery({
        queryKey: ['definition-history', definitionId],
        queryFn: async () => {
            const res = await authenticatedFetch(
                `/api/executions?scheduled_job_id=${definitionId}&limit=25`
            );
            return res.json() as Promise<any[]>;
        },
        enabled: !!definitionId,
    });

    const grouped = React.useMemo(() => {
        if (!executions) return [];
        const byRunId: Record<string, any[]> = {};
        const ungrouped: any[] = [];
        executions.forEach((ex: any) => {
            if (!ex.job_run_id) {
                ungrouped.push(ex);
            } else {
                if (!byRunId[ex.job_run_id]) byRunId[ex.job_run_id] = [];
                byRunId[ex.job_run_id].push(ex);
            }
        });
        const rows: any[] = [
            ...Object.values(byRunId).map(group => {
                const latest = [...group].sort((a, b) => (b.attempt_number ?? 0) - (a.attempt_number ?? 0))[0];
                return { ...latest, _attemptCount: group.length };
            }),
            ...ungrouped.map((ex: any) => ({ ...ex, _attemptCount: 1 })),
        ];
        return rows.sort((a, b) =>
            new Date(b.started_at ?? 0).getTime() - new Date(a.started_at ?? 0).getTime()
        );
    }, [executions]);

    if (isLoading) return <div className="py-8 text-center text-muted-foreground text-sm animate-pulse">Loading history...</div>;

    return (
        <div className="mt-4 rounded-xl border border-muted bg-zinc-950 overflow-hidden">
            <div className="px-4 py-3 border-b border-muted flex items-center gap-2">
                <Terminal className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-bold text-foreground">Execution History</span>
            </div>
            {grouped.length === 0 ? (
                <p className="py-8 text-center text-muted-foreground text-sm italic">No runs yet for this definition</p>
            ) : (
                <table className="w-full text-sm">
                    <thead className="bg-secondary/50">
                        <tr className="text-left text-muted-foreground text-xs font-bold uppercase tracking-wider">
                            <th className="px-4 py-2">When</th>
                            <th className="px-4 py-2">Node</th>
                            <th className="px-4 py-2">Status</th>
                            <th className="px-4 py-2">Duration</th>
                            <th className="px-4 py-2">Retry</th>
                            <th className="px-4 py-2 text-right">Logs</th>
                        </tr>
                    </thead>
                    <tbody>
                        {grouped.map((row: any) => {
                            const showRetryBadge = (row.max_retries ?? 0) > 1 && (row._attemptCount ?? 1) > 1;
                            const isRetrying = row.status === 'RETRYING';
                            const isFailedExhausted = row.status === 'FAILED' && row.attempt_number === (row.max_retries ?? 0) + 1;
                            return (
                                <tr key={row.id} className="border-t border-zinc-900 hover:bg-secondary/30 transition-colors">
                                    <td className="px-4 py-2 text-muted-foreground whitespace-nowrap tabular-nums text-xs">
                                        {row.started_at ? formatDistanceToNow(new Date(row.started_at), { addSuffix: true }) : '—'}
                                    </td>
                                    <td className="px-4 py-2 text-muted-foreground text-xs font-mono">{row.node_id || 'N/A'}</td>
                                    <td className="px-4 py-2">
                                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                                            row.status === 'COMPLETED' ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                                            row.status === 'FAILED' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                                            row.status === 'RETRYING' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' :
                                            'bg-muted text-muted-foreground border-muted'
                                        }`}>{row.status}</span>
                                    </td>
                                    <td className="px-4 py-2 text-muted-foreground tabular-nums text-xs">
                                        {row.duration_seconds != null ? `${row.duration_seconds.toFixed(1)}s` : '—'}
                                    </td>
                                    <td className="px-4 py-2">
                                        {showRetryBadge && (
                                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                                                isRetrying ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                                                : isFailedExhausted ? 'bg-red-500/10 text-red-500 border-red-500/20'
                                                : 'bg-muted text-muted-foreground border-muted'
                                            }`}>
                                                {isRetrying
                                                    ? `Attempt ${row.attempt_number} of ${(row.max_retries ?? 0) + 1}`
                                                    : `Failed ${row.attempt_number}/${(row.max_retries ?? 0) + 1}`}
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 text-right">
                                        <button
                                            onClick={() => onOpenRun(row.job_run_id, row.id)}
                                            className="text-xs text-primary hover:text-primary/80 font-bold flex items-center gap-1 ml-auto"
                                        >
                                            <Terminal className="h-3 w-3" /> Logs
                                        </button>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            )}
        </div>
    );
};

const JobDefinitions = () => {
    const [definitions, setDefinitions] = useState([]);
    const [executions, setExecutions] = useState([]);
    const [signatures, setSignatures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingJob, setEditingJob] = useState<EditingJob | null>(null);
    const [activeTab, setActiveTab] = useState<'active' | 'staging'>('active');
    const [selectedDefId, setSelectedDefId] = useState<string | null>(null);
    const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
    const [selectedExId, setSelectedExId] = useState<number | null>(null);
    const [showLogModal, setShowLogModal] = useState(false);

    const [formData, setFormData] = useState(EMPTY_FORM);
    const [showDraftWarning, setShowDraftWarning] = useState(false);
    const [pendingDraftSave, setPendingDraftSave] = useState<(() => void) | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [defRes, execRes, sigRes] = await Promise.all([
                authenticatedFetch('/jobs/definitions'),
                authenticatedFetch('/jobs'),
                authenticatedFetch('/signatures')
            ]);

            if (defRes.ok) { const d = await defRes.json(); setDefinitions(Array.isArray(d) ? d : (d.items ?? [])); }
            if (execRes.ok) { const d = await execRes.json(); setExecutions(Array.isArray(d) ? d : (d.items ?? [])); }
            if (sigRes.ok) { const d = await sigRes.json(); setSignatures(Array.isArray(d) ? d : (d.items ?? [])); }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            const res = await authenticatedFetch(`/jobs/definitions/${id}`, { method: 'DELETE' });
            if (res.ok) loadData();
        } catch (e) {
            console.error(e);
        }
    };

    const handleToggle = async (id: string) => {
        try {
            const res = await authenticatedFetch(`/jobs/definitions/${id}/toggle`, { method: 'PATCH' });
            if (res.ok) loadData();
        } catch (e) {
            console.error(e);
        }
    };

    const handleEdit = async (id: string) => {
        try {
            const res = await authenticatedFetch(`/jobs/definitions/${id}`);
            if (!res.ok) {
                const err = await res.json();
                toast.error(err.detail || 'Failed to load job definition');
                return;
            }
            const data = await res.json();
            setEditingJob(data);
            setShowModal(true);
        } catch (e) {
            console.error(e);
            toast.error('Failed to load job definition');
        }
    };

    const buildPayload = () => {
        const tags = formData.target_tags.trim()
            ? formData.target_tags.split(',').map(t => t.trim()).filter(Boolean)
            : undefined;
        const caps = formData.capability_requirements.trim()
            ? Object.fromEntries(
                formData.capability_requirements.split(',')
                    .map(s => s.trim().split(':').map(p => p.trim()))
                    .filter(parts => parts.length === 2 && parts[0])
              )
            : undefined;
        return { ...formData, target_tags: tags, capability_requirements: caps };
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (editingJob) {
            const scriptChanged = formData.script_content !== editingJob.script_content;
            const sigUnchanged = formData.signature === editingJob.signature_payload;
            console.log('[DRAFT]', scriptChanged, sigUnchanged, '|', formData.script_content?.substring(0,25), '|', editingJob.script_content?.substring(0,25), '|', formData.signature?.substring(0,15), '|', editingJob.signature_payload?.substring(0,15));
            if (scriptChanged && sigUnchanged) {
                setPendingDraftSave(() => () => handleUpdate(editingJob.id, { signature: undefined, signature_id: undefined }));
                setShowDraftWarning(true);
                return;
            }
            await handleUpdate(editingJob.id);
            return;
        }
        try {
            const res = await authenticatedFetch('/jobs/definitions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(buildPayload())
            });
            if (res.ok) {
                toast.success('Job definition created successfully');
                closeModal();
                loadData();
            } else {
                const err = await res.json();
                toast.error(err.detail || 'Failed to create job definition');
            }
        } catch (e) {
            console.error(e);
            toast.error('Submission Error');
        }
    };

    const handleUpdate = async (id: string, overrides?: Record<string, unknown>) => {
        try {
            const payload = overrides ? { ...buildPayload(), ...overrides } : buildPayload();
            const res = await authenticatedFetch(`/jobs/definitions/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                toast.success('Job definition updated successfully');
                closeModal();
                loadData();
            } else {
                const err = await res.json();
                toast.error(err.detail || 'Failed to update job definition');
            }
        } catch (e) {
            console.error(e);
            toast.error('Update Error');
        }
    };

    const handleResign = async (id: string, signatureId: string, signature: string) => {
        try {
            const res = await authenticatedFetch(`/jobs/definitions/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ signature_id: signatureId, signature }),
            });
            if (res.ok) {
                toast.success('Job re-signed and reactivated');
                loadData();
            } else {
                const err = await res.json();
                toast.error(err.detail || 'Re-sign failed');
            }
        } catch (e) {
            toast.error('Re-sign error');
        }
    };

    const handlePublish = async (id: string) => {
        try {
            const res = await authenticatedFetch(`/jobs/definitions/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'ACTIVE' })
            });
            if (res.ok) {
                toast.success('Job published successfully');
                loadData();
            } else {
                const err = await res.json();
                toast.error(err.detail || 'Failed to publish job');
            }
        } catch (e) {
            console.error(e);
            toast.error('Publish Error');
        }
    };

    const handleSelectDef = (id: string) => setSelectedDefId(prev => prev === id ? null : id);

    const openCreateModal = () => {
        setEditingJob(null);
        setFormData(EMPTY_FORM);
        setShowModal(true);
    };

    const closeModal = () => {
        setShowModal(false);
        setEditingJob(null);
    };

    const filteredDefinitions = definitions.filter(def => {
        if (activeTab === 'active') {
            return def.status !== 'DRAFT';
        } else {
            return def.status === 'DRAFT';
        }
    });

    if (loading) return (
        <div className="space-y-4">
            <div className="h-10 w-48 bg-secondary border border-muted rounded-lg animate-pulse" />
            <div className="h-64 bg-secondary border border-muted rounded-lg animate-pulse" />
        </div>
    );

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-foreground">Scheduled Jobs</h1>
                    <p className="text-sm text-muted-foreground mt-1">Signed, zero-trust recurring payloads.</p>
                </div>
            </div>

            <Tabs defaultValue="definitions">
                <TabsList>
                    <TabsTrigger value="definitions">Definitions</TabsTrigger>
                    <TabsTrigger value="health">Health</TabsTrigger>
                    <TabsTrigger value="templates">Templates</TabsTrigger>
                </TabsList>

                <TabsContent value="definitions">
                    <div className="space-y-4 mt-4">
                        <div className="flex items-center gap-2">
                            <div className="bg-secondary/50 p-1 rounded-xl border border-muted flex mr-4">
                                <button
                                    onClick={() => setActiveTab('active')}
                                    className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === 'active' ? 'bg-muted text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
                                >
                                    ACTIVE
                                </button>
                                <button
                                    onClick={() => setActiveTab('staging')}
                                    className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === 'staging' ? 'bg-muted text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
                                >
                                    STAGING
                                </button>
                            </div>
                            <Button onClick={openCreateModal} className="bg-primary hover:bg-primary/90 text-foreground font-bold h-11 px-6 rounded-xl shadow-lg shadow-primary/10">
                                <Plus className="mr-2 h-4 w-4" />
                                Archive New Payload
                            </Button>
                        </div>

                        <JobDefinitionList
                            definitions={filteredDefinitions}
                            executions={executions}
                            onDelete={handleDelete}
                            onToggle={handleToggle}
                            onEdit={handleEdit}
                            onPublish={handlePublish}
                            onResign={handleResign}
                            signatures={signatures}
                            selectedDefId={selectedDefId}
                            onSelect={handleSelectDef}
                        />

                        {selectedDefId && (
                            <DefinitionHistoryPanel
                                definitionId={selectedDefId}
                                onOpenRun={(jobRunId, executionId) => {
                                    setSelectedRunId(jobRunId);
                                    setSelectedExId(executionId);
                                    setShowLogModal(true);
                                }}
                            />
                        )}
                        <ExecutionLogModal
                            jobRunId={selectedRunId ?? undefined}
                            executionId={!selectedRunId ? (selectedExId ?? undefined) : undefined}
                            open={showLogModal}
                            onClose={() => { setShowLogModal(false); setSelectedRunId(null); setSelectedExId(null); }}
                        />
                    </div>
                </TabsContent>

                <TabsContent value="health">
                    <div className="mt-4">
                        <HealthTab />
                    </div>
                </TabsContent>

                <TabsContent value="templates">
                    <div className="mt-4">
                        <TemplatesTab />
                    </div>
                </TabsContent>
            </Tabs>

            <Dialog open={showDraftWarning} onOpenChange={(open) => { if (!open) setShowDraftWarning(false); }}>
                <DialogContent className="max-w-md bg-zinc-950 border-muted">
                    <DialogHeader>
                        <DialogTitle className="text-foreground">Script Change Will Require Re-signing</DialogTitle>
                        <DialogDescription className="text-muted-foreground">
                            <span className="font-semibold text-foreground">{editingJob?.name}</span> — cron fires will be
                            blocked until re-signed. Use the Re-sign button in the job list to reactivate.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="gap-2">
                        <Button
                            variant="ghost"
                            onClick={() => setShowDraftWarning(false)}
                            className="text-muted-foreground hover:text-foreground"
                        >
                            Cancel
                        </Button>
                        <Button
                            className="bg-amber-500 hover:bg-amber-600 text-foreground font-bold"
                            onClick={() => {
                                setShowDraftWarning(false);
                                pendingDraftSave?.();
                            }}
                        >
                            Save &amp; Go to DRAFT
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <JobDefinitionModal
                isOpen={showModal}
                onClose={(open) => { if (!open) closeModal(); }}
                onSubmit={handleSubmit}
                formData={formData}
                setFormData={setFormData}
                signatures={signatures}
                editingJob={editingJob}
            />
        </div>
    );
};

export default JobDefinitions;
