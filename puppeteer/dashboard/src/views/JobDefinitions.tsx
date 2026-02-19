import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
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
        target_node_id: ''
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

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const res = await authenticatedFetch('/jobs/definitions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            if (res.ok) {
                setShowModal(false);
                loadData();
            } else {
                const err = await res.json();
                alert(`Error: ${err.detail}`);
            }
        } catch (e) {
            console.error(e);
            alert("Submission Error");
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
                    <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Immutable Schedules</h1>
                    <p className="text-zinc-500">Centrally signed Python payloads with zero-trust execution verification.</p>
                </div>
                <Button onClick={() => setShowModal(true)} className="bg-primary hover:bg-primary/90 text-white font-bold h-11 px-6 rounded-xl shadow-lg shadow-primary/10">
                    <Plus className="mr-2 h-4 w-4" />
                    Archive New Payload
                </Button>
            </div>

            <JobDefinitionList definitions={definitions} executions={executions} />

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
