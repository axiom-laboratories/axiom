import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../auth';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const Dashboard = () => {
    const [stats, setStats] = useState({ activeNodes: 0, runningJobs: 0, successRate: 100 });
    const [recentJobs, setRecentJobs] = useState([]);
    const [chartData, setChartData] = useState([]);

    const loadData = async () => {
        try {
            // Parallel Fetch
            const [nodesRes, jobsRes] = await Promise.all([
                authenticatedFetch('/nodes'),
                authenticatedFetch('/jobs')
            ]);

            if (nodesRes.ok && jobsRes.ok) {
                const nodes = await nodesRes.json();
                const jobs = await jobsRes.json();

                // Calculate Metrics
                const onlineNodes = nodes.filter(n => n.status === 'ONLINE').length;
                const runningJobs = jobs.filter(j => j.status === 'ASSIGNED' || j.status === 'PENDING').length;
                const completed = jobs.filter(j => j.status === 'COMPLETED').length;
                const failed = jobs.filter(j => j.status === 'FAILED').length;
                const total = completed + failed;
                const rate = total > 0 ? Math.round((completed / total) * 100) : 100;

                setStats({ activeNodes: onlineNodes, runningJobs, successRate: rate });
                setRecentJobs(jobs.slice(0, 5));

                // Mock Chart Data (Real data would need aggregation endpoint)
                setChartData([
                    { name: 'Mon', failures: 2 },
                    { name: 'Tue', failures: 0 },
                    { name: 'Wed', failures: 1 },
                    { name: 'Thu', failures: 5 },
                    { name: 'Fri', failures: failed }, // Use today's count
                ]);
            }
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div>
            <h1>Control Panel</h1>
            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '30px' }}>
                <div className="card kpi">
                    <h3>Active Puppets</h3>
                    <div className="value">{stats.activeNodes}</div>
                </div>
                <div className="card kpi">
                    <h3>Running Jobs</h3>
                    <div className="value">{stats.runningJobs}</div>
                </div>
                <div className="card kpi">
                    <h3>Success Rate</h3>
                    <div className="value">{stats.successRate}%</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
                {/* Chart */}
                <div className="card">
                    <h3>Failure Trend (7 Days)</h3>
                    <div style={{ height: '300px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData}>
                                <XAxis dataKey="name" stroke="#888" />
                                <YAxis stroke="#888" />
                                <Tooltip contentStyle={{ backgroundColor: '#333' }} />
                                <Bar dataKey="failures" fill="#ff4444" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Recent Activity */}
                <div className="card">
                    <h3>Recent Activity</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {recentJobs.map(job => (
                            <div key={job.guid} style={{ padding: '10px', backgroundColor: '#333', borderRadius: '4px', fontSize: '0.9rem' }}>
                                <span className={`badge ${job.status.toLowerCase()}`}>{job.status}</span>
                                <span style={{ marginLeft: '10px' }}>{job.payload.task_type || 'Job'}</span>
                                <div style={{ fontSize: '0.8rem', color: '#888', marginTop: '5px' }}>
                                    {new Date(job.started_at || Date.now()).toLocaleTimeString()}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
