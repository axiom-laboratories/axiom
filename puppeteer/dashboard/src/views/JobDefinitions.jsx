import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../auth';
import { Link } from 'react-router-dom';

const JobDefinitions = () => {
    const [definitions, setDefinitions] = useState([]);
    const [executions, setExecutions] = useState([]);
    const [signatures, setSignatures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    // Form Data
    const [formData, setFormData] = useState({
        name: '',
        script_content: '',
        signature: '', // B64
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

            if (defRes.ok) setDefinitions(await defRes.json());
            if (execRes.ok) setExecutions(await execRes.json());
            if (sigRes.ok) setSignatures(await sigRes.json());
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    const getSparklineData = (defId) => {
        // Filter executions for this def, sort by date desc, take 30
        const related = executions
            .filter(e => e.scheduled_job_id === defId)
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .slice(0, 30)
            .reverse(); // Oldest to newest for chart

        return related;
    };

    const renderSparkline = (data) => {
        if (!data.length) return <span className="text-muted">No History</span>;

        return (
            <div style={{ display: 'flex', alignItems: 'flex-end', height: '20px', gap: '2px' }}>
                {data.map((run, i) => {
                    const color = run.status === 'COMPLETED' ? '#4caf50' : (run.status === 'FAILED' ? '#f44336' : '#ff9800');
                    const height = run.status === 'COMPLETED' ? '100%' : '50%';
                    return (
                        <div key={i} title={`${run.status} - ${new Date(run.created_at).toLocaleString()}`}
                            style={{ width: '4px', height, backgroundColor: color, borderRadius: '2px' }}></div>
                    );
                })}
            </div>
        );
    };

    const handleSubmit = async (e) => {
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
        } catch (e) { console.error(e); alert("Submission Error"); }
    };

    if (loading) return <div>Loading...</div>;

    return (
        <div className="container-fluid p-4">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <h2>⚡ Scheduled Jobs</h2>
                <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ New Job</button>
            </div>

            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <table className="table table-dark table-hover mb-0">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Schedule</th>
                            <th>Active</th>
                            <th>Last Runs (30d)</th>
                            <th>Created</th>
                        </tr>
                    </thead>
                    <tbody>
                        {definitions.map(def => (
                            <tr key={def.id}>
                                <td>{def.name}</td>
                                <td><code>{def.schedule_cron || 'Manual'}</code></td>
                                <td>{def.is_active ? '✅' : '❌'}</td>
                                <td>{renderSparkline(getSparklineData(def.id))}</td>
                                <td>{new Date(def.created_at).toLocaleDateString()}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {showModal && (
                <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.8)' }}>
                    <div className="modal-dialog modal-lg modal-dialog-centered">
                        <div className="modal-content" style={{ backgroundColor: '#1e1e1e' }}>
                            <div className="modal-header">
                                <h5 className="modal-title">Create Scheduled Job (Signed)</h5>
                            </div>
                            <div className="modal-body">
                                <form onSubmit={handleSubmit}>
                                    <div className="row">
                                        <div className="col-md-6 mb-3">
                                            <label>Job Name</label>
                                            <input className="form-control" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} required />
                                        </div>
                                        <div className="col-md-6 mb-3">
                                            <label>Cron Schedule</label>
                                            <input className="form-control" value={formData.schedule_cron} onChange={e => setFormData({ ...formData, schedule_cron: e.target.value })} placeholder="* * * * *" />
                                        </div>
                                    </div>

                                    <div className="mb-3">
                                        <label>Python Script</label>
                                        <textarea className="form-control" rows="5" value={formData.script_content} onChange={e => setFormData({ ...formData, script_content: e.target.value })} required style={{ fontFamily: 'monospace' }}></textarea>
                                    </div>

                                    <div className="row">
                                        <div className="col-md-6 mb-3">
                                            <label>Signature Identity (Public Key)</label>
                                            <select className="form-control" value={formData.signature_id} onChange={e => setFormData({ ...formData, signature_id: e.target.value })} required>
                                                <option value="">Select Key...</option>
                                                {signatures.map(s => <option key={s.id} value={s.id}>{s.name} ({s.uploaded_by})</option>)}
                                            </select>
                                        </div>
                                        <div className="col-md-6 mb-3">
                                            <label>Target Node (Optional)</label>
                                            <input className="form-control" value={formData.target_node_id} onChange={e => setFormData({ ...formData, target_node_id: e.target.value })} placeholder="Leave empty for dynamic/all" />
                                        </div>
                                    </div>

                                    <div className="mb-3">
                                        <label>Signature Payload (Base64) - MUST match Script & Key</label>
                                        <textarea className="form-control" rows="2" value={formData.signature} onChange={e => setFormData({ ...formData, signature: e.target.value })} required placeholder="Paste output of signing tool..." style={{ fontFamily: 'monospace' }}></textarea>
                                        <small className="text-muted">Use <code>openssl</code> or <code>libsodium</code> to sign the script content exactly as pasted above.</small>
                                    </div>

                                    <div className="d-flex justify-content-end gap-2">
                                        <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                                        <button type="submit" className="btn btn-primary">Create & Verify</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default JobDefinitions;
