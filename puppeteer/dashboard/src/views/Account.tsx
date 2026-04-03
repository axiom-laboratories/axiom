import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  KeyRound,
  Key,
  Copy,
  Eye,
  EyeOff,
  Trash2,
  Plus,
  Download,
  Shield,
  User,
  Loader2,
  Check,
  AlertTriangle
} from 'lucide-react';
import { authenticatedFetch, getUser, setToken } from '../auth';

import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
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
import { Textarea } from '@/components/ui/textarea';

interface SigningKey {
  id: string;
  name: string;
  public_key_pem: string;
  created_at: string;
}

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
}

interface UserProfile {
  username: string;
  role: string;
  email?: string;
}

const Account = () => {
  const queryClient = useQueryClient();
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  // Dialog states
  const [uploadKeyOpen, setUploadKeyOpen] = useState(false);
  const [genKeyOpen, setGenKeyOpen] = useState(false);
  const [genApiKeyOpen, setGenApiKeyOpen] = useState(false);
  const [deleteKeyConfirm, setDeleteKeyConfirm] = useState<string | null>(null);
  const [revokeApiKeyConfirm, setRevokeApiKeyConfirm] = useState<string | null>(null);

  // Success result states
  const [generatedSigningKey, setGeneratedSigningKey] = useState<{ name: string; private_key_pem: string } | null>(null);
  const [generatedApiKey, setGeneratedApiKey] = useState<{ name: string; raw_key: string } | null>(null);

  // Queries
  const { data: profile, isLoading: profileLoading } = useQuery<UserProfile>({
    queryKey: ['me'],
    queryFn: () => authenticatedFetch('/auth/me').then((r) => r.json()),
  });

  const { data: signingKeys, isLoading: keysLoading } = useQuery<SigningKey[]>({
    queryKey: ['my-signing-keys'],
    queryFn: () => authenticatedFetch('/auth/me/signing-keys').then((r) => r.json()),
  });

  const { data: apiKeys, isLoading: apiKeysLoading } = useQuery<ApiKey[]>({
    queryKey: ['my-api-keys'],
    queryFn: () => authenticatedFetch('/auth/me/api-keys').then((r) => r.json()),
  });

  // Mutations
  const updatePasswordMutation = useMutation({
    mutationFn: (data: any) =>
      authenticatedFetch('/auth/me', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }).then(async (r) => {
        if (!r.ok) {
          const err = await r.json();
          throw new Error(err.detail || 'Failed to update password');
        }
        return r.json();
      }),
    onSuccess: (data) => {
      setToken(data.access_token);
      toast.success('Password updated successfully');
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const uploadKeyMutation = useMutation({
    mutationFn: (data: { name: string; public_key_pem: string }) =>
      authenticatedFetch('/auth/me/signing-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }).then((r) => r.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-signing-keys'] });
      setUploadKeyOpen(false);
      toast.success('Signing key uploaded');
    },
  });

  const generateKeyPairMutation = useMutation({
    mutationFn: (data: { name: string }) =>
      authenticatedFetch('/auth/me/signing-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }).then((r) => r.json()),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['my-signing-keys'] });
      setGeneratedSigningKey(data);
      toast.success('Keypair generated');
    },
  });

  const deleteKeyMutation = useMutation({
    mutationFn: (id: string) =>
      authenticatedFetch(`/auth/me/signing-keys/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-signing-keys'] });
      toast.success('Signing key deleted');
    },
  });

  const generateApiKeyMutation = useMutation({
    mutationFn: (data: { name: string; expires_in_days?: number }) =>
      authenticatedFetch('/auth/me/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }).then((r) => r.json()),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['my-api-keys'] });
      setGeneratedApiKey(data);
      toast.success('API key generated');
    },
  });

  const revokeApiKeyMutation = useMutation({
    mutationFn: (id: string) =>
      authenticatedFetch(`/auth/me/api-keys/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-api-keys'] });
      toast.success('API key revoked');
    },
  });

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error('New passwords do not match');
      return;
    }
    updatePasswordMutation.mutate({
      current_password: passwordForm.current_password,
      password: passwordForm.new_password,
    });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const downloadKey = (name: string, content: string) => {
    const element = document.createElement('a');
    const file = new Blob([content], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `${name}_private_key.pem`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const getRoleBadge = (role: string) => {
    switch (role?.toLowerCase()) {
      case 'admin':
        return <Badge className="bg-red-500/10 text-red-400 border-red-500/20">Admin</Badge>;
      case 'operator':
        return <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">Operator</Badge>;
      case 'viewer':
        return <Badge className="bg-muted/50 text-muted-foreground border-muted/50">Viewer</Badge>;
      default:
        return <Badge variant="outline">{role}</Badge>;
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 p-6 text-foreground min-h-screen bg-card">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Account Center</h1>
      </div>

      {/* SECTION 1 - Profile */}
      <Card className="bg-background border-muted shadow-xl">
        <CardHeader className="flex flex-row items-center space-x-4 pb-4">
          <div className="p-3 bg-muted rounded-lg">
            <User className="w-6 h-6 text-muted-foreground" />
          </div>
          <div>
            <CardTitle>Profile</CardTitle>
            <CardDescription className="text-muted-foreground">Your account details and role</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-1">
              <Label className="text-muted-foreground">Username</Label>
              <div className="text-lg font-medium">{profile?.username || '...'}</div>
            </div>
            <div className="space-y-1">
              <Label className="text-muted-foreground">System Role</Label>
              <div className="flex items-center pt-1">
                {profileLoading ? <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /> : getRoleBadge(profile?.role || '')}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* SECTION 2 - Security (Password Change) */}
      <Card className="bg-background border-muted shadow-xl">
        <CardHeader className="flex flex-row items-center space-x-4 pb-4">
          <div className="p-3 bg-muted rounded-lg">
            <Shield className="w-6 h-6 text-muted-foreground" />
          </div>
          <div>
            <CardTitle>Security</CardTitle>
            <CardDescription className="text-muted-foreground">Change your account password</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePasswordSubmit} className="max-w-md space-y-4">
            <div className="space-y-2">
              <Label htmlFor="current_password">Current Password</Label>
              <Input
                id="current_password"
                type="password"
                className="bg-card border-muted focus:ring-muted"
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new_password">New Password</Label>
              <Input
                id="new_password"
                type="password"
                className="bg-card border-muted focus:ring-muted"
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirm New Password</Label>
              <Input
                id="confirm_password"
                type="password"
                className="bg-card border-muted focus:ring-muted"
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                required
              />
            </div>
            <Button
              type="submit"
              className="bg-foreground text-background hover:bg-foreground/90"
              disabled={updatePasswordMutation.isPending}
            >
              {updatePasswordMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Update Password
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* SECTION 3 - Signing Keys */}
      <Card className="bg-background border-muted shadow-xl">
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div className="flex flex-row items-center space-x-4">
            <div className="p-3 bg-muted rounded-lg">
              <KeyRound className="w-6 h-6 text-muted-foreground" />
            </div>
            <div>
              <CardTitle>Signing Keys</CardTitle>
              <CardDescription className="text-muted-foreground">Manage Ed25519 keys for job validation</CardDescription>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="border-muted hover:bg-muted" onClick={() => setUploadKeyOpen(true)}>
              <Plus className="w-4 h-4 mr-2" /> Upload
            </Button>
            <Button size="sm" className="bg-foreground text-background hover:bg-foreground/90" onClick={() => setGenKeyOpen(true)}>
              <KeyRound className="w-4 h-4 mr-2" /> Generate Keypair
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {keysLoading ? (
            <div className="flex justify-center p-8"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-muted text-muted-foreground text-sm">
                    <th className="py-3 px-4 font-medium">Name</th>
                    <th className="py-3 px-4 font-medium">Public Key (Truncated)</th>
                    <th className="py-3 px-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-muted">
                  {signingKeys?.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="py-8 text-center text-muted-foreground italic">No signing keys found.</td>
                    </tr>
                  ) : (
                    signingKeys?.map((key) => (
                      <tr key={key.id} className="hover:bg-muted/30 transition-colors">
                        <td className="py-4 px-4 font-medium">{key.name}</td>
                        <td className="py-4 px-4">
                          <code className="text-xs bg-card px-2 py-1 rounded text-muted-foreground">
                            {key.public_key_pem.substring(0, 40)}...
                          </code>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-muted-foreground hover:text-red-400 hover:bg-red-400/10"
                            onClick={() => setDeleteKeyConfirm(key.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SECTION 4 - API Keys */}
      <Card className="bg-background border-muted shadow-xl">
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div className="flex flex-row items-center space-x-4">
            <div className="p-3 bg-muted rounded-lg">
              <Key className="w-6 h-6 text-muted-foreground" />
            </div>
            <div>
              <CardTitle>API Keys</CardTitle>
              <CardDescription className="text-muted-foreground">Keys for programmatic access to Puppeteer</CardDescription>
            </div>
          </div>
          <Button size="sm" className="bg-foreground text-background hover:bg-foreground/90" onClick={() => setGenApiKeyOpen(true)}>
            <Plus className="w-4 h-4 mr-2" /> Generate API Key
          </Button>
        </CardHeader>
        <CardContent>
          {apiKeysLoading ? (
            <div className="flex justify-center p-8"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-muted text-muted-foreground text-sm">
                    <th className="py-3 px-4 font-medium">Name</th>
                    <th className="py-3 px-4 font-medium">Prefix</th>
                    <th className="py-3 px-4 font-medium">Expires</th>
                    <th className="py-3 px-4 font-medium">Last Used</th>
                    <th className="py-3 px-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-muted">
                  {apiKeys?.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground italic">No API keys found.</td>
                    </tr>
                  ) : (
                    apiKeys?.map((key) => (
                      <tr key={key.id} className="hover:bg-muted/30 transition-colors">
                        <td className="py-4 px-4 font-medium">{key.name}</td>
                        <td className="py-4 px-4">
                          <code className="text-xs bg-card px-2 py-1 rounded text-muted-foreground font-mono">
                            {key.key_prefix}
                          </code>
                        </td>
                        <td className="py-4 px-4 text-muted-foreground text-sm">
                          {key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}
                        </td>
                        <td className="py-4 px-4 text-muted-foreground text-sm">
                          {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}
                        </td>
                        <td className="py-4 px-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-muted-foreground hover:text-red-400 hover:bg-red-400/10"
                            onClick={() => setRevokeApiKeyConfirm(key.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* DIALOGS */}

      {/* Upload Signing Key Dialog */}
      <Dialog open={uploadKeyOpen} onOpenChange={setUploadKeyOpen}>
        <DialogContent className="bg-background border-muted text-foreground">
          <DialogHeader>
            <DialogTitle>Upload Signing Key</DialogTitle>
            <DialogDescription className="text-muted-foreground">Add an existing Ed25519 public key in PEM format.</DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.currentTarget);
              uploadKeyMutation.mutate({
                name: formData.get('name') as string,
                public_key_pem: formData.get('public_key_pem') as string,
              });
            }}
            className="space-y-4 pt-4"
          >
            <div className="space-y-2">
              <Label htmlFor="key_name">Key Name</Label>
              <Input id="key_name" name="name" className="bg-card border-muted" placeholder="My Dev Key" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="public_key_pem">Public Key (PEM)</Label>
              <Textarea
                id="public_key_pem"
                name="public_key_pem"
                className="bg-card border-muted font-mono text-xs h-32"
                placeholder="-----BEGIN PUBLIC KEY-----..."
                required
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => setUploadKeyOpen(false)}>Cancel</Button>
              <Button type="submit" className="bg-foreground text-background hover:bg-foreground/90">Upload Key</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Generate Keypair Dialog */}
      <Dialog open={genKeyOpen} onOpenChange={(open) => {
        setGenKeyOpen(open);
        if (!open) setGeneratedSigningKey(null);
      }}>
        <DialogContent className="bg-background border-muted text-foreground max-w-2xl">
          <DialogHeader>
            <DialogTitle>Generate Ed25519 Keypair</DialogTitle>
            <DialogDescription className="text-muted-foreground">We'll generate a secure keypair for you. The public key will be saved.</DialogDescription>
          </DialogHeader>
          
          {!generatedSigningKey ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                generateKeyPairMutation.mutate({ name: formData.get('name') as string });
              }}
              className="space-y-4 pt-4"
            >
              <div className="space-y-2">
                <Label htmlFor="gen_key_name">Key Name</Label>
                <Input id="gen_key_name" name="name" className="bg-card border-muted" placeholder="My Workspace Key" required />
              </div>
              <DialogFooter>
                <Button type="button" variant="ghost" onClick={() => setGenKeyOpen(false)}>Cancel</Button>
                <Button type="submit" className="bg-foreground text-background hover:bg-foreground/90" disabled={generateKeyPairMutation.isPending}>
                  {generateKeyPairMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Generate Keypair
                </Button>
              </DialogFooter>
            </form>
          ) : (
            <div className="space-y-6 pt-4">
              <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-lg flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
                <div className="text-sm text-amber-200">
                  <p className="font-bold">Save this private key now.</p>
                  <p>It cannot be retrieved later. For your security, we do not store private keys.</p>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Private Key (PEM)</Label>
                <pre className="bg-card border border-muted p-4 rounded font-mono text-xs overflow-x-auto max-h-64 whitespace-pre-wrap text-foreground/80">
                  {generatedSigningKey.private_key_pem}
                </pre>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" size="sm" className="border-muted hover:bg-muted" onClick={() => copyToClipboard(generatedSigningKey.private_key_pem)}>
                  <Copy className="w-4 h-4 mr-2" /> Copy
                </Button>
                <Button variant="outline" size="sm" className="border-muted hover:bg-muted" onClick={() => downloadKey(generatedSigningKey.name, generatedSigningKey.private_key_pem)}>
                  <Download className="w-4 h-4 mr-2" /> Download
                </Button>
                <Button className="bg-foreground text-background hover:bg-foreground/90" onClick={() => setGenKeyOpen(false)}>Done</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Generate API Key Dialog */}
      <Dialog open={genApiKeyOpen} onOpenChange={(open) => {
        setGenApiKeyOpen(open);
        if (!open) setGeneratedApiKey(null);
      }}>
        <DialogContent className="bg-background border-muted text-foreground">
          <DialogHeader>
            <DialogTitle>Generate API Key</DialogTitle>
            <DialogDescription className="text-muted-foreground">Create a key for external integrations.</DialogDescription>
          </DialogHeader>

          {!generatedApiKey ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                const days = formData.get('expires_in_days');
                generateApiKeyMutation.mutate({
                  name: formData.get('name') as string,
                  expires_in_days: days ? parseInt(days as string) : undefined,
                });
              }}
              className="space-y-4 pt-4"
            >
              <div className="space-y-2">
                <Label htmlFor="api_key_name">Key Name</Label>
                <Input id="api_key_name" name="name" className="bg-card border-muted" placeholder="CI/CD Integration" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="expires_in_days">Expiration (Days, optional)</Label>
                <Input id="expires_in_days" name="expires_in_days" type="number" className="bg-card border-muted" placeholder="30" />
              </div>
              <DialogFooter>
                <Button type="button" variant="ghost" onClick={() => setGenApiKeyOpen(false)}>Cancel</Button>
                <Button type="submit" className="bg-foreground text-background hover:bg-foreground/90" disabled={generateApiKeyMutation.isPending}>
                  {generateApiKeyMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Generate Key
                </Button>
              </DialogFooter>
            </form>
          ) : (
            <div className="space-y-6 pt-4">
              <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-lg flex items-start space-x-3">
                <Shield className="w-5 h-5 text-amber-500 mt-0.5" />
                <div className="text-sm text-amber-200">
                  <p className="font-bold">Copy your API key now.</p>
                  <p>This key will not be shown again.</p>
                </div>
              </div>
              <div className="space-y-2">
                <Label>API Key</Label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-card border border-muted p-3 rounded font-mono text-sm break-all text-foreground/80">
                    {generatedApiKey.raw_key}
                  </code>
                  <Button variant="outline" size="icon" className="border-muted shrink-0" onClick={() => copyToClipboard(generatedApiKey.raw_key)}>
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              <DialogFooter>
                <Button className="w-full bg-foreground text-background hover:bg-foreground/90" onClick={() => setGenApiKeyOpen(false)}>I have saved my key</Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* AlertDialogs for Deletion/Revocation */}
      <AlertDialog open={!!deleteKeyConfirm} onOpenChange={(open) => !open && setDeleteKeyConfirm(null)}>
        <AlertDialogContent className="bg-background border-muted text-foreground">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Signing Key?</AlertDialogTitle>
            <AlertDialogDescription className="text-muted-foreground">
              This action cannot be undone. Jobs signed with this key will no longer be verifiable.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border-muted hover:bg-muted hover:text-foreground">Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-500 hover:bg-red-600 text-foreground"
              onClick={() => deleteKeyConfirm && deleteKeyMutation.mutate(deleteKeyConfirm)}
            >
              Delete Key
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={!!revokeApiKeyConfirm} onOpenChange={(open) => !open && setRevokeApiKeyConfirm(null)}>
        <AlertDialogContent className="bg-background border-muted text-foreground">
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke API Key?</AlertDialogTitle>
            <AlertDialogDescription className="text-muted-foreground">
              Any applications using this key will lose access immediately.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border-muted hover:bg-muted hover:text-foreground">Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-500 hover:bg-red-600 text-foreground"
              onClick={() => revokeApiKeyConfirm && revokeApiKeyMutation.mutate(revokeApiKeyConfirm)}
            >
              Revoke Key
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Account;
