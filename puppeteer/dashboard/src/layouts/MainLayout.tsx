import { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import {
    LayoutDashboard,
    Network,
    Server,
    ShieldCheck,
    Settings,
    Menu,
    Cpu
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';

const MainLayout = () => {
    const [isMobileOpen, setIsMobileOpen] = useState(false);

    const NavItem = ({ to, icon: Icon, label }: { to: string, icon: React.ComponentType<{ className?: string }>, label: string }) => (
        <NavLink
            to={to}
            className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-zinc-800 hover:text-white ${isActive ? "bg-zinc-800 text-white shadow-sm" : "text-zinc-400"
                }`
            }
            onClick={() => setIsMobileOpen(false)}
        >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{label}</span>
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
                    <div className="pt-4 pb-1 px-3 text-2xs font-bold text-zinc-500 uppercase tracking-widest">
                        Monitoring
                    </div>
                    <NavItem to="/nodes" icon={Server} label="Puppets" />
                    <NavItem to="/jobs" icon={Cpu} label="Orchestration" />

                    <div className="pt-4 pb-1 px-3 text-2xs font-bold text-zinc-500 uppercase tracking-widest">
                        Security
                    </div>
                    <NavItem to="/signatures" icon={ShieldCheck} label="Trust Assets" />

                    <div className="pt-4 pb-1 px-3 text-2xs font-bold text-zinc-500 uppercase tracking-widest">
                        System
                    </div>
                    <NavItem to="/admin" icon={Settings} label="Settings" />
                </nav>
            </div>
            <div className="p-6 border-t border-zinc-900">
                <div className="flex items-center gap-2 text-2xs font-medium text-zinc-500">
                    <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
                    v1.2.0 • Online
                </div>
            </div>
        </div>
    );

    return (
        <div className="flex min-h-screen w-full bg-zinc-975 text-white">
            {/* Desktop Sidebar */}
            <aside className="hidden border-r border-zinc-900 w-64 shrink-0 md:block bg-zinc-975">
                <SidebarContent />
            </aside>

            {/* Mobile Sidebar & Main Content */}
            <div className="flex flex-col flex-1 min-w-0">
                <header className="flex h-16 items-center gap-4 border-b border-zinc-900 bg-zinc-975 px-4 lg:px-6 sticky top-0 z-10">
                    <Sheet open={isMobileOpen} onOpenChange={setIsMobileOpen}>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon" className="shrink-0 md:hidden hover:bg-zinc-800">
                                <Menu className="h-5 w-5" />
                                <span className="sr-only">Toggle navigation</span>
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="left" className="flex flex-col p-4 bg-zinc-975 border-r-zinc-900 w-72">
                            <SidebarContent />
                        </SheetContent>
                    </Sheet>

                    <div className="flex-1 flex items-center justify-between">
                        <h1 className="text-sm font-semibold text-zinc-400 md:hidden">Puppeteer</h1>
                        <div>{/* Spacer or search */}</div>
                        <Button variant="ghost" size="icon" className="rounded-full hover:bg-zinc-800">
                            <div className="h-8 w-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                                <span className="text-xs font-bold text-primary">A</span>
                            </div>
                        </Button>
                    </div>
                </header>
                <main className="flex-1 p-4 lg:p-8 overflow-auto max-w-7xl mx-auto w-full">
                    <Outlet />
                </main>
            </div>
        </div>
    );
};

export default MainLayout;
