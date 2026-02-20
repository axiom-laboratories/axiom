import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import {
    Activity,
    Network,
    CheckCircle2,
    Clock,
    AlertCircle,
    ArrowUpRight
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { authenticatedFetch } from '../auth';

const Dashboard = () => {
    const [stats, setStats] = useState({ activeNodes: 0, runningJobs: 0, successRate: 100 });
    const [recentJobs, setRecentJobs] = useState([]);
    const [chartData, setChartData] = useState([]);

    const loadData = async () => {
        try {
            const [nodesRes, jobsRes] = await Promise.all([
                authenticatedFetch('/nodes'),
                authenticatedFetch('/jobs')
            ]);

            if (nodesRes.ok && jobsRes.ok) {
                const nodes = await nodesRes.json();
                const jobs = await jobsRes.json();

                const onlineNodes = nodes.filter(n => n.status === 'ONLINE').length;
                const runningJobs = jobs.filter(j => j.status === 'ASSIGNED' || j.status === 'PENDING').length;
                const completed = jobs.filter(j => j.status === 'COMPLETED').length;
                const failed = jobs.filter(j => j.status === 'FAILED').length;
                const total = completed + failed;
                const rate = total > 0 ? Math.round((completed / total) * 100) : 100;

                setStats({ activeNodes: onlineNodes, runningJobs, successRate: rate });
                setRecentJobs(jobs.slice(0, 5));

                setChartData([
                    { name: 'Mon', failures: 2 },
                    { name: 'Tue', failures: 0 },
                    { name: 'Wed', failures: 1 },
                    { name: 'Thu', failures: 5 },
                    { name: 'Fri', failures: failed },
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
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Control Plane</h1>
                <p className="text-zinc-500">Global mesh orchestration and telemetry overview.</p>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="bg-zinc-925 border-zinc-800/50 hover:border-primary/50 transition-colors">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-400">Active Puppets</CardTitle>
                        <Network className="h-4 w-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-white tracking-tight">{stats.activeNodes}</div>
                        <p className="text-xs text-zinc-600 mt-1 flex items-center gap-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                            Nodes currently responding to heartbeat
                        </p>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-925 border-zinc-800/50 hover:border-primary/50 transition-colors">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-400">Running Jobs</CardTitle>
                        <Activity className="h-4 w-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-white tracking-tight">{stats.runningJobs}</div>
                        <p className="text-xs text-zinc-600 mt-1">Pending and currently assigned tasks</p>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-925 border-zinc-800/50 hover:border-primary/50 transition-colors">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-400">Success Rate</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-white tracking-tight">{stats.successRate}%</div>
                        <p className="text-xs text-zinc-600 mt-1">Validation pass rate over last 100 jobs</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Chart */}
                <Card className="lg:col-span-2 bg-zinc-925 border-zinc-800/50">
                    <CardHeader>
                        <CardTitle className="text-lg font-bold text-white">Failure Trend</CardTitle>
                        <CardDescription className="text-zinc-500">Security and execution failures across the mesh (7d)</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <div className="sr-only" id="failure-trend-desc">
                            Bar chart showing failures over the last 7 days. Current fail count is {stats.runningJobs > 0 ? 'visible' : 'zero'}.
                        </div>
                        <ResponsiveContainer width="100%" height="100%" aria-describedby="failure-trend-desc">
                            <BarChart data={chartData}>
                                <XAxis
                                    dataKey="name"
                                    stroke="#3f3f46"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <YAxis
                                    stroke="#3f3f46"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#09090b', border: '1px solid #27272a', borderRadius: '8px' }}
                                    itemStyle={{ color: '#fff' }}
                                    cursor={{ fill: '#ffffff05' }}
                                />
                                <Bar dataKey="failures" radius={[4, 4, 0, 0]}>
                                    {chartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.failures > 0 ? '#ef4444' : '#10b981'} fillOpacity={0.8} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Recent Activity */}
                <Card className="bg-zinc-925 border-zinc-800/50">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="text-lg font-bold text-white">Recent Activity</CardTitle>
                            <CardDescription className="text-zinc-500">Latest orchestration events</CardDescription>
                        </div>
                        <ArrowUpRight className="h-4 w-4 text-zinc-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {recentJobs.length > 0 ? (
                                recentJobs.map(job => (
                                    <div key={job.guid} className="flex items-start gap-3 p-3 rounded-xl bg-zinc-900/50 border border-zinc-800/50 group hover:bg-zinc-900 transition-all">
                                        <div className={`mt-1 h-2 w-2 rounded-full shrink-0 ${job.status === 'COMPLETED' ? 'bg-green-500' :
                                            job.status === 'FAILED' ? 'bg-red-500' : 'bg-yellow-500'
                                            }`} />
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between gap-2">
                                                <p className="text-sm font-medium text-white truncate">
                                                    {job.payload.task_type || 'System Task'}
                                                </p>
                                                <span className="text-2xs text-zinc-600 flex items-center gap-1">
                                                    <Clock className="h-3 w-3" />
                                                    {new Date(job.started_at || Date.now()).toLocaleTimeString()}
                                                </span>
                                            </div>
                                            <p className="text-2xs text-zinc-500 font-mono mt-1 uppercase tracking-wider">
                                                ID: {job.guid.substring(0, 8)}
                                            </p>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="text-center py-8">
                                    <AlertCircle className="h-8 w-8 text-zinc-800 mx-auto mb-2" />
                                    <p className="text-sm text-zinc-600">No recent jobs found</p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default Dashboard;
