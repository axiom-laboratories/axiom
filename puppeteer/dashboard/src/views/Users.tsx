import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { UserPlus, Trash2, ChevronDown, ChevronRight, Plus, X, Shield, KeyRound, RotateCcw, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { authenticatedFetch } from '../auth';
import { useFeatures } from '../hooks/useFeatures';
import { UpgradePlaceholder } from '../components/UpgradePlaceholder';

const ALL_PERMISSIONS = [
    'jobs:read', 'jobs:write',
    'nodes:read', 'nodes:write',
    'definitions:read', 'definitions:write',
    'foundry:read', 'foundry:write',
    'signatures:read', 'signatures:write',
    'tokens:write', 'users:write',
];

const ROLES = ['operator', 'viewer'];

const roleBadge = (role: string) => {
    if (role === 'admin') return 'bg-red-500/10 text-red-400 border-red-500/20';
    if (role === 'operator') return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    return 'bg-muted/50 text-muted-foreground border-muted/30';
};

interface UserRecord {
    id: string;
    username: string;
    role: string;
    created_at: string;
    must_change_password?: boolean;
}

const fetchUsers = async (): Promise<UserRecord[]> => {
    const res = await authenticatedFetch('/admin/users');
    if (!res.ok) throw new Error('Failed to fetch users');
    return res.json();
};

const fetchRolePermissions = async (role: string): Promise<string[]> => {
    const res = await authenticatedFetch(`/admin/roles/${role}/permissions`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((p: { permission: string }) => p.permission);
};

// ── Role Permissions Panel ────────────────────────────────────────────────────

const RolePanel = ({ role }: { role: string }) => {
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);

    const { data: perms = [] } = useQuery({
        queryKey: ['role-perms', role],
        queryFn: () => fetchRolePermissions(role),
        enabled: open,
    });

    const grant = useMutation({
        mutationFn: (permission: string) =>
            authenticatedFetch(`/admin/roles/${role}/permissions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ permission }),
            }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['role-perms', role] }),
    });

    const revoke = useMutation({
        mutationFn: (permission: string) =>
            authenticatedFetch(`/admin/roles/${role}/permissions/${permission}`, { method: 'DELETE' }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['role-perms', role] }),
    });

    const missing = ALL_PERMISSIONS.filter(p => !perms.includes(p));

    return (
        <div className="border border-muted rounded-lg overflow-hidden">
            <button
                className="w-full flex items-center justify-between px-4 py-3 bg-secondary/50 hover:bg-secondary transition-colors text-left"
                onClick={() => setOpen(o => !o)}
            >
                <div className="flex items-center gap-3">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-foreground capitalize">{role}</span>
                    <span className="text-xs text-muted-foreground">{open ? `${perms.length} permissions` : ''}</span>
                </div>
                {open ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
            </button>

            {open && (
                <div className="px-4 py-4 space-y-4 bg-background/30">
                    <div className="flex flex-wrap gap-2">
                        {perms.map(p => (
                            <span key={p} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-primary/10 border border-primary/20 text-xs font-mono text-primary/80">
                                {p}
                                <button
                                    onClick={() => revoke.mutate(p)}
                                    className="ml-0.5 text-muted-foreground hover:text-red-400 transition-colors"
                                    title="Revoke"
                                >
                                    <X className="h-3 w-3" />
                                </button>
                            </span>
                        ))}
                        {perms.length === 0 && (
                            <span className="text-xs text-muted-foreground/60 italic">No permissions assigned</span>
                        )}
                    </div>

                    {missing.length > 0 && (
                        <>
                            <Separator className="bg-muted" />
                            <div>
                                <p className="text-xs text-muted-foreground mb-2">Grant permission:</p>
                                <div className="flex flex-wrap gap-2">
                                    {missing.map(p => (
                                        <button
                                            key={p}
                                            onClick={() => grant.mutate(p)}
                                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-muted text-xs font-mono text-muted-foreground hover:text-foreground hover:border-muted-foreground transition-colors"
                                        >
                                            <Plus className="h-3 w-3" />
                                            {p}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

// ── User Row ─────────────────────────────────────────────────────────────────

const UserRow = ({ user }: { user: UserRecord }) => {
    const qc = useQueryClient();
    const [editingRole, setEditingRole] = useState(false);
    const [showReset, setShowReset] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [resetPw, setResetPw] = useState('');
    const [resetConfirm, setResetConfirm] = useState('');
    const [resetMsg, setResetMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

    const updateRole = useMutation({
        mutationFn: (role: string) =>
            authenticatedFetch(`/admin/users/${user.username}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role }),
            }),
        onSuccess: () => {
            toast.success(`Role for ${user.username} updated to ${updateRole.variables}`);
            qc.invalidateQueries({ queryKey: ['users'] });
            setEditingRole(false);
        },
        onError: (e: Error) => toast.error(`Failed to update role: ${e.message}`),
    });

    const deleteUser = useMutation({
        mutationFn: () => authenticatedFetch(`/admin/users/${user.username}`, { method: 'DELETE' }),
        onSuccess: () => {
            toast.success(`User ${user.username} deleted`);
            qc.invalidateQueries({ queryKey: ['users'] });
            setShowDeleteConfirm(false);
        },
        onError: (e: Error) => toast.error(`Failed to delete user: ${e.message}`),
    });

    const resetPassword = useMutation({
        mutationFn: () =>
            authenticatedFetch(`/admin/users/${user.username}/reset-password`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: resetPw }),
            }),
        onSuccess: () => {
            toast.success(`Password reset for ${user.username}`);
            setResetPw(''); setResetConfirm(''); setShowReset(false);
            setResetMsg({ type: 'ok', text: 'Password reset.' });
        },
        onError: () => {
            toast.error(`Failed to reset password for ${user.username}`);
            setResetMsg({ type: 'err', text: 'Reset failed.' });
        },
    });

    const forceChange = useMutation({
        mutationFn: (enabled: boolean) =>
            authenticatedFetch(`/admin/users/${user.username}/force-password-change`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled }),
            }),
        onSuccess: () => {
            toast.success(`Force password change ${forceChange.variables ? 'enabled' : 'disabled'} for ${user.username}`);
            qc.invalidateQueries({ queryKey: ['users'] });
        },
        onError: (e: Error) => toast.error(`Failed to update force change status: ${e.message}`),
    });

    const canReset = resetPw.length >= 8 && resetPw === resetConfirm;

    return (
        <>
            <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete User?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete user "{user.username}"? This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => deleteUser.mutate()} disabled={deleteUser.isPending}>
                            {deleteUser.isPending ? 'Deleting...' : 'Delete User'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
            <tr className="border-b border-muted/50 hover:bg-muted/20 transition-colors">
                <td className="px-6 py-3 font-mono text-foreground">
                    <span className="flex items-center gap-2">
                        {user.username}
                        {user.must_change_password && (
                            <span title="Must change password on next login">
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                            </span>
                        )}
                    </span>
                </td>
                <td className="px-6 py-3">
                    {editingRole ? (
                        <div className="flex items-center gap-2">
                            <select
                                defaultValue={user.role}
                                onChange={e => updateRole.mutate(e.target.value)}
                                className="h-7 rounded bg-muted border border-muted text-foreground text-xs px-2"
                            >
                                <option value="viewer">viewer</option>
                                <option value="operator">operator</option>
                                <option value="admin">admin</option>
                            </select>
                            <button onClick={() => setEditingRole(false)} className="text-muted-foreground hover:text-foreground">
                                <X className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    ) : (
                        <Badge
                            variant="outline"
                            className={`text-xs font-mono cursor-pointer ${roleBadge(user.role)}`}
                            onClick={() => user.role !== 'admin' && setEditingRole(true)}
                            title={user.role !== 'admin' ? 'Click to change role' : ''}
                        >
                            {user.role}
                        </Badge>
                    )}
                </td>
                <td className="px-6 py-3 text-muted-foreground text-xs font-mono">
                    {new Date(user.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-3">
                    <div className="flex items-center justify-end gap-1">
                        {user.role !== 'admin' && (
                            <>
                                <Button
                                    size="icon" variant="ghost"
                                    className={`h-7 w-7 ${user.must_change_password ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-500/10' : 'text-muted-foreground/60 hover:text-amber-400 hover:bg-amber-500/10'}`}
                                    onClick={() => forceChange.mutate(!user.must_change_password)}
                                    title={user.must_change_password ? 'Clear forced password change' : 'Force password change on next login'}
                                >
                                    <RotateCcw className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                    size="icon" variant="ghost"
                                    className={`h-7 w-7 ${showReset ? 'text-primary bg-primary/10' : 'text-muted-foreground/60 hover:text-primary hover:bg-primary/10'}`}
                                    onClick={() => { setShowReset(s => !s); setResetMsg(null); }}
                                    title="Reset password"
                                >
                                    <KeyRound className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                    size="icon" variant="ghost"
                                    className="h-7 w-7 text-muted-foreground/60 hover:text-red-400 hover:bg-red-500/10"
                                    onClick={() => setShowDeleteConfirm(true)}
                                    title="Delete user"
                                >
                                    <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                            </>
                        )}
                    </div>
                </td>
            </tr>
            {showReset && (
                <tr className="border-b border-muted/50 bg-secondary/30">
                    <td colSpan={4} className="px-6 py-3">
                        <div className="flex items-center gap-3 flex-wrap">
                            <span className="text-xs text-muted-foreground font-mono">Reset password for <span className="text-foreground">{user.username}</span>:</span>
                            <Input
                                type="password"
                                placeholder="New password"
                                value={resetPw}
                                onChange={e => { setResetPw(e.target.value); setResetMsg(null); }}
                                className="h-7 w-40 bg-muted border-muted text-foreground text-xs px-2"
                            />
                            <Input
                                type="password"
                                placeholder="Confirm"
                                value={resetConfirm}
                                onChange={e => { setResetConfirm(e.target.value); setResetMsg(null); }}
                                className={`h-7 w-32 bg-muted border-muted text-foreground text-xs px-2 ${resetConfirm && resetConfirm !== resetPw ? 'border-red-500/50' : ''}`}
                            />
                            <Button
                                size="sm" className="h-7 bg-primary hover:bg-primary/90 text-foreground text-xs px-3"
                                onClick={() => resetPassword.mutate()}
                                disabled={!canReset || resetPassword.isPending}
                            >
                                Set Password
                            </Button>
                            <Button size="sm" variant="ghost" className="h-7 text-muted-foreground text-xs px-2"
                                onClick={() => { setShowReset(false); setResetPw(''); setResetConfirm(''); }}>
                                Cancel
                            </Button>
                            {resetMsg && <span className={`text-xs ${resetMsg.type === 'ok' ? 'text-emerald-400' : 'text-red-400'}`}>{resetMsg.text}</span>}
                        </div>
                    </td>
                </tr>
            )}
        </>
    );
};

// ── Main View ─────────────────────────────────────────────────────────────────

const Users = () => {
    const qc = useQueryClient();
    const [showCreate, setShowCreate] = useState(false);
    const [newUsername, setNewUsername] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [newRole, setNewRole] = useState('viewer');

    const { data: users = [], isLoading } = useQuery({
        queryKey: ['users'],
        queryFn: fetchUsers,
    });

    const createUser = useMutation({
        mutationFn: () =>
            authenticatedFetch('/admin/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: newUsername, password: newPassword, role: newRole }),
            }),
        onSuccess: () => {
            toast.success(`User ${newUsername} created`);
            qc.invalidateQueries({ queryKey: ['users'] });
            setNewUsername('');
            setNewPassword('');
            setNewRole('viewer');
            setShowCreate(false);
        },
        onError: (e: Error) => toast.error(`Failed to create user: ${e.message}`),
    });

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-foreground">Users & Roles</h1>
                <p className="text-sm text-muted-foreground mt-1">Manage operator accounts and configure role permissions.</p>
            </div>

            {/* ── Users Table ── */}
            <Card className="bg-card border-muted/50">
                <CardHeader className="flex flex-row items-center justify-between pb-4">
                    <div>
                        <CardTitle className="text-lg font-bold text-foreground">Users</CardTitle>
                        <CardDescription className="text-muted-foreground">
                            {users.length} account{users.length !== 1 ? 's' : ''}
                        </CardDescription>
                    </div>
                    <Button
                        size="sm"
                        className="bg-primary hover:bg-primary/90 text-foreground font-bold"
                        onClick={() => setShowCreate(s => !s)}
                    >
                        <UserPlus className="mr-2 h-4 w-4" />
                        New User
                    </Button>
                </CardHeader>

                {showCreate && (
                    <div className="mx-6 mb-4 p-4 rounded-lg border border-muted bg-secondary/50 space-y-3">
                        <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Create User</p>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <Input
                                placeholder="Username"
                                value={newUsername}
                                onChange={e => setNewUsername(e.target.value)}
                                className="bg-muted border-muted text-foreground placeholder:text-muted-foreground/60"
                            />
                            <Input
                                type="password"
                                placeholder="Password"
                                value={newPassword}
                                onChange={e => setNewPassword(e.target.value)}
                                className="bg-muted border-muted text-foreground placeholder:text-muted-foreground/60"
                            />
                            <select
                                value={newRole}
                                onChange={e => setNewRole(e.target.value)}
                                className="h-9 rounded-md bg-muted border border-muted text-foreground text-sm px-3"
                            >
                                <option value="viewer">viewer</option>
                                <option value="operator">operator</option>
                                <option value="admin">admin</option>
                            </select>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                size="sm"
                                onClick={() => createUser.mutate()}
                                disabled={!newUsername || !newPassword || createUser.isPending}
                                className="bg-primary hover:bg-primary/90 text-foreground"
                            >
                                Create
                            </Button>
                            <Button size="sm" variant="ghost" className="text-muted-foreground" onClick={() => setShowCreate(false)}>
                                Cancel
                            </Button>
                        </div>
                    </div>
                )}

                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-muted text-muted-foreground text-xs uppercase tracking-wider">
                                    <th className="px-6 py-3 text-left font-medium">Username</th>
                                    <th className="px-6 py-3 text-left font-medium">Role</th>
                                    <th className="px-6 py-3 text-left font-medium">Created</th>
                                    <th className="px-6 py-3 text-right font-medium">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {isLoading ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-8 text-center text-muted-foreground/60">Loading...</td>
                                    </tr>
                                ) : users.map(user => (
                                    <UserRow key={user.username} user={user} />
                                ))}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>

            {/* ── Role Permissions ── */}
            <Card className="bg-card border-muted/50">
                <CardHeader>
                    <CardTitle className="text-lg font-bold text-foreground">Role Permissions</CardTitle>
                    <CardDescription className="text-muted-foreground">
                        Configure which actions each role can perform. Admin always has full access.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                    {ROLES.map(role => <RolePanel key={role} role={role} />)}
                </CardContent>
            </Card>
        </div>
    );
};

const UsersWithFeatureCheck = () => {
    const features = useFeatures();
    if (!features.rbac) {
        return <UpgradePlaceholder feature="Users & RBAC" description="Multi-user management with role-based access control (admin, operator, viewer) and per-role permission assignment." />;
    }
    return <Users />;
};

export default UsersWithFeatureCheck;
