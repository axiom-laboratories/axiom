import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Network } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { login } from '../auth';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await login(username, password);
            navigate('/');
        } catch (err) {
            setError('Invalid Credentials');
        }
    };

    return (
        <div className="flex h-screen items-center justify-center bg-zinc-975 px-4">
            <div className="w-full max-w-[400px] space-y-8 bg-zinc-925 p-10 rounded-2xl border border-zinc-800/50 shadow-2xl">
                <div className="text-center space-y-2">
                    <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary mb-4">
                        <Network className="h-6 w-6" />
                    </div>
                    <h2 className="text-2xl font-bold tracking-tight text-white">System Login</h2>
                    <p className="text-zinc-500 text-sm">Enter your credentials to access the mesh</p>
                </div>

                {error && (
                    <div className="bg-destructive/10 border border-destructive/20 text-destructive text-xs py-3 px-4 rounded-lg text-center font-medium animate-in fade-in slide-in-from-top-1">
                        {error}
                    </div>
                )}

                <form onSubmit={handleLogin} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            placeholder="admin"
                            className="w-full h-11 px-4 bg-zinc-900 border border-zinc-800 text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all placeholder:text-zinc-700"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder="••••••••"
                            className="w-full h-11 px-4 bg-zinc-900 border border-zinc-800 text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all placeholder:text-zinc-700"
                        />
                    </div>
                    <Button type="submit" className="w-full h-11 bg-primary hover:bg-primary/90 text-white rounded-xl font-bold shadow-lg shadow-primary/20 transition-all active:scale-[0.98]">
                        Enter Control Plane
                    </Button>
                </form>

                <div className="text-center pt-4">
                    <p className="text-zinc-600 text-xs uppercase font-bold tracking-widest">v1.2.0 • Secured by mTLS</p>
                </div>
            </div>
        </div>
    );
};

export default Login;
