import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react';
import { toast } from 'sonner';

interface MirrorConfigCardProps {
    ecosystem: string;
    displayName: string;
    url: string;
    healthStatus: 'ok' | 'warn' | 'error';
    onUpdate: (newUrl: string) => Promise<void>;
    canEdit: boolean;
}

export function MirrorConfigCard({
    ecosystem,
    displayName,
    url,
    healthStatus,
    onUpdate,
    canEdit,
}: MirrorConfigCardProps) {
    const [editUrl, setEditUrl] = useState(url);
    const [isSaving, setIsSaving] = useState(false);

    const handleBlur = async () => {
        if (editUrl === url || !canEdit) {
            return;
        }

        setIsSaving(true);
        try {
            await onUpdate(editUrl);
            toast.success(`${displayName} mirror URL updated`);
        } catch (error) {
            setEditUrl(url); // Revert on error
            toast.error(`Failed to update ${displayName} mirror URL`);
        } finally {
            setIsSaving(false);
        }
    };

    const getHealthColor = () => {
        switch (healthStatus) {
            case 'ok':
                return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
            case 'warn':
                return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
            case 'error':
                return 'bg-red-500/20 text-red-400 border-red-500/30';
        }
    };

    const getHealthIcon = () => {
        switch (healthStatus) {
            case 'ok':
                return <CheckCircle2 className="h-4 w-4" />;
            case 'warn':
                return <AlertCircle className="h-4 w-4" />;
            case 'error':
                return <XCircle className="h-4 w-4" />;
        }
    };

    const getHealthText = () => {
        switch (healthStatus) {
            case 'ok':
                return 'Healthy';
            case 'warn':
                return 'Unreachable';
            case 'error':
                return 'Error';
        }
    };

    return (
        <Card className="bg-card border-muted/50 shadow-none">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-bold text-foreground">
                        {displayName}
                    </CardTitle>
                    <Badge
                        variant="outline"
                        className={`flex items-center gap-1.5 border ${getHealthColor()}`}
                    >
                        {getHealthIcon()}
                        <span className="text-xs font-semibold">{getHealthText()}</span>
                    </Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <label className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
                        Mirror URL
                    </label>
                    <Input
                        type="url"
                        value={editUrl}
                        onChange={(e) => setEditUrl(e.target.value)}
                        onBlur={handleBlur}
                        disabled={!canEdit || isSaving}
                        placeholder="http://mirror:8080"
                        className="bg-secondary border-muted h-10 font-mono text-sm"
                    />
                </div>
                {!canEdit && (
                    <p className="text-xs text-muted-foreground">
                        Read-only: Admin access required to edit
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
