import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { CondaDefaultsToSModal } from './CondaDefaultsToSModal';
import { authenticatedFetch } from '../auth';

interface SmelterIngredientSelectorProps {
    onIngredientSelect?: (ingredient: {
        ecosystem: string;
        channel?: string;
        name: string;
        version_constraint: string;
    }) => void;
}

const ECOSYSTEMS = ['PYPI', 'APT', 'APK', 'NPM', 'NUGET', 'OCI_HUB', 'OCI_GHCR', 'CONDA'];

const CONDA_CHANNELS = ['conda-forge', 'defaults'];

export const SmelterIngredientSelector: React.FC<SmelterIngredientSelectorProps> = ({
    onIngredientSelect,
}) => {
    const [selectedEcosystem, setSelectedEcosystem] = useState<string>('PYPI');
    const [selectedChannel, setSelectedChannel] = useState<string>('conda-forge');
    const [ingredientName, setIngredientName] = useState<string>('');
    const [versionConstraint, setVersionConstraint] = useState<string>('*');
    const [showCondaDefaultsModal, setShowCondaDefaultsModal] = useState<boolean>(false);
    const [condaDefaultsAcknowledged, setCondaDefaultsAcknowledged] = useState<boolean>(false);
    const [approvalBlocked, setApprovalBlocked] = useState<boolean>(false);

    // Fetch mirror config on mount to check if current user has acknowledged Conda defaults ToS
    const { data: mirrorConfig } = useQuery({
        queryKey: ['mirror-config'],
        queryFn: async () => {
            const response = await authenticatedFetch('/api/admin/mirror-config');
            if (!response.ok) throw new Error('Failed to fetch mirror config');
            return response.json();
        },
        staleTime: 1000 * 60 * 5, // 5 minutes
    });

    // Initialize acknowledgment status when config loads
    useEffect(() => {
        if (mirrorConfig?.conda_defaults_acknowledged_by_current_user !== undefined) {
            setCondaDefaultsAcknowledged(mirrorConfig.conda_defaults_acknowledged_by_current_user);
        }
    }, [mirrorConfig]);

    // Pre-select conda-forge when ecosystem is CONDA
    useEffect(() => {
        if (selectedEcosystem === 'CONDA') {
            setSelectedChannel('conda-forge');
        }
    }, [selectedEcosystem]);

    // Check if approval should be blocked (Conda defaults selected but not acknowledged)
    useEffect(() => {
        const isCondaDefaults =
            selectedEcosystem === 'CONDA' && selectedChannel === 'defaults';
        const shouldBlock = isCondaDefaults && !condaDefaultsAcknowledged;
        setApprovalBlocked(shouldBlock);
        if (shouldBlock) {
            setShowCondaDefaultsModal(true);
        }
    }, [selectedEcosystem, selectedChannel, condaDefaultsAcknowledged]);

    // Mutation to acknowledge Conda defaults ToS
    const acknowledgeCondaDefaultsMutation = useMutation({
        mutationFn: async () => {
            const response = await authenticatedFetch('/api/admin/conda-defaults-acknowledge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channel: 'defaults' }),
            });
            if (!response.ok) throw new Error('Failed to acknowledge Conda defaults ToS');
            return response.json();
        },
        onSuccess: () => {
            setCondaDefaultsAcknowledged(true);
            setShowCondaDefaultsModal(false);
            setApprovalBlocked(false);
            toast.success('Conda defaults ToS acknowledged. You may now proceed.');
        },
        onError: (error) => {
            toast.error(`Failed to acknowledge ToS: ${error instanceof Error ? error.message : 'Unknown error'}`);
        },
    });

    const handleCondaDefaultsAcknowledge = async () => {
        await acknowledgeCondaDefaultsMutation.mutateAsync();
    };

    const handleCondaDefaultsCancel = () => {
        setShowCondaDefaultsModal(false);
        // Reset channel selection back to conda-forge
        setSelectedChannel('conda-forge');
        setApprovalBlocked(false);
    };

    const handleApproveIngredient = () => {
        if (!ingredientName.trim()) {
            toast.error('Please enter an ingredient name');
            return;
        }

        if (approvalBlocked) {
            toast.error('Conda defaults ToS must be acknowledged before proceeding');
            return;
        }

        const ingredient = {
            ecosystem: selectedEcosystem,
            ...(selectedEcosystem === 'CONDA' && { channel: selectedChannel }),
            name: ingredientName,
            version_constraint: versionConstraint || '*',
        };

        if (onIngredientSelect) {
            onIngredientSelect(ingredient);
        }

        // Reset form
        setIngredientName('');
        setVersionConstraint('*');
        if (selectedEcosystem === 'CONDA') {
            setSelectedChannel('conda-forge');
        }

        toast.success(`Ingredient "${ingredientName}" approved for ${selectedEcosystem}`);
    };

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label htmlFor="ecosystem">Ecosystem</Label>
                    <Select value={selectedEcosystem} onValueChange={setSelectedEcosystem}>
                        <SelectTrigger id="ecosystem">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {ECOSYSTEMS.map((eco) => (
                                <SelectItem key={eco} value={eco}>
                                    {eco}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {selectedEcosystem === 'CONDA' && (
                    <div className="space-y-2">
                        <Label htmlFor="channel">Conda Channel</Label>
                        <Select value={selectedChannel} onValueChange={setSelectedChannel}>
                            <SelectTrigger id="channel">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {CONDA_CHANNELS.map((ch) => (
                                    <SelectItem key={ch} value={ch}>
                                        {ch}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {selectedChannel === 'defaults' && !condaDefaultsAcknowledged && (
                            <p className="text-xs text-amber-600 dark:text-amber-400">
                                Requires ToS acknowledgment before proceeding
                            </p>
                        )}
                    </div>
                )}

                <div className="space-y-2">
                    <Label htmlFor="name">Package Name</Label>
                    <Input
                        id="name"
                        placeholder="e.g., requests, curl, jq"
                        value={ingredientName}
                        onChange={(e) => setIngredientName(e.target.value)}
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="version">Version Constraint</Label>
                    <Input
                        id="version"
                        placeholder="e.g., 2.28.1 or * for latest"
                        value={versionConstraint}
                        onChange={(e) => setVersionConstraint(e.target.value)}
                    />
                </div>
            </div>

            <div className="flex justify-end">
                <Button
                    onClick={handleApproveIngredient}
                    disabled={approvalBlocked || !ingredientName.trim()}
                    className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
                >
                    {approvalBlocked ? 'Acknowledge ToS to Proceed' : 'Approve Ingredient'}
                </Button>
            </div>

            <CondaDefaultsToSModal
                isOpen={showCondaDefaultsModal}
                onAcknowledge={handleCondaDefaultsAcknowledge}
                onCancel={handleCondaDefaultsCancel}
            />
        </div>
    );
};
