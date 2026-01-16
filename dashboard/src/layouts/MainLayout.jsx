import { Outlet, Link, useLocation } from 'react-router-dom';
import { logout, getUser } from '../auth';

const MainLayout = () => {
    const user = getUser();
    const location = useLocation();

    return (
        <div style={{ display: 'flex', height: '100vh', backgroundColor: '#121212', color: '#fff' }}>
            {/* Sidebar */}
            <aside style={{ width: '250px', backgroundColor: '#1e1e1e', padding: '20px', display: 'flex', flexDirection: 'column' }}>
                <h2 style={{ color: '#e91e63', marginBottom: '30px' }}>Puppet Master</h2>

                <nav style={{ flex: 1 }}>
                    <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>📊 Dashboard</Link>
                    <Link to="/nodes" className={`nav-link ${location.pathname === '/nodes' ? 'active' : ''}`}>🖥 Nodes</Link>
                    <Link to="/jobs" className={`nav-link ${location.pathname === '/jobs' ? 'active' : ''}`}>⚡ Jobs</Link>
                    {user?.role === 'admin' && (
                        <Link to="/admin" className={`nav-link ${location.pathname === '/admin' ? 'active' : ''}`}>⚙ Admin</Link>
                    )}
                </nav>

                <div style={{ borderTop: '1px solid #333', paddingTop: '20px' }}>
                    <div style={{ marginBottom: '10px' }}>👤 {user?.sub} <small>({user?.role})</small></div>
                    <button className="btn-sm" onClick={logout} style={{ width: '100%', backgroundColor: '#333' }}>Sign Out</button>
                </div>
            </aside>

            {/* Content */}
            <main style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
                <Outlet />
            </main>
        </div>
    );
};

export default MainLayout;
