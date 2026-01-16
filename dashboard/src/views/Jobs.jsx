import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../auth';

const Jobs = () => {
    const [jobs, setJobs] = useState([]);
    const [newTaskType, setNewTaskType] = useState('web_task');
    const [newTaskPayload, setNewTaskPayload] = useState('{}');

    const fetchJobs = async () => {
        try {
            const res = await authenticatedFetch('https://localhost:8001/jobs');
            if (res.ok) {
                setJobs(await res.json());
            }
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 3000);
        return () => clearInterval(interval);
    }, []);

    const createJob = async () => {
        try {
            const payload = JSON.parse(newTaskPayload);
            const res = await authenticatedFetch('https://localhost:8001/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task_type: newTaskType,
                    payload: payload
                })
            });
            if (res.ok) {
                fetchJobs();
                alert('Job Submitted');
            } else {
                alert('Failed to submit job');
            }
        } catch (e) {
            alert('Invalid JSON Payload');
        }
    };

    return (
        <div>
            <h1>Task Queue</h1>

            {/* Create Job Box */}
            <div className="card" style={{ marginBottom: '20px' }}>
                <h3>Submit New Job</h3>
                <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                    <select
                        value={newTaskType}
                        onChange={(e) => setNewTaskType(e.target.value)}
                        style={{ padding: '8px', backgroundColor: '#333', color: '#fff', border: 'none' }}
                    >
                        <option value="web_task">Web Task</option>
                        <option value="python_script">Python Script</option>
                        <option value="file_download">File Download</option>
                    </select>
                    <button className="btn-primary" onClick={createJob}>Submit Job</button>
                </div>
                <textarea
                    value={newTaskPayload}
                    onChange={(e) => setNewTaskPayload(e.target.value)}
                    style={{ width: '100%', height: '100px', backgroundColor: '#222', color: '#0f0', border: '1px solid #444', fontFamily: 'monospace' }}
                />
            </div>

            {/* Jobs Table */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead style={{ backgroundColor: '#222', color: '#888' }}>
                        <tr>
                            <th style={{ padding: '15px' }}>GUID</th>
                            <th>Type</th>
                            <th>Status</th>
                            <th>Node</th>
                            <th>Started</th>
                            <th>Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        {jobs.map(job => (
                            <tr key={job.guid} style={{ borderBottom: '1px solid #333' }}>
                                <td style={{ padding: '15px', fontFamily: 'monospace', color: '#aaa' }}>{job.guid.substring(0, 8)}...</td>
                                <td>{job.payload.task_type || job.task_type || 'Generic'}</td>
                                <td>
                                    <span className={`badge ${job.status.toLowerCase()}`}>{job.status}</span>
                                </td>
                                <td style={{ fontFamily: 'monospace' }}>{job.node_id ? job.node_id.substring(0, 15) : '-'}</td>
                                <td>{job.started_at ? new Date(job.started_at).toLocaleTimeString() : '-'}</td>
                                <td>{job.duration_seconds ? `${job.duration_seconds.toFixed(2)}s` : '-'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default Jobs;
