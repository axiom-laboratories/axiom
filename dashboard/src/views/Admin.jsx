import { useState } from 'react';
import { authenticatedFetch } from '../auth';

const Admin = () => {
    const [joinToken, setJoinToken] = useState(null);
    const [pubKey, setPubKey] = useState('');

    // Generate Token
    const generateToken = async () => {
        const res = await authenticatedFetch('https://localhost:8001/admin/generate-token', { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            setJoinToken(data.token);
        } else {
            alert('Failed to generate token (Requires Admin/Operator Role)');
        }
    };

    // Upload Key
    const uploadKey = async () => {
        const res = await authenticatedFetch('https://localhost:8001/admin/upload-key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key_content: pubKey })
        });
        if (res.ok) {
            alert('Key Stored Successfully');
            setPubKey('');
        } else {
            alert('Failed to upload key (Requires Admin Role)');
        }
    };

    return (
        <div>
            <h1>Admin Console</h1>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                {/* Node Onboarding */}
                <div className="card">
                    <h3>🖥 Node Onboarding</h3>
                    <p style={{ color: '#aaa', fontSize: '0.9rem' }}>
                        Generate a secure One-Time Token for new nodes to join the mesh.
                    </p>
                    <button className="btn-primary" onClick={generateToken} style={{ marginTop: '10px' }}>
                        Generate Join Token
                    </button>

                    {joinToken && (
                        <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#222', border: '1px solid #4caf50', borderRadius: '4px' }}>
                            <div style={{ color: '#888', marginBottom: '5px' }}>NEW TOKEN GENERATED:</div>
                            <code style={{ color: '#4caf50', fontSize: '1.2rem' }}>{joinToken}</code>
                            <div style={{ marginTop: '10px', fontSize: '0.8rem', color: '#aaa' }}>
                                Use this token in the Installer Wizard or Environment Variables.
                            </div>
                        </div>
                    )}
                </div>

                {/* Key Management */}
                <div className="card">
                    <h3>🔐 Code Signing Keys</h3>
                    <p style={{ color: '#aaa', fontSize: '0.9rem' }}>
                        Rotate the Master Public Key for script verification.
                    </p>
                    <textarea
                        value={pubKey}
                        onChange={e => setPubKey(e.target.value)}
                        placeholder="Paste Public PEM Key here..."
                        style={{ width: '100%', height: '150px', backgroundColor: '#222', color: '#0f0', border: '1px solid #444', fontFamily: 'monospace', margin: '10px 0' }}
                    />
                    <button className="btn-primary" onClick={uploadKey}>Upload New Key</button>
                </div>
            </div>
        </div>
    );
};

export default Admin;
