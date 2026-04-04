import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Loader2, CheckCircle2, AlertCircle, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { authenticatedFetch } from '../auth';
import { getUser } from '../auth';

interface AnalyzedPackage {
    package_name: string;
    import_name: string;
    ecosystem: string;
    confidence: 'High' | 'Medium' | 'Low';
    mapped: boolean;
    status: 'approved' | 'new' | 'pending';
    blueprints?: string[];
    node_count?: number;
}

interface AnalyzeScriptResponse {
    detected_language: string;
    suggestions: AnalyzedPackage[];
    approved_list: string[];
    pending_review_list: string[];
}

interface ScriptAnalysisRequest {
    package_name: string;
    ecosystem: string;
    detected_import: string;
    source_script_hash: string;
}

export const ScriptAnalyzerPanel: React.FC = () => {
    const [scriptText, setScriptText] = useState<string>('');
    const [detectedLanguage, setDetectedLanguage] = useState<string>('python');
    const [selectedLanguage, setSelectedLanguage] = useState<string>('python');
    const [analysisResults, setAnalysisResults] = useState<AnalyzedPackage[] | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
    const [selectedSuggestions, setSelectedSuggestions] = useState<Set<string>>(new Set());
    const [selectAllNew, setSelectAllNew] = useState<boolean>(false);
    const [analysisError, setAnalysisError] = useState<string>('');

    const user = getUser();
    const isAdmin = user?.role === 'admin';
    const canApprove = isAdmin; // Users with foundry:write permission (simplified for MVP)

    // Auto-detect language from script content
    useEffect(() => {
        if (!scriptText.trim()) {
            setDetectedLanguage('python');
            setSelectedLanguage('python');
            return;
        }

        let detected = 'bash';
        const text = scriptText.toLowerCase();

        // Check for Python indicators
        if (
            text.includes('import ') ||
            text.includes('from ') ||
            text.includes('def ') ||
            text.includes('class ') ||
            text.includes('#!/usr/bin/env python') ||
            text.includes('#!/usr/bin/python')
        ) {
            detected = 'python';
        }
        // Check for PowerShell indicators
        else if (
            text.includes('import-module') ||
            text.includes('install-module') ||
            text.includes('install-package') ||
            text.includes('#!/usr/bin/env pwsh') ||
            text.includes('#!powershell')
        ) {
            detected = 'powershell';
        }
        // Check for Bash indicators
        else if (
            text.includes('apt-get') ||
            text.includes('yum') ||
            text.includes('dnf') ||
            text.includes('apk add') ||
            text.includes('pip install') ||
            text.includes('#!/bin/bash') ||
            text.includes('#!/bin/sh')
        ) {
            detected = 'bash';
        }

        setDetectedLanguage(detected);
        if (!selectedLanguage || selectedLanguage === detectedLanguage) {
            setSelectedLanguage(detected);
        }
    }, [scriptText]);

    // Mutation for analyzing script
    const analyzeScriptMutation = useMutation({
        mutationFn: async () => {
            if (!scriptText.trim()) {
                throw new Error('Please paste a script');
            }

            const response = await authenticatedFetch('/api/analyzer/analyze-script', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    script_content: scriptText,
                    language: selectedLanguage,
                }),
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Analysis failed' }));
                throw new Error(error.detail || 'Analysis failed');
            }

            return response.json() as Promise<AnalyzeScriptResponse>;
        },
        onSuccess: (data) => {
            setAnalysisResults(data.suggestions || []);
            setSelectedSuggestions(new Set());
            setSelectAllNew(false);
            setAnalysisError('');

            if (!data.suggestions || data.suggestions.length === 0) {
                toast.info('No packages detected in script');
            } else {
                const newCount = data.suggestions.filter(s => s.status === 'new').length;
                toast.success(`Found ${data.suggestions.length} packages (${newCount} new)`);
            }
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : 'Analysis failed';
            setAnalysisResults(null);
            setAnalysisError(message);
            toast.error(message);
        },
    });

    // Mutation for approving selected packages
    const approveSelectedMutation = useMutation({
        mutationFn: async () => {
            const selectedArray = Array.from(selectedSuggestions);
            if (selectedArray.length === 0) {
                throw new Error('Select at least one package');
            }

            // Call approve endpoint for each selected package
            const results = await Promise.all(
                selectedArray.map((packageName) => {
                    const suggestion = analysisResults?.find(s => s.package_name === packageName);
                    if (!suggestion) return Promise.reject(new Error(`Package not found: ${packageName}`));

                    return authenticatedFetch('/api/analyzer/requests', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            package_name: packageName,
                            ecosystem: suggestion.ecosystem,
                            detected_import: suggestion.import_name,
                        }),
                    }).then(async (res) => {
                        if (!res.ok) {
                            const error = await res.json().catch(() => ({}));
                            throw new Error(error.detail || `Failed to approve ${packageName}`);
                        }
                        return res.json();
                    });
                })
            );

            return results;
        },
        onSuccess: () => {
            toast.success(`Approved ${selectedSuggestions.size} packages`);
            setSelectedSuggestions(new Set());
            setSelectAllNew(false);
            // Optionally re-run analysis to update statuses
            analyzeScriptMutation.mutate();
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : 'Approval failed';
            toast.error(message);
        },
    });

    // Mutation for requesting approval (non-admin users)
    const requestApprovalMutation = useMutation({
        mutationFn: async () => {
            const selectedArray = Array.from(selectedSuggestions);
            if (selectedArray.length === 0) {
                throw new Error('Select at least one package');
            }

            const results = await Promise.all(
                selectedArray.map((packageName) => {
                    const suggestion = analysisResults?.find(s => s.package_name === packageName);
                    if (!suggestion) return Promise.reject(new Error(`Package not found: ${packageName}`));

                    return authenticatedFetch('/api/analyzer/requests', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            package_name: packageName,
                            ecosystem: suggestion.ecosystem,
                            detected_import: suggestion.import_name,
                        }),
                    }).then(async (res) => {
                        if (!res.ok) {
                            const error = await res.json().catch(() => ({}));
                            throw new Error(error.detail || `Failed to request approval for ${packageName}`);
                        }
                        return res.json();
                    });
                })
            );

            return results;
        },
        onSuccess: () => {
            toast.success(`Requested approval for ${selectedSuggestions.size} packages`);
            setSelectedSuggestions(new Set());
            setSelectAllNew(false);
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : 'Request failed';
            toast.error(message);
        },
    });

    const handleAnalyzeClick = () => {
        setAnalysisError('');
        analyzeScriptMutation.mutate();
    };

    const handleToggleSelection = (packageName: string) => {
        const newSet = new Set(selectedSuggestions);
        if (newSet.has(packageName)) {
            newSet.delete(packageName);
        } else {
            newSet.add(packageName);
        }
        setSelectedSuggestions(newSet);
    };

    const handleSelectAllNew = () => {
        if (selectAllNew) {
            setSelectedSuggestions(new Set());
            setSelectAllNew(false);
        } else {
            const newPackages = analysisResults
                ?.filter(s => s.status === 'new')
                .map(s => s.package_name) || [];
            setSelectedSuggestions(new Set(newPackages));
            setSelectAllNew(true);
        }
    };

    const newPackagesCount = analysisResults?.filter(s => s.status === 'new').length || 0;
    const groupedResults: Record<string, AnalyzedPackage[]> = {};

    if (analysisResults) {
        analysisResults.forEach((result) => {
            const ecosystem = result.ecosystem || 'Unknown';
            if (!groupedResults[ecosystem]) {
                groupedResults[ecosystem] = [];
            }
            groupedResults[ecosystem].push(result);
        });
    }

    return (
        <div className="space-y-6">
            {/* Analyzer Form */}
            <div className="space-y-4">
                <div className="space-y-2">
                    <label htmlFor="script" className="text-sm font-medium">Script Content</label>
                    <Textarea
                        id="script"
                        placeholder="Paste your Python, Bash, or PowerShell script here..."
                        value={scriptText}
                        onChange={(e) => setScriptText(e.target.value)}
                        className="h-48"
                    />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label htmlFor="language" className="text-sm font-medium">Language</label>
                        <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                            <SelectTrigger id="language">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="python">Python</SelectItem>
                                <SelectItem value="bash">Bash / Shell</SelectItem>
                                <SelectItem value="powershell">PowerShell</SelectItem>
                            </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">Detected: {detectedLanguage}</p>
                    </div>

                    <div className="flex items-end">
                        <Button
                            onClick={handleAnalyzeClick}
                            disabled={isAnalyzing || !scriptText.trim()}
                            className="w-full"
                        >
                            {isAnalyzing ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Analyzing...
                                </>
                            ) : (
                                'Analyze Script'
                            )}
                        </Button>
                    </div>
                </div>

                {analysisError && (
                    <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex gap-3">
                        <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
                        <div className="text-sm text-red-800 dark:text-red-300">{analysisError}</div>
                    </div>
                )}
            </div>

            {/* Results Table */}
            {analysisResults && analysisResults.length > 0 && (
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold">Analysis Results</h3>
                        {newPackagesCount > 0 && (
                            <Badge variant="secondary">
                                {selectedSuggestions.size} of {newPackagesCount} new selected
                            </Badge>
                        )}
                    </div>

                    {/* Grouped by Ecosystem */}
                    {Object.entries(groupedResults).map(([ecosystem, suggestions]) => (
                        <div key={ecosystem} className="space-y-3">
                            <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                                {ecosystem}
                            </h4>

                            <div className="border border-muted rounded-lg overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead className="bg-muted/50 border-b border-muted">
                                        <tr>
                                            <th className="px-4 py-2 text-left">
                                                {newPackagesCount > 0 && suggestions.some(s => s.status === 'new') && (
                                                    <Checkbox
                                                        checked={selectAllNew && suggestions
                                                            .filter(s => s.status === 'new')
                                                            .every(s => selectedSuggestions.has(s.package_name))}
                                                        onCheckedChange={handleSelectAllNew}
                                                    />
                                                )}
                                            </th>
                                            <th className="px-4 py-2 text-left font-medium">Package</th>
                                            <th className="px-4 py-2 text-left font-medium">Import/Command</th>
                                            <th className="px-4 py-2 text-left font-medium">Confidence</th>
                                            <th className="px-4 py-2 text-left font-medium">Status</th>
                                            <th className="px-4 py-2 text-left font-medium">Details</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-muted">
                                        {suggestions.map((suggestion) => (
                                            <tr
                                                key={suggestion.package_name}
                                                className={`hover:bg-muted/50 transition-colors ${
                                                    suggestion.status === 'approved' ? 'opacity-60 bg-muted/30' : ''
                                                }`}
                                            >
                                                <td className="px-4 py-3">
                                                    {suggestion.status !== 'approved' && (
                                                        <Checkbox
                                                            checked={selectedSuggestions.has(suggestion.package_name)}
                                                            onCheckedChange={() =>
                                                                handleToggleSelection(suggestion.package_name)
                                                            }
                                                            disabled={suggestion.status === 'approved'}
                                                        />
                                                    )}
                                                </td>
                                                <td className="px-4 py-3 font-medium">{suggestion.package_name}</td>
                                                <td className="px-4 py-3 text-muted-foreground text-xs">
                                                    {suggestion.import_name}
                                                    {suggestion.mapped && (
                                                        <span className="ml-2 inline-flex items-center gap-1">
                                                            <Info className="h-3 w-3" />
                                                            <span className="text-xs text-blue-600 dark:text-blue-400">mapped</span>
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <Badge
                                                        variant={
                                                            suggestion.confidence === 'High'
                                                                ? 'default'
                                                                : suggestion.confidence === 'Medium'
                                                                    ? 'secondary'
                                                                    : 'outline'
                                                        }
                                                    >
                                                        {suggestion.confidence}
                                                    </Badge>
                                                </td>
                                                <td className="px-4 py-3">
                                                    {suggestion.status === 'approved' && (
                                                        <Badge className="bg-green-600">Approved</Badge>
                                                    )}
                                                    {suggestion.status === 'new' && (
                                                        <Badge className="bg-blue-600">New</Badge>
                                                    )}
                                                    {suggestion.status === 'pending' && (
                                                        <Badge className="bg-amber-600">Pending</Badge>
                                                    )}
                                                </td>
                                                <td className="px-4 py-3 text-xs text-muted-foreground">
                                                    {suggestion.status === 'approved' && suggestion.blueprints && (
                                                        <div className="space-y-1">
                                                            <div>In: {suggestion.blueprints.join(', ')}</div>
                                                            {suggestion.node_count !== undefined && (
                                                                <div>Ready on {suggestion.node_count} nodes</div>
                                                            )}
                                                        </div>
                                                    )}
                                                    {suggestion.status === 'pending' && (
                                                        <div>Awaiting admin review</div>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ))}

                    {/* Action Buttons */}
                    {selectedSuggestions.size > 0 && (
                        <div className="flex gap-3 justify-end pt-4">
                            {canApprove ? (
                                <Button
                                    onClick={() => approveSelectedMutation.mutate()}
                                    disabled={approveSelectedMutation.isPending}
                                    className="bg-green-600 hover:bg-green-700"
                                >
                                    {approveSelectedMutation.isPending ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Approving...
                                        </>
                                    ) : (
                                        `Approve Selected (${selectedSuggestions.size})`
                                    )}
                                </Button>
                            ) : (
                                <Button
                                    onClick={() => requestApprovalMutation.mutate()}
                                    disabled={requestApprovalMutation.isPending}
                                    variant="outline"
                                >
                                    {requestApprovalMutation.isPending ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Requesting...
                                        </>
                                    ) : (
                                        `Request Approval (${selectedSuggestions.size})`
                                    )}
                                </Button>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Empty State */}
            {analysisResults && analysisResults.length === 0 && (
                <div className="text-center py-12">
                    <CheckCircle2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">No packages detected in script</p>
                </div>
            )}
        </div>
    );
};
