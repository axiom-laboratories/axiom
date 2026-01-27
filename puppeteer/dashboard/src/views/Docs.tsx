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
    const [content, setContent] = useState('');

    useEffect(() => {
        setContent(userGuideMd);
    }, []);

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Documentation & Wiki</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="prose prose-slate dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {content}
                        </ReactMarkdown>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default Docs;
