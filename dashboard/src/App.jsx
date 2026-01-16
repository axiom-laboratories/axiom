import { useState, useEffect } from 'react';
import './index.css';

function App() {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(false);

    const fetchJobs = async () => {
        try {
            const res = await fetch('https://localhost:8001/jobs');
            const data = await res.json();
            setJobs(data);
        } catch (e) {
            console.error("Failed to fetch jobs:", e);
        }
    };

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 2000); // Real-time polling
        return () => clearInterval(interval);
    }, []);

    const createJob = async () => {
        setLoading(true);
        try {
            await fetch('https://localhost:8000/submit_intent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-KEY': 'master-secret-key'
                },
                body: JSON.stringify({
                    task_type: 'web_task',
                    payload: {
                        message: `Task created at ${new Date().toLocaleTimeString()}`,
                        params: { a: 1, b: 2 }
                    },
                    priority: Math.floor(Math.random() * 10)
                })
            });
            // Immediate fetch after create
            setTimeout(fetchJobs, 500);
        } catch (e) {
            console.error("Failed to create job:", e);
            alert("Failed to submit intent to Model Service");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container">
            <header className="header">
                <h1>Orchestrator Control</h1>
                <div className="status-badge">
                    System: <span className="online">ONLINE</span>
                </div>
            </header>

            <main>
                <div className="controls">
                    <button
                        className="btn-primary"
                        onClick={createJob}
                        disabled={loading}
                    >
                        {loading ? 'Submitting...' : '+ New Intent'}
                    </button>
                </div>

                <div className="job-grid">
                    {jobs.length === 0 && <p className="empty-state">No active jobs.</p>}
                    {jobs.map(job => (
                        <div key={job.guid} className={`job-card status-${job.status.toLowerCase()}`}>
                            <div className="card-header">
                                <span className="guid">{job.guid.split('-')[0]}...</span>
                                <span className={`badge ${job.status.toLowerCase()}`}>{job.status}</span>
                            </div>
                            <div className="card-body">
                                <pre>{JSON.stringify(job.payload, null, 2)}</pre>
                            </div>
                            {job.result && (
                                <div className="card-footer">
                                    <strong>Result:</strong>
                                    <pre>{JSON.stringify(job.result, null, 2)}</pre>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </main>
        </div>
    );
}

export default App;
