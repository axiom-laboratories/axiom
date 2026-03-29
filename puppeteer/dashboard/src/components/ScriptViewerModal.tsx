import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check, Copy } from 'lucide-react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { authenticatedFetch } from '../auth';

const ReactDiffViewer = React.lazy(() => import('react-diff-viewer-continued'));

interface ScriptViewerModalProps {
    open: boolean;
    onClose: () => void;
    jobDefId: string;
    versionNumber?: number;
    scriptContent?: string;
    runtime?: string;
}

const runtimeLabel = (runtime?: string): string => {
    switch (runtime?.toLowerCase()) {
        case 'python': return 'Python';
        case 'bash': return 'Bash';
        case 'powershell': return 'PowerShell';
        default: return runtime ?? '';
    }
};

const ScriptViewerModal: React.FC<ScriptViewerModalProps> = ({
    open,
    onClose,
    jobDefId,
    versionNumber,
    scriptContent,
    runtime,
}) => {
    const [copied, setCopied] = React.useState(false);
    const [showDiff, setShowDiff] = React.useState(false);

    // Reset diff view when modal opens/closes or version changes
    React.useEffect(() => {
        if (!open) setShowDiff(false);
    }, [open, versionNumber]);

    // Fetch current version script if versionNumber is provided
    const { data: currentVersion, isLoading: currentLoading } = useQuery({
        queryKey: ['script-version', jobDefId, versionNumber],
        queryFn: async () => {
            const res = await authenticatedFetch(
                `/api/jobs/definitions/${jobDefId}/versions/${versionNumber}`
            );
            if (!res.ok) throw new Error('Failed to fetch version');
            return res.json() as Promise<{ script_content: string; version_number: number }>;
        },
        enabled: open && !!jobDefId && versionNumber != null,
    });

    // Fetch previous version script for diff
    const prevVersionNumber = versionNumber != null && versionNumber > 1 ? versionNumber - 1 : null;
    const { data: previousVersion, isLoading: prevLoading } = useQuery({
        queryKey: ['script-version', jobDefId, prevVersionNumber],
        queryFn: async () => {
            const res = await authenticatedFetch(
                `/api/jobs/definitions/${jobDefId}/versions/${prevVersionNumber}`
            );
            if (!res.ok) throw new Error('Failed to fetch previous version');
            return res.json() as Promise<{ script_content: string; version_number: number }>;
        },
        enabled: showDiff && !!jobDefId && prevVersionNumber != null,
    });

    const displayScript =
        versionNumber != null
            ? (currentVersion?.script_content ?? '')
            : (scriptContent ?? '');

    const title =
        versionNumber != null
            ? `Script — v${versionNumber}`
            : 'Script';

    const canCompare = versionNumber != null && versionNumber > 1;

    const handleCopy = () => {
        navigator.clipboard.writeText(displayScript);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    const isLoading = versionNumber != null && currentLoading;

    return (
        <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
            <DialogContent className="max-w-3xl bg-zinc-950 border-zinc-800 text-white">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-white">
                        {title}
                        {runtime && (
                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border bg-zinc-800 text-zinc-400 border-zinc-700">
                                {runtimeLabel(runtime)}
                            </span>
                        )}
                    </DialogTitle>
                </DialogHeader>

                {/* Toolbar */}
                <div className="flex items-center gap-2 justify-end -mt-2 mb-1">
                    {canCompare && (
                        <button
                            onClick={() => setShowDiff(d => !d)}
                            className={`text-xs px-2.5 py-1 rounded border transition-colors ${
                                showDiff
                                    ? 'bg-blue-500/20 text-blue-300 border-blue-500/40 hover:bg-blue-500/30'
                                    : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:bg-zinc-700 hover:text-zinc-200'
                            }`}
                            disabled={prevLoading}
                        >
                            {prevLoading
                                ? 'Loading…'
                                : showDiff
                                    ? `Hide diff`
                                    : `Compare with v${prevVersionNumber}`}
                        </button>
                    )}
                    <button
                        onClick={handleCopy}
                        className="flex items-center gap-1 text-xs px-2.5 py-1 rounded border bg-zinc-800 text-zinc-400 border-zinc-700 hover:bg-zinc-700 hover:text-zinc-200 transition-colors"
                    >
                        {copied ? (
                            <>
                                <Check className="h-3 w-3 text-green-400" />
                                <span className="text-green-400">Copied</span>
                            </>
                        ) : (
                            <>
                                <Copy className="h-3 w-3" />
                                Copy
                            </>
                        )}
                    </button>
                </div>

                {/* Content */}
                {isLoading ? (
                    <div className="h-40 bg-zinc-900 rounded-lg animate-pulse" />
                ) : showDiff && previousVersion ? (
                    <React.Suspense fallback={<div className="text-zinc-500 text-sm py-4">Loading diff...</div>}>
                        <div className="overflow-auto max-h-[60vh] rounded-lg border border-zinc-800 text-xs">
                            <ReactDiffViewer
                                oldValue={previousVersion.script_content}
                                newValue={displayScript}
                                leftTitle={`v${prevVersionNumber}`}
                                rightTitle={`v${versionNumber}`}
                                useDarkTheme={true}
                                splitView={true}
                            />
                        </div>
                    </React.Suspense>
                ) : (
                    <pre className="bg-zinc-900 rounded-lg p-4 overflow-auto text-sm font-mono text-zinc-200 max-h-[60vh] whitespace-pre-wrap">
                        {displayScript || <span className="text-zinc-600 italic">No script content</span>}
                    </pre>
                )}
            </DialogContent>
        </Dialog>
    );
};

export default ScriptViewerModal;
