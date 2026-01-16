import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../auth';

const Nodes = () => {
    const [nodes, setNodes] = useState([]);

    const fetchNodes = async () => {
        try {
            const res = await authenticatedFetch('https://localhost:8001/nodes');
            if (res.ok) {
                setNodes(await res.json());
            }
        } catch (e) {
            console.error("Failed", e);
        }
    };

    useEffect(() => {
        fetchNodes();
        const interval = setInterval(fetchNodes, 5000);
        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (node) => {
        if (node.status === 'OFFLINE') return '#ff4444'; // Red
        if (!node.stats) return '#00C851'; // Green (No stats yet)

        const cpu = node.stats.cpu || 0;
        const ram = node.stats.ram || 0;

        if (cpu > 95 || ram > 95) return '#ffbb33'; // Orange
        if (cpu > 80 || ram > 80) return '#ffeb3b'; // Yellow
        return '#00C851'; // Green
    };

    return (
        <div>
            <h1>Environment Nodes</h1>
            <div className="job-grid">
                {nodes.map(node => (
                    <div key={node.node_id} className="job-card" style={{ borderColor: getStatusColor(node) }}>
                        <div className="card-header">
                            <span style={{ fontWeight: 'bold' }}>{node.hostname}</span>
                            <span className="badge" style={{ backgroundColor: getStatusColor(node), color: '#000' }}>
                                {node.status}
                            </span>
                        </div>
                        <div className="card-body">
                            <div>IP: {node.ip}</div>
                            <div>Last Seen: {new Date(node.last_seen).toLocaleTimeString()}</div>
                            {node.stats && (
                                <div style={{ marginTop: '10px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span>CPU</span>
                                        <span>{node.stats.cpu}%</span>
                                    </div>
                                    <div className="progress-bar">
                                        <div style={{ width: `${node.stats.cpu}%`, backgroundColor: node.stats.cpu > 80 ? 'orange' : '#2196f3' }}></div>
                                    </div>

                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '5px' }}>
                                        <span>RAM</span>
                                        <span>{node.stats.ram}%</span>
                                    </div>
                                    <div className="progress-bar">
                                        <div style={{ width: `${node.stats.ram}%`, backgroundColor: node.stats.ram > 80 ? 'orange' : '#9c27b0' }}></div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Nodes;
