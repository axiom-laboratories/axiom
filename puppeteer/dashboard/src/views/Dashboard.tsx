import { useState, useEffect } from 'react';
import { useTheme } from '@/hooks/useTheme';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import {
    Activity,
    Network,
    CheckCircle2,
    Clock,
    AlertCircle,
    ArrowUpRight
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { authenticatedFetch } from '../auth';

const Dashboard = () => {
    const { theme } = useTheme();
    const [stats, setStats] = useState({ activeNodes: 0, runningJobs: 0, successRate: 100 });
    const [recentJobs, setRecentJobs] = useState([]);
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadData = async () => {
        try {
            const [nodesRes, jobsRes, statsRes] = await Promise.all([
                authenticatedFetch('/nodes'),
                authenticatedFetch('/jobs'),
                authenticatedFetch('/api/jobs/stats')
            ]);

            if (nodesRes.ok && jobsRes.ok && statsRes.ok) {
                const nodesData = await nodesRes.json();
                const jobsData = await jobsRes.json();
                const jobStats = await statsRes.json();

                const nodes: any[] = Array.isArray(nodesData) ? nodesData : (nodesData.items ?? []);
                const jobs: any[] = Array.isArray(jobsData) ? jobsData : (jobsData.items ?? []);

                const onlineNodes = nodes.filter(n => n.status === 'ONLINE').length;

                // Use backend aggregated stats for precision
                const runningJobs = jobStats.running || 0;
                const completed = jobStats.completed || 0;
                const failed = jobStats.failed || 0;
                const total = completed + failed;
                const rate = total > 0 ? Math.round((completed / total) * 100) : 100;

                setStats({ activeNodes: onlineNodes, runningJobs, successRate: rate });
                setRecentJobs(jobs.slice(0, 5));

                // Aggregate failure trend for the last 7 days
                const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
                const trendMap: Record<string, number> = {};

                // Initialize last 7 days
                const now = new Date();
                const trendData = [];
                for (let i = 6; i >= 0; i--) {
                    const d = new Date(now);
                    d.setDate(d.getDate() - i);
                    const dayLabel = days[d.getDay()];
                    trendMap[dayLabel] = 0;
                    trendData.push({ name: dayLabel, failures: 0, dateStr: d.toDateString() });
                }

                // Count failures by date
                jobs.forEach((job: any) => {
                    if (job.status === 'FAILED' && job.started_at) {
                        const jobDate = new Date(job.started_at).toDateString();
                        const match = trendData.find(t => t.dateStr === jobDate);
                        if (match) {
                            match.failures++;
                        }
                    }
                });

                setChartData(trendData.map(({ name, failures }) => ({ name, failures })));
            }
        } catch (e) {
            console.error(e);
            toast.error('Failed to load dashboard data. Retrying...');
        } finally {
            setLoading(false);
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
                <h1 className="text-2xl font-bold tracking-tight text-foreground">Dashboard</h1>
                <p className="text-sm text-muted-foreground mt-1">Global mesh orchestration overview.</p>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="bg-card border-muted hover:border-primary/50 transition-colors">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Active Nodes</CardTitle>
                        <Network className="h-4 w-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="h-9 w-16 bg-muted animate-pulse rounded" />
                        ) : (
                            <div className="text-3xl font-bold text-foreground tracking-tight">{stats.activeNodes}</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                            Nodes currently responding to heartbeat
                        </p>
                    </CardContent>
                </Card>

                <Card className="bg-card border-muted hover:border-primary/50 transition-colors">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Running Jobs</CardTitle>
                        <Activity className="h-4 w-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="h-9 w-16 bg-muted animate-pulse rounded" />
                        ) : (
                            <div className="text-3xl font-bold text-foreground tracking-tight">{stats.runningJobs}</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">Pending and currently assigned tasks</p>
                    </CardContent>
                </Card>

                <Card className="bg-card border-muted hover:border-primary/50 transition-colors">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Success Rate</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="h-9 w-16 bg-muted animate-pulse rounded" />
                        ) : (
                            <div className="text-3xl font-bold text-foreground tracking-tight">{stats.successRate}%</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">Validation pass rate over last 100 jobs</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Chart */}
                <Card className="lg:col-span-2 bg-card border-muted">
                    <CardHeader>
                        <CardTitle className="text-lg font-bold text-foreground">Failure Trend</CardTitle>
                        <CardDescription className="text-muted-foreground">Security and execution failures across the mesh (7d)</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <div className="sr-only" id="failure-trend-desc">
                            Bar chart showing failures over the last 7 days. Current fail count is {stats.runningJobs > 0 ? 'visible' : 'zero'}.
                        </div>
                        <ResponsiveContainer width="100%" height="100%" aria-describedby="failure-trend-desc">
                            <BarChart data={chartData}>
                                <XAxis
                                    dataKey="name"
                                    stroke="currentColor"
                                    className="text-muted-foreground"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <YAxis
                                    stroke="currentColor"
                                    className="text-muted-foreground"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'var(--background)', border: '1px solid var(--muted)', borderRadius: '8px' }}
                                    itemStyle={{ color: 'var(--foreground)' }}
                                    cursor={{ fill: 'rgba(0,0,0,0.05)' }}
                                />
                                <Bar dataKey="failures" radius={[4, 4, 0, 0]}>
                                    {chartData.map((entry, index) => {
                                        const failureColor = theme === 'dark' ? (entry.failures > 0 ? '#f87171' : '#6ee7b7') : (entry.failures > 0 ? '#ef4444' : '#10b981');
                                        return (
                                            <Cell key={`cell-${index}`} fill={failureColor} fillOpacity={0.8} />
                                        );
                                    })}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Recent Activity */}
                <Card className="bg-card border-muted">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="text-lg font-bold text-foreground">Recent Activity</CardTitle>
                            <CardDescription className="text-muted-foreground">Latest orchestration events</CardDescription>
                        </div>
                        <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {recentJobs.length > 0 ? (
                                recentJobs.map(job => (
                                    <div key={job.guid} className="flex items-start gap-3 p-3 rounded-xl bg-secondary border border-muted group hover:bg-muted transition-all">
                                        <div className={`mt-1 h-2 w-2 rounded-full shrink-0 ${job.status === 'COMPLETED' ? 'bg-green-500' :
                                            job.status === 'FAILED' ? 'bg-red-500' : 'bg-yellow-500'
                                            }`} />
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between gap-2">
                                                <p className="text-sm font-medium text-foreground truncate">
                                                    {job.payload.task_type || 'System Task'}
                                                </p>
                                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                                    <Clock className="h-3 w-3" />
                                                    {new Date(job.started_at || Date.now()).toLocaleTimeString()}
                                                </span>
                                            </div>
                                            <p className="text-xs text-muted-foreground font-mono mt-1 uppercase tracking-wider">
                                                ID: {job.guid.substring(0, 8)}
                                            </p>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="text-center py-8">
                                    <AlertCircle className="h-8 w-8 text-muted mx-auto mb-2" />
                                    <p className="text-sm text-muted-foreground">No recent jobs found</p>
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
