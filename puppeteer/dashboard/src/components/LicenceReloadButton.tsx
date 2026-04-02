import React, { useState } from 'react';
import { RefreshCcw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { authenticatedFetch } from '../auth';

export interface LicenceReloadButtonProps {
  onReloadSuccess?: (newStatus: string) => void;
  disabled?: boolean;
  isAdmin?: boolean;
}

export const LicenceReloadButton: React.FC<LicenceReloadButtonProps> = ({
  onReloadSuccess,
  disabled = false,
  isAdmin = false,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [licenceKey, setLicenceKey] = useState('');

  const handleReload = async () => {
    if (!isAdmin) {
      toast.error('Only admins can reload the licence');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authenticatedFetch('/api/admin/licence/reload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ licence_key: licenceKey || null }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        const message =
          errorData?.detail?.message || errorData?.detail || 'Failed to reload licence';
        toast.error(`Licence reload failed: ${message}`);
        return;
      }

      const data = await res.json();
      toast.success(`Licence reloaded. New status: ${data.status}`);
      setLicenceKey('');
      setIsModalOpen(false);
      onReloadSuccess?.(data.status);
    } catch (error) {
      console.error('Licence reload error:', error);
      toast.error('Licence reload failed');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAdmin) {
    return null; // Hide button for non-admins
  }

  return (
    <>
      <Button
        onClick={() => setIsModalOpen(true)}
        disabled={disabled || isLoading}
        className="bg-primary hover:bg-primary/90 text-white font-bold gap-2"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Reloading...
          </>
        ) : (
          <>
            <RefreshCcw className="h-4 w-4" />
            Reload Licence
          </>
        )}
      </Button>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="bg-zinc-925 border-zinc-800 text-white">
          <DialogHeader>
            <DialogTitle>Reload Licence</DialogTitle>
            <DialogDescription>
              Enter an optional licence key to override the current configuration. Leave empty to use the configured key.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Licence Key (Optional)</Label>
              <Input
                placeholder="Paste your EE licence key here"
                value={licenceKey}
                onChange={(e) => setLicenceKey(e.target.value)}
                className="bg-zinc-950 border-zinc-800 font-mono text-sm"
                type="password"
              />
              <p className="text-xs text-zinc-500">
                If left empty, the system will use the configured AXIOM_LICENCE_KEY.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => {
                setIsModalOpen(false);
                setLicenceKey('');
              }}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleReload}
              disabled={isLoading}
              className="bg-primary hover:bg-primary/90 text-white font-bold gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Reloading...
                </>
              ) : (
                <>
                  <RefreshCcw className="h-4 w-4" />
                  Confirm Reload
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
