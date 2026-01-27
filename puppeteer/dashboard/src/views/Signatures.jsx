import { useState, useEffect } from 'react';
import { authenticatedFetch, getUser } from '../auth';

const Signatures = () => {
    const [signatures, setSignatures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [formData, setFormData] = useState({ name: '', public_key: '' });
    const user = getUser();

    useEffect(() => {
        loadSignatures();
    }, []);

    const loadSignatures = async () => {
        try {
            const res = await authenticatedFetch('/signatures');
            if (res.ok) {
                setSignatures(await res.json());
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id) => {
        if (!confirm("Are you sure? Jobs using this key will fail validation.")) return;
        try {
            const res = await authenticatedFetch(`/signatures/${id}`, {
                method: 'DELETE'
            });
            if (res.ok) loadSignatures();
        } catch (e) { console.error(e); }
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        try {
            const res = await authenticatedFetch('/signatures', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            if (res.ok) {
                setShowModal(false);
                setFormData({ name: '', public_key: '' });
                loadSignatures();
            } else {
                alert("Upload Failed");
            }
        } catch (e) { console.error(e); }
    };

    if (loading) return <div>Loading...</div>;
    if (user?.role !== 'admin') return <div className="p-4"><h3>Access Denied (Admin Only)</h3></div>;

    return (
        <div className="container-fluid p-4">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <h2>🔐 Signature Registry</h2>
                <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ Upload Key</button>
            </div>

            <div className="card-grid">
                {signatures.map(sig => (
                    <div key={sig.id} className="card p-3 mb-3" style={{ backgroundColor: '#1e1e1e', border: '1px solid #333' }}>
                        <h4>{sig.name}</h4>
                        <div className="text-muted small">Uploaded by: {sig.uploaded_by}</div>
                        <div className="text-muted small">ID: {sig.id}</div>
                        <pre style={{ maxHeight: '100px', overflow: 'hidden', backgroundColor: '#000', padding: '5px', marginTop: '10px' }}>
                            {sig.public_key}
                        </pre>
                        <button className="btn btn-danger btn-sm mt-2" onClick={() => handleDelete(sig.id)}>Delete</button>
                    </div>
                ))}
                {signatures.length === 0 && <p className="text-muted">No trusted keys found.</p>}
            </div>

            {showModal && (
                <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.8)' }}>
                    <div className="modal-dialog modal-dialog-centered">
                        <div className="modal-content" style={{ backgroundColor: '#1e1e1e' }}>
                            <div className="modal-header">
                                <h5 className="modal-title">Upload Public Key (PEM)</h5>
                            </div>
                            <div className="modal-body">
                                <form onSubmit={handleUpload}>
                                    <div className="mb-3">
                                        <label>Name</label>
                                        <input className="form-control" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} required placeholder="e.g. DevOps Pipeline" />
                                    </div>
                                    <div className="mb-3">
                                        <label>Public Key (PEM)</label>
                                        <textarea className="form-control" rows="5" value={formData.public_key} onChange={e => setFormData({ ...formData, public_key: e.target.value })} required placeholder="-----BEGIN PUBLIC KEY-----..." style={{ fontFamily: 'monospace' }}></textarea>
                                    </div>
                                    <div className="d-flex justify-content-end gap-2">
                                        <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                                        <button type="submit" className="btn btn-primary">Upload</button>
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

export default Signatures;
