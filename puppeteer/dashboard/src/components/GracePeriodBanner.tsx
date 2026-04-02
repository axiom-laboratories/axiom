import React, { useState, useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface GracePeriodBannerProps {
  daysRemaining: number;
  expiryDate?: string;
  onDismiss?: () => void;
}

export const GracePeriodBanner: React.FC<GracePeriodBannerProps> = ({
  daysRemaining,
  expiryDate,
  onDismiss,
}) => {
  const [isDismissed, setIsDismissed] = useState(() => {
    // Check localStorage for dismissal flag
    return localStorage.getItem('grace-period-banner-dismissed') === 'true';
  });

  const handleDismiss = () => {
    localStorage.setItem('grace-period-banner-dismissed', 'true');
    setIsDismissed(true);
    onDismiss?.();
  };

  if (isDismissed) {
    return null;
  }

  const graceDayText =
    daysRemaining === 1 ? '1 day' : `${daysRemaining} days`;

  return (
    <div className="mb-4 flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
      <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-400" />
      <div className="flex-1">
        <p className="text-sm font-medium text-amber-400">Licence Grace Period</p>
        <p className="mt-1 text-sm text-amber-100">
          Your licence will expire in {graceDayText}{expiryDate ? ` (${expiryDate})` : ''}.
          Renew now to avoid service interruption.
        </p>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleDismiss}
        className="ml-auto h-6 w-6 flex-shrink-0 p-0 text-amber-400 hover:bg-amber-500/20 hover:text-amber-300"
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
};
