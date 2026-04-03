import { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard,
    Network,
    Server,
    ShieldCheck,
    Settings,
    Menu,
    Cpu,
    Boxes,
    ScrollText,
    Users,
    CalendarClock,
    Bot,
    Webhook,
    History as HistoryIcon,
    BookOpen,
    Lock,
    ListOrdered,
    AlertTriangle,
    X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { getUser, logout, setToken } from '../auth';
import { useFeatures } from '../hooks/useFeatures';
import { useLicence } from '../hooks/useLicence';
import { ThemeToggle } from '@/components/ThemeToggle';
import { NotificationBell } from '@/components/NotificationBell';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { authenticatedFetch } from '../auth';

const MainLayout = () => {
    const [isMobileOpen, setIsMobileOpen] = useState(false);
    const features = useFeatures();
    const licence = useLicence();

    const NavItem = ({ to, icon: Icon, label }: { to: string, icon: React.ComponentType<{ className?: string }>, label: string }) => (
        <NavLink
            to={to}
            className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-muted hover:text-foreground ${isActive ? "bg-muted text-foreground shadow-sm" : "text-muted-foreground"
                }`
            }
            onClick={() => setIsMobileOpen(false)}
            aria-label={label}
        >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{label}</span>
        </NavLink>
    );

    const NavItemEE = ({ to, icon: Icon, label, enabled }: { to: string, icon: React.ComponentType<{ className?: string }>, label: string, enabled: boolean }) => (
        <NavLink
            to={to}
            className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-muted hover:text-foreground ${isActive ? "bg-muted text-foreground shadow-sm" : "text-muted-foreground"}`
            }
            onClick={() => setIsMobileOpen(false)}
            aria-label={label}
        >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="flex-1">{label}</span>
            {!enabled && <Lock className="h-3 w-3 text-muted shrink-0" />}
        </NavLink>
    );

    const SidebarContent = () => (
        <div className="flex h-full flex-col gap-4">
            <div className="flex h-16 items-center px-6">
                <a href="/" className="flex items-center gap-3 font-bold text-lg tracking-tight">
                    <div className="bg-primary p-1.5 rounded-lg text-white">
                        <Network className="h-5 w-5" />
                    </div>
                    <span>Puppeteer</span>
                </a>
            </div>
            <div className="flex-1 overflow-auto px-4 pb-4">
                <nav className="space-y-1.5">
                    <NavItem to="/" icon={LayoutDashboard} label="Dashboard" />
                    <div className="pt-4 pb-1 px-3 text-2xs font-bold text-muted-foreground uppercase tracking-widest">
                        Monitoring
                    </div>
                    <NavItem to="/nodes" icon={Server} label="Nodes" />
                    <NavItem to="/jobs" icon={Cpu} label="Jobs" />
                    <NavItem to="/queue" icon={ListOrdered} label="Queue" />
                    <NavItem to="/history" icon={HistoryIcon} label="History" />
                    <NavItem to="/scheduled-jobs" icon={CalendarClock} label="Scheduled Jobs" />

                    <div className="pt-4 pb-1 px-3 text-2xs font-bold text-muted-foreground uppercase tracking-widest">
                        Security
                    </div>
                    <NavItem to="/signatures" icon={ShieldCheck} label="Signing Keys" />

                    <div className="pt-4 pb-1 px-3 text-2xs font-bold text-muted-foreground uppercase tracking-widest">
                        Foundry
                    </div>
                    <NavItemEE to="/templates" icon={Boxes} label="Templates" enabled={features.foundry} />

                    <div className="pt-4 pb-1 px-3 text-2xs font-bold text-muted-foreground uppercase tracking-widest">
                        System
                    </div>
                    <NavItem to="/admin" icon={Settings} label="Settings" />
                    <NavItemEE to="/users" icon={Users} label="Users & Roles" enabled={features.rbac} />
                    <NavItemEE to="/service-principals" icon={Bot} label="Service Principals" enabled={features.service_principals} />
                    <NavItemEE to="/webhooks" icon={Webhook} label="Webhooks" enabled={features.webhooks} />
                    <NavItemEE to="/audit" icon={ScrollText} label="Audit Log" enabled={features.audit} />

                    <div className="pt-4 pb-1 px-3 text-2xs font-bold text-muted-foreground uppercase tracking-widest">
                        Documentation
                    </div>
                    <a
                        href="/docs/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-muted hover:text-foreground text-muted-foreground"
                        aria-label="Documentation"
                    >
                        <BookOpen className="h-4 w-4 shrink-0" />
                        <span>Docs</span>
                    </a>
                </nav>
            </div>
            <div className="p-6 border-t border-muted space-y-4">
                <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
                    <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
                        v1.2.0 • Online
                    </div>
                    <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${
                        licence.status === 'expired' ? 'bg-red-500/20 text-red-400'
                        : licence.status === 'grace'  ? 'bg-amber-500/20 text-amber-400'
                        : licence.isEnterprise        ? 'bg-indigo-500/20 text-indigo-400'
                        :                               'bg-muted text-muted-foreground'
                    }`}>
                        {licence.isEnterprise ? 'EE' : 'CE'}
                    </span>
                </div>
                <div className="flex justify-center">
                    <ThemeToggle />
                </div>
            </div>
        </div>
    );

    const navigate = useNavigate();
    const user = getUser();
    const isAdmin = user?.role === 'admin';
    const initial = user?.username?.[0]?.toUpperCase() ?? '?';

    const [forceChangeOpen, setForceChangeOpen] = useState<boolean>(
        () => localStorage.getItem('mop_must_change_password') === '1'
    );
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [pwError, setPwError] = useState('');
    const [pwLoading, setPwLoading] = useState(false);

    const handleForceChange = async (e: React.FormEvent) => {
        e.preventDefault();
        setPwError('');
        if (newPassword.length < 8) {
            setPwError('Password must be at least 8 characters.');
            return;
        }
        if (newPassword !== confirmPassword) {
            setPwError('Passwords do not match.');
            return;
        }
        setPwLoading(true);
        try {
            const res = await authenticatedFetch('/auth/me', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: newPassword }),
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                setPwError(body.detail || 'Failed to change password.');
                return;
            }
            const body = await res.json();
            if (body.access_token) setToken(body.access_token);
            localStorage.removeItem('mop_must_change_password');
            setForceChangeOpen(false);
        } catch {
            setPwError('Network error — please try again.');
        } finally {
            setPwLoading(false);
        }
    };

    const GRACE_DISMISSED_KEY = 'axiom_licence_grace_dismissed';
    const [graceDismissed, setGraceDismissed] = useState<boolean>(
        () => sessionStorage.getItem(GRACE_DISMISSED_KEY) === '1'
    );
    const handleDismissGrace = () => {
        sessionStorage.setItem(GRACE_DISMISSED_KEY, '1');
        setGraceDismissed(true);
    };

    const handleLogout = () => {
        logout();
    };

    return (
        <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
            {/* Desktop Sidebar */}
            <aside className="hidden border-r border-muted w-64 shrink-0 md:flex md:flex-col h-screen sticky top-0 overflow-y-auto bg-secondary" role="navigation" aria-label="Main Sidebar">
                <SidebarContent />
            </aside>

            {/* Mobile Sidebar & Main Content */}
            <div className="flex flex-col flex-1 min-w-0 h-screen overflow-hidden">
                <header className="flex h-16 items-center gap-4 border-b border-muted bg-secondary px-4 lg:px-6 sticky top-0 z-10">
                    <Sheet open={isMobileOpen} onOpenChange={setIsMobileOpen}>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon" className="shrink-0 md:hidden hover:bg-muted">
                                <Menu className="h-5 w-5" />
                                <span className="sr-only">Toggle navigation</span>
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="left" className="flex flex-col p-4 bg-secondary border-r-muted w-72" aria-label="Mobile Menu">
                            <SidebarContent />
                        </SheetContent>
                    </Sheet>

                    <div className="flex-1 flex items-center justify-between">
                        <h1 className="text-sm font-semibold text-muted-foreground md:hidden">Puppeteer</h1>
                        <div>{/* Spacer or search */}</div>
                        <div className="flex items-center gap-2">
                            <NotificationBell />
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="icon" className="rounded-full hover:bg-muted" aria-label="User menu">
                                        <div className="h-8 w-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                                            <span className="text-xs font-bold text-primary">{initial}</span>
                                        </div>
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-48">
                                    <DropdownMenuLabel className="text-muted-foreground font-normal">
                                        Signed in as <span className="text-foreground font-medium">{user?.username}</span>
                                    </DropdownMenuLabel>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={() => navigate('/account')}>
                                        My Account
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem
                                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                                        onClick={handleLogout}
                                    >
                                        Sign Out
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    </div>
                </header>
                {isAdmin && licence.status === 'grace' && !graceDismissed && (
                    <div className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-amber-900/40 text-amber-300 border-b border-amber-800">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        <span>{`Your EE licence expires in ${licence.days_until_expiry} day${licence.days_until_expiry === 1 ? '' : 's'}. Please renew.`}</span>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="ml-auto h-6 w-6 text-amber-300 hover:text-amber-100 hover:bg-amber-800/50"
                            onClick={handleDismissGrace}
                            aria-label="Dismiss licence warning"
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                )}
                {isAdmin && licence.status === 'expired' && (
                    <div className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-red-900/40 text-red-300 border-b border-red-800">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        Your EE licence has expired. The system is running in Community Edition mode.
                    </div>
                )}
                <main className="flex-1 p-4 lg:p-8 overflow-y-auto max-w-7xl mx-auto w-full">
                    <Outlet />
                </main>
            </div>

            <Dialog open={forceChangeOpen} onOpenChange={() => {}}>
                <DialogContent className="sm:max-w-md bg-card border-muted" onInteractOutside={(e) => e.preventDefault()}>
                    <DialogHeader>
                        <DialogTitle className="text-foreground">Change Your Password</DialogTitle>
                        <DialogDescription className="text-muted-foreground">
                            You are using the default password. Please set a new password before continuing.
                        </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleForceChange} className="space-y-4 mt-2">
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">New Password</label>
                            <input
                                type="password"
                                value={newPassword}
                                onChange={e => setNewPassword(e.target.value)}
                                placeholder="Min. 8 characters"
                                className="w-full h-10 px-3 bg-card border border-muted text-foreground rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all placeholder:text-muted-foreground"
                                autoFocus
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Confirm Password</label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={e => setConfirmPassword(e.target.value)}
                                placeholder="Repeat new password"
                                className="w-full h-10 px-3 bg-card border border-muted text-foreground rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all placeholder:text-muted-foreground"
                            />
                        </div>
                        {pwError && <p className="text-sm text-red-400">{pwError}</p>}
                        <Button
                            type="submit"
                            disabled={pwLoading || !newPassword || !confirmPassword}
                            className="w-full bg-primary hover:bg-primary/90 text-white font-bold"
                        >
                            {pwLoading ? 'Saving…' : 'Set Password'}
                        </Button>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default MainLayout;
