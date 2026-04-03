import { AlertCircle, X } from 'lucide-react';
import { useState } from 'react';

interface MirrorHealthBannerProps {
  isEE: boolean;
  mirrorsAvailable: boolean;
}

export function MirrorHealthBanner({
  isEE,
  mirrorsAvailable
}: MirrorHealthBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (!isEE || mirrorsAvailable || dismissed) {
    return null;
  }

  return (
    <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded p-4 flex items-start gap-3 mb-4">
      <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <h3 className="font-semibold text-amber-900 dark:text-amber-100">
          Mirror services not running
        </h3>
        <p className="text-sm text-amber-800 dark:text-amber-200 mt-1">
          EE is active but mirror services are unreachable. To enable mirrors, run:
        </p>
        <code className="block bg-amber-100 dark:bg-amber-900 text-amber-900 dark:text-amber-100 text-xs p-2 mt-2 rounded font-mono overflow-auto">
          docker compose -f compose.server.yaml -f compose.ee.yaml up -d
        </code>
        <p className="text-xs text-amber-700 dark:text-amber-300 mt-2">
          Mirror services are only available in the standard Docker Compose deployment.
        </p>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 flex-shrink-0"
        aria-label="Dismiss"
      >
        <X className="w-5 h-5" />
      </button>
    </div>
  );
}
