import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2, Package, HardDrive, Clock } from 'lucide-react';

interface Template {
  id: string;
  friendly_name: string;
  description?: string;
  base_image?: string;
  package_count?: number;
  blueprint?: {
    packages?: Array<{
      name: string;
      ecosystem: string;
      version_constraint?: string;
    }>;
  };
}

interface BuildConfirmationDialogProps {
  template: Template;
  isOpen: boolean;
  onClose: () => void;
  onBuild: () => Promise<void>;
}

// Calculate ecosystem-specific build times
const calculateBuildTime = (template: Template): { min: number; max: number } => {
  const times: Record<string, number> = {
    PYPI: 30,
    APT: 5,
    APK: 3,
    NUGET: 20,
    OCI: 15
  };

  let totalSeconds = 0;
  const ecosystems = new Set<string>();

  if (template.blueprint?.packages) {
    for (const pkg of template.blueprint.packages) {
      ecosystems.add(pkg.ecosystem.toUpperCase());
      totalSeconds += times[pkg.ecosystem.toUpperCase()] || 10;
    }
  }

  // Add 10s overhead
  totalSeconds += 10;

  // Calculate min and max with buffer
  const minMinutes = Math.max(1, Math.floor(totalSeconds / 60));
  const maxMinutes = Math.ceil((totalSeconds * 1.2) / 60); // 20% buffer for max

  return { min: minMinutes, max: maxMinutes };
};

// Count packages by ecosystem
const countByEcosystem = (template: Template): Record<string, number> => {
  const counts: Record<string, number> = {};

  if (template.blueprint?.packages) {
    for (const pkg of template.blueprint.packages) {
      const eco = pkg.ecosystem.toUpperCase();
      counts[eco] = (counts[eco] || 0) + 1;
    }
  }

  return counts;
};

export default function BuildConfirmationDialog({
  template,
  isOpen,
  onClose,
  onBuild
}: BuildConfirmationDialogProps) {
  const [isBuilding, setIsBuilding] = useState(false);
  const buildTime = calculateBuildTime(template);
  const packageCounts = countByEcosystem(template);

  const handleBuild = async () => {
    setIsBuilding(true);
    try {
      await onBuild();
    } finally {
      setIsBuilding(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => {
      if (!open && !isBuilding) {
        onClose();
      }
    }}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Ready to Build {template.friendly_name}?</DialogTitle>
        </DialogHeader>

        <Card className="bg-muted/50 border-muted">
          <CardContent className="pt-6 space-y-4">
            {/* Template Name */}
            <div>
              <h3 className="text-lg font-semibold text-foreground mb-1">
                {template.friendly_name}
              </h3>
              {template.description && (
                <p className="text-sm text-muted-foreground">
                  {template.description}
                </p>
              )}
            </div>

            {/* Base OS */}
            <div className="flex items-center gap-2 text-sm">
              <HardDrive className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Base OS:</span>
              <span className="font-medium text-foreground">
                {template.base_image || 'Default'}
              </span>
            </div>

            {/* Package Count by Ecosystem */}
            <div>
              <div className="flex items-center gap-2 mb-2 text-sm">
                <Package className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground font-medium">Packages:</span>
              </div>
              <div className="grid grid-cols-2 gap-2 ml-6">
                {Object.entries(packageCounts).length > 0 ? (
                  Object.entries(packageCounts).map(([ecosystem, count]) => (
                    <div key={ecosystem} className="text-sm text-muted-foreground">
                      <span className="font-medium">{count}</span> {ecosystem}
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground">No packages selected</div>
                )}
              </div>
            </div>

            {/* Estimated Build Time */}
            <div className="flex items-center gap-2 text-sm">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Est. Build Time:</span>
              <span className="font-medium text-foreground">
                {buildTime.min}–{buildTime.max} minutes
              </span>
            </div>
          </CardContent>
        </Card>

        <DialogFooter className="flex gap-2 justify-end">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isBuilding}
          >
            Cancel
          </Button>
          <Button
            onClick={handleBuild}
            disabled={isBuilding}
            className="bg-pink-600 hover:bg-pink-700 text-white"
          >
            {isBuilding ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Building...
              </>
            ) : (
              'Build'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
