import React from 'react';
import { Calendar, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export interface LicenceStatusProps {
  status: 'valid' | 'grace' | 'expired' | 'ce';
  tier: string;
  organization?: string;
  customerID?: string;
  nodeLimit?: number;
  currentNodeCount?: number;
  daysUntilExpiry: number;
  expiryDate?: string;
  lastReloadTime?: string;
}

const STATUS_CONFIG = {
  valid: {
    badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    icon: CheckCircle2,
    label: 'Active',
    description: 'Licence is valid and active',
  },
  grace: {
    badge: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    icon: AlertCircle,
    label: 'Grace Period',
    description: 'Licence will expire soon',
  },
  expired: {
    badge: 'bg-red-500/20 text-red-400 border-red-500/30',
    icon: AlertCircle,
    label: 'Expired',
    description: 'Licence has expired',
  },
  ce: {
    badge: 'bg-muted text-muted-foreground border-muted',
    icon: CheckCircle2,
    label: 'Community Edition',
    description: 'Running Community Edition',
  },
};

export const LicenceStatus: React.FC<LicenceStatusProps> = ({
  status,
  tier,
  organization,
  customerID,
  nodeLimit,
  currentNodeCount,
  daysUntilExpiry,
  expiryDate,
  lastReloadTime,
}) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.ce;
  const Icon = config.icon;

  const nodeUtilization = nodeLimit && currentNodeCount
    ? Math.round((currentNodeCount / nodeLimit) * 100)
    : 0;

  return (
    <Card className="bg-card border-muted/50">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-lg font-semibold text-foreground">Licence Status</CardTitle>
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${config.badge}`}>
          <Icon className="h-4 w-4" />
          <span className="text-xs font-bold">{config.label}</span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Tier */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Edition</span>
          <span className="text-sm font-medium text-foreground">{tier}</span>
        </div>

        {/* Organization (EE only) */}
        {status !== 'ce' && organization && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Organization</span>
            <span className="text-sm font-medium text-foreground">{organization}</span>
          </div>
        )}

        {/* Customer ID (EE only) */}
        {status !== 'ce' && customerID && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Customer ID</span>
            <span className="text-xs font-mono text-foreground/80">{customerID}</span>
          </div>
        )}

        {/* Node Limit (EE only) */}
        {status !== 'ce' && nodeLimit && nodeLimit > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Node Limit</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">
                {currentNodeCount || 0} / {nodeLimit}
              </span>
              <Badge
                className={`text-xs font-bold ${
                  nodeUtilization >= 80
                    ? 'bg-red-500/20 text-red-400'
                    : nodeUtilization >= 60
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'bg-emerald-500/20 text-emerald-400'
                }`}
              >
                {nodeUtilization}%
              </Badge>
            </div>
          </div>
        )}

        {/* Expiry Date (EE only) */}
        {status !== 'ce' && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Expires</span>
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span
                className={`text-sm font-medium ${
                  status === 'expired'
                    ? 'text-red-400'
                    : status === 'grace'
                    ? 'text-amber-400'
                    : 'text-emerald-400'
                }`}
              >
                {expiryDate || `in ${daysUntilExpiry} days`}
              </span>
            </div>
          </div>
        )}

        {/* Last Reload */}
        {lastReloadTime && (
          <div className="flex items-center justify-between pt-2 border-t border-muted">
            <span className="text-xs text-muted-foreground">Last reloaded</span>
            <span className="text-xs text-muted-foreground">{lastReloadTime}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
