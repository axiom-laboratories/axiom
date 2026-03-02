import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// We'll fetch the raw markdown from GitHub or local server assets if possible.
// For now, let's hardcode the import or fetch it from a public URL if strictly needed.
// However, since we are in a monorepo, we can import it as a raw string if configured, 
// OR simpler: just paste the content here for the "Embedded" experience if dynamic fetching is complex without a backend file server.
// Let's try to fetch it from the backend API if we had a static file server.
// WITHOUT backend support for raw files, we can just bundle it.

// Bundling approach (simplest for "within orchestration server"):
// Note: Vite can import as string with ?raw suffix
import userGuideMd from '../assets/UserGuide.md?raw';

const Docs = () => {
    // Content is imported at build time, no need for effect or state
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">Documentation</h1>
                <p className="text-sm text-zinc-500 mt-1">System user guide and orchestration manuals.</p>
            </div>
            <Card className="bg-zinc-925 border-zinc-800/50">
                <CardContent className="pt-6">
                    <div className="prose prose-slate dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {userGuideMd}
                        </ReactMarkdown>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default Docs;
