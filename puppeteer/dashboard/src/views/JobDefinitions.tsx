import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { authenticatedFetch } from '../auth';
import JobDefinitionList from '../components/job-definitions/JobDefinitionList';
import JobDefinitionModal from '../components/job-definitions/JobDefinitionModal';

const JobDefinitions = () => {
    const [definitions, setDefinitions] = useState([]);
    const [executions, setExecutions] = useState([]);
    const [signatures, setSignatures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    const [formData, setFormData] = useState({
        name: '',
        script_content: '',
        signature: '',
        signature_id: '',
        schedule_cron: '* * * * *',
        target_node_id: '',
        target_tags: '',
        capability_requirements: '',
    });

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

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
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
            const body = {
                ...formData,
                target_tags: tags,
                capability_requirements: caps,
            };
            const res = await authenticatedFetch('/jobs/definitions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (res.ok) {
                toast.success('Job definition created successfully');
                setShowModal(false);
                loadData();
            } else {
                const err = await res.json();
                toast.error(err.detail || 'Failed to create job definition');
            }
        } catch (e) {
            console.error(e);
            toast.error("Submission Error");
        }
    };

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
                <Button onClick={() => setShowModal(true)} className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-6 rounded-xl shadow-lg shadow-primary/10">
                    <Plus className="mr-2 h-4 w-4" />
                    Archive New Payload
                </Button>
            </div>

            <JobDefinitionList definitions={definitions} executions={executions} onDelete={handleDelete} onToggle={handleToggle} />

            <JobDefinitionModal
                isOpen={showModal}
                onClose={setShowModal}
                onSubmit={handleSubmit}
                formData={formData}
                setFormData={setFormData}
                signatures={signatures}
            />
        </div>
    );
};

export default JobDefinitions;
