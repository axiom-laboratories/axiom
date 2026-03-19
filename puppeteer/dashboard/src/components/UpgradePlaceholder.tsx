import { Lock } from 'lucide-react';

interface Props {
  feature: string;
  description: string;
}

export function UpgradePlaceholder({ feature, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <div className="flex flex-col items-center gap-4 max-w-md text-center">
        <div className="h-16 w-16 rounded-2xl bg-zinc-800 border border-zinc-700 flex items-center justify-center">
          <Lock className="h-8 w-8 text-zinc-500" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-semibold text-white">Enterprise Edition Required</h2>
          <p className="text-sm text-zinc-400">{feature} is available in Axiom Enterprise Edition.</p>
          <p className="text-sm text-zinc-500">{description}</p>
        </div>
        <div className="flex gap-3 pt-2">
          <a
            href="https://axiom.run/enterprise"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Learn More
          </a>
        </div>
      </div>
    </div>
  );
}
