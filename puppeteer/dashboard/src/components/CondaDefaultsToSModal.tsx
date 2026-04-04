import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface CondaDefaultsToSModalProps {
    isOpen: boolean;
    onAcknowledge: () => void;
    onCancel: () => void;
}

export const CondaDefaultsToSModal: React.FC<CondaDefaultsToSModalProps> = ({
    isOpen,
    onAcknowledge,
    onCancel,
}) => {
    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="w-6 h-6 text-amber-500" />
                        <DialogTitle>Anaconda defaults Channel — Commercial Terms</DialogTitle>
                    </div>
                </DialogHeader>

                <div className="space-y-4 text-sm">
                    <DialogDescription>
                        Anaconda's <code className="bg-muted px-2 py-1 rounded font-mono text-xs">defaults</code> channel is a commercial service
                        that may require a license agreement for organizations with 200 or more employees.
                    </DialogDescription>

                    <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg p-4 space-y-2">
                        <p className="font-semibold text-amber-900 dark:text-amber-200">Terms of Service</p>
                        <p className="text-amber-800 dark:text-amber-300">
                            By selecting the Anaconda defaults channel, you acknowledge that you have read and agreed to
                            <a
                                href="https://www.anaconda.com/terms-of-service"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="underline font-medium hover:opacity-75"
                            >
                                Anaconda's Terms of Service
                            </a>.
                        </p>
                    </div>

                    <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4 space-y-2">
                        <p className="font-semibold text-blue-900 dark:text-blue-200">Recommendation</p>
                        <p className="text-blue-800 dark:text-blue-300">
                            We recommend using <code className="bg-muted px-2 py-1 rounded font-mono text-xs">conda-forge</code> instead.
                            It is a free, community-maintained alternative that works with all Conda-compatible tools.
                        </p>
                    </div>

                    <p className="text-xs text-muted-foreground">
                        Once you acknowledge this, you won't be asked again in this session. Other users will still see this warning
                        when they select the defaults channel.
                    </p>
                </div>

                <DialogFooter className="gap-2">
                    <Button variant="outline" onClick={onCancel}>
                        Cancel
                    </Button>
                    <Button onClick={onAcknowledge} className="bg-amber-600 hover:bg-amber-700">
                        I Acknowledge
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
