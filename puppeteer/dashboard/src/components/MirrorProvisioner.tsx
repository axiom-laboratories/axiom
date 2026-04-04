/**
 * Mirror provisioner UI component.
 *
 * If provisioning_enabled is false:
 * - Shows read-only gray toggle (disabled) with docker compose command hint
 *
 * If provisioning_enabled is true:
 * - Shows enabled toggle switch that calls start/stop via useDockerApi hook
 * - Shows loading spinner while request in flight
 * - Updates status badge (running/stopped/error)
 */

import React from 'react';
import { Switch } from './ui/switch';
import { Loader } from 'lucide-react';
import { useDockerApi } from '../hooks/useDockerApi';
import { toast } from 'sonner';

interface MirrorProvisionerProps {
  ecosystem: string;
  provisioning_enabled: boolean;
}

const ECOSYSTEM_NAMES: Record<string, string> = {
  pypi: 'PyPI',
  apt: 'APT (Debian)',
  apk: 'APK (Alpine)',
  npm: 'npm',
  nuget: 'NuGet',
  oci_hub: 'OCI Hub',
  oci_ghcr: 'OCI GHCR',
  conda: 'Conda',
};

export function MirrorProvisioner({
  ecosystem,
  provisioning_enabled,
}: MirrorProvisionerProps) {
  const { status, isLoading, error, startService, stopService } = useDockerApi(ecosystem);

  const handleToggle = async (checked: boolean) => {
    try {
      if (checked) {
        await startService();
        toast.success(`${ECOSYSTEM_NAMES[ecosystem]} mirror started`);
      } else {
        await stopService();
        toast.success(`${ECOSYSTEM_NAMES[ecosystem]} mirror stopped`);
      }
    } catch (err) {
      console.error('Provisioning error:', err);
      const errorMsg = error || 'Failed to manage service';
      toast.error(errorMsg);
    }
  };

  if (!provisioning_enabled) {
    // Read-only mode with manual command hint
    const composeCmd = `docker compose -f compose.ee.yaml up -d ${ecosystem}`;
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Switch checked={false} disabled className="opacity-50" />
          <span className="text-sm text-muted-foreground">Provisioning disabled</span>
        </div>
        <div className="bg-muted p-2 rounded text-xs font-mono text-muted-foreground">
          {composeCmd}
        </div>
      </div>
    );
  }

  // Interactive mode with toggle
  const isChecked = status === 'running';
  const statusColor =
    status === 'running'
      ? 'text-green-600'
      : status === 'stopped'
        ? 'text-gray-600'
        : 'text-red-600';

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {isLoading && <Loader className="h-4 w-4 animate-spin text-blue-500" />}
        {!isLoading && (
          <Switch
            checked={isChecked}
            onCheckedChange={handleToggle}
            disabled={isLoading}
          />
        )}
        <span className={`text-sm font-medium ${statusColor}`}>
          {status === 'running' && 'Running'}
          {status === 'stopped' && 'Stopped'}
          {status === 'error' && 'Error'}
          {status === 'unknown' && 'Unknown'}
        </span>
      </div>
      {error && (
        <div className="bg-red-50 text-red-700 text-xs p-2 rounded">
          {error}
        </div>
      )}
    </div>
  );
}
