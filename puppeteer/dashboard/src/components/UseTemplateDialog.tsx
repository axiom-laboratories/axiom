import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { authenticatedFetch } from '../auth';
import BuildConfirmationDialog from './BuildConfirmationDialog';

interface Template {
  id: string;
  friendly_name: string;
  description?: string;
  is_starter?: boolean;
  base_image?: string;
  package_count?: number;
  status?: string;
}

interface UseTemplateDialogProps {
  template: Template | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function UseTemplateDialog({ template, isOpen, onClose }: UseTemplateDialogProps) {
  const [action, setAction] = useState<'build' | 'customize' | null>(null);

  const buildMutation = useMutation({
    mutationFn: async () => {
      const res = await authenticatedFetch(`/api/templates/${template?.id}/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_approve: true })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Build failed');
      }
      return await res.json();
    },
    onSuccess: (data) => {
      toast.success(`Build started for ${template?.friendly_name}`);
      setAction(null);
      onClose();
    },
    onError: (err: Error) => {
      toast.error(err.message);
    }
  });

  const cloneMutation = useMutation({
    mutationFn: async () => {
      const res = await authenticatedFetch(`/api/templates/${template?.id}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          friendly_name: `${template?.friendly_name} (Custom)`
        })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Clone failed');
      }
      return await res.json();
    },
    onSuccess: (clonedTemplate) => {
      toast.success(`Template cloned: ${clonedTemplate.friendly_name}`);
      // Navigate to blueprint wizard for the cloned template
      // This will be handled by parent component via callback
      setAction(null);
      onClose();
      // Emit event or callback to navigate to wizard
      window.dispatchEvent(new CustomEvent('navigate-to-wizard', {
        detail: { templateId: clonedTemplate.id }
      }));
    },
    onError: (err: Error) => {
      toast.error(err.message);
    }
  });

  // Return null if template is not available
  if (!template) {
    return null;
  }

  // If action is 'build', show BuildConfirmationDialog
  if (action === 'build') {
    return (
      <BuildConfirmationDialog
        template={template}
        isOpen={isOpen}
        onClose={() => {
          setAction(null);
          onClose();
        }}
        onBuild={async () => {
          await buildMutation.mutateAsync();
        }}
      />
    );
  }

  // Show initial dialog with two action buttons
  return (
    <Dialog open={isOpen && action !== 'build'} onOpenChange={(open) => {
      if (!open) {
        setAction(null);
        onClose();
      }
    }}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Use {template?.friendly_name}?</DialogTitle>
          <DialogDescription>
            Build Now creates a ready-to-use node image. Customize First lets you modify packages before building.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <p className="text-sm text-muted-foreground mb-4">
            {template?.description}
          </p>
          {template?.package_count && (
            <p className="text-sm text-muted-foreground">
              Package count: {template.package_count}
            </p>
          )}
        </div>

        <DialogFooter className="flex gap-2 justify-end">
          <Button
            variant="outline"
            onClick={() => {
              setAction('customize');
              cloneMutation.mutate();
            }}
            disabled={cloneMutation.isPending}
          >
            {cloneMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Customizing...
              </>
            ) : (
              'Customize First'
            )}
          </Button>
          <Button
            onClick={() => setAction('build')}
            className="bg-pink-600 hover:bg-pink-700 text-white"
          >
            Build Now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
