import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../auth';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        try {
            await login(username, password);
            navigate('/');
        } catch (err) {
            setError('Invalid Credentials');
        }
    };

    return (
        <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center', backgroundColor: '#121212' }}>
            <form onSubmit={handleLogin} style={{ backgroundColor: '#1e1e1e', padding: '40px', borderRadius: '8px', width: '300px' }}>
                <h2 style={{ color: '#FFF', textAlign: 'center', marginBottom: '20px' }}>System Login</h2>
                {error && <div style={{ color: '#ff4444', marginBottom: '10px', textAlign: 'center' }}>{error}</div>}
                <div style={{ marginBottom: '15px' }}>
                    <label style={{ color: '#aaa', display: 'block', marginBottom: '5px' }}>Username</label>
                    <input
                        type="text"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        style={{ width: '100%', padding: '10px', backgroundColor: '#333', border: 'none', color: '#fff', borderRadius: '4px' }}
                    />
                </div>
                <div style={{ marginBottom: '20px' }}>
                    <label style={{ color: '#aaa', display: 'block', marginBottom: '5px' }}>Password</label>
                    <input
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        style={{ width: '100%', padding: '10px', backgroundColor: '#333', border: 'none', color: '#fff', borderRadius: '4px' }}
                    />
                </div>
                <button type="submit" className="btn-primary" style={{ width: '100%' }}>Enter Control Plane</button>
            </form>
        </div>
    );
};

export default Login;
