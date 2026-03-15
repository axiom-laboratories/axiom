import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { authenticatedFetch } from '../auth';
import JobDefinitionList from '../components/job-definitions/JobDefinitionList';
import JobDefinitionModal from '../components/job-definitions/JobDefinitionModal';

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
};

const JobDefinitions = () => {
    const [definitions, setDefinitions] = useState([]);
    const [executions, setExecutions] = useState([]);
    const [signatures, setSignatures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingJob, setEditingJob] = useState<EditingJob | null>(null);
    const [activeTab, setActiveTab] = useState<'active' | 'staging'>('active');

    const [formData, setFormData] = useState(EMPTY_FORM);

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

            if (defRes.ok) setDefinitions(await defRes.ok ? await defRes.json() : []);
            if (execRes.ok) setExecutions(await execRes.ok ? await execRes.json() : []);
            if (sigRes.ok) setSignatures(await sigRes.ok ? await sigRes.json() : []);
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

    const handleUpdate = async (id: string) => {
        try {
            const res = await authenticatedFetch(`/jobs/definitions/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(buildPayload())
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
            <div className="h-10 w-48 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
            <div className="h-64 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
        </div>
    );

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-white">Scheduled Jobs</h1>
                    <p className="text-sm text-zinc-500 mt-1">Signed, zero-trust recurring payloads.</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="bg-zinc-900/50 p-1 rounded-xl border border-zinc-800 flex mr-4">
                        <button
                            onClick={() => setActiveTab('active')}
                            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === 'active' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-500 hover:text-zinc-300'}`}
                        >
                            ACTIVE
                        </button>
                        <button
                            onClick={() => setActiveTab('staging')}
                            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === 'staging' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-500 hover:text-zinc-300'}`}
                        >
                            STAGING
                        </button>
                    </div>
                    <Button onClick={openCreateModal} className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-6 rounded-xl shadow-lg shadow-primary/10">
                        <Plus className="mr-2 h-4 w-4" />
                        Archive New Payload
                    </Button>
                </div>
            </div>

            <JobDefinitionList 
                definitions={filteredDefinitions} 
                executions={executions} 
                onDelete={handleDelete} 
                onToggle={handleToggle} 
                onEdit={handleEdit} 
                onPublish={handlePublish}
            />

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
