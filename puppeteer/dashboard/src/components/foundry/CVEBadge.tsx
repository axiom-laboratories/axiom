import React, { useState } from 'react';
import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';

interface CVEDetail {
  cve_id: string;
  cvss_score: number | null;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  description: string;
  fix_versions: string[];
  affected_package: string;
  is_transitive: boolean;
}

interface CVEBadgeProps {
  cve_count: number;
  worst_severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | null;
  cves: CVEDetail[];
  ingredient_name: string;
}

const severityColors = {
  CRITICAL: "bg-[hsl(var(--cve-critical-bg))] text-[hsl(var(--cve-critical-fg))]",
  HIGH: "bg-[hsl(var(--cve-high-bg))] text-[hsl(var(--cve-high-fg))]",
  MEDIUM: "bg-[hsl(var(--cve-medium-bg))] text-[hsl(var(--cve-medium-fg))]",
  LOW: "bg-[hsl(var(--cve-low-bg))] text-[hsl(var(--cve-low-fg))]",
};

const severityEmoji = {
  CRITICAL: "🟥",
  HIGH: "🟧",
  MEDIUM: "🟨",
  LOW: "🟦",
};

export const CVEBadge: React.FC<CVEBadgeProps> = ({
  cve_count,
  worst_severity,
  cves,
  ingredient_name,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [selectedCveIdx, setSelectedCveIdx] = useState<number | null>(null);

  // Clean badge case
  if (cve_count === 0) {
    return (
      <div className="inline-flex items-center gap-1 px-2 py-1 rounded text-sm font-medium bg-[hsl(var(--cve-clean-bg))] text-[hsl(var(--cve-clean-fg))]">
        <span>✅</span>
        <span>Clean</span>
      </div>
    );
  }

  // CVE badge case
  if (!worst_severity) {
    return null;
  }

  const badgeClass = severityColors[worst_severity];
  const emoji = severityEmoji[worst_severity];

  return (
    <div className="inline-block">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`inline-flex items-center gap-1 px-2 py-1 rounded text-sm font-medium hover:opacity-80 transition-opacity ${badgeClass}`}
        aria-label={`${cve_count} ${worst_severity} vulnerabilities`}
      >
        <span>{emoji}</span>
        <span>{cve_count}</span>
        <span>{worst_severity}</span>
        {expanded ? (
          <ChevronDown size={14} />
        ) : (
          <ChevronRight size={14} />
        )}
      </button>

      {expanded && (
        <div className="mt-2 p-3 bg-muted rounded border border-border space-y-3">
          {cves.map((cve, idx) => (
            <div key={`${cve.cve_id}-${idx}`} className="space-y-2">
              <div
                className="flex items-start gap-2 cursor-pointer hover:bg-accent/5 dark:hover:bg-accent/10 p-2 rounded transition-colors"
                onClick={() =>
                  setSelectedCveIdx(selectedCveIdx === idx ? null : idx)
                }
              >
                <div
                  className={`px-2 py-1 rounded text-xs font-semibold whitespace-nowrap ${severityColors[cve.severity]}`}
                >
                  {cve.severity}
                </div>
                <div className="flex-1 min-w-0">
                  <a
                    href={`https://nvd.nist.gov/vuln/detail/${cve.cve_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline dark:text-blue-400 font-mono text-sm inline-flex items-center gap-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {cve.cve_id}
                    <ExternalLink size={12} />
                  </a>
                </div>
              </div>

              {selectedCveIdx === idx && (
                <div className="ml-2 pl-3 border-l-2 border-border space-y-2 text-sm">
                  {cve.cvss_score !== null && (
                    <div>
                      <span className="font-semibold">CVSS Score:</span>{" "}
                      {cve.cvss_score.toFixed(1)}
                    </div>
                  )}

                  <div>
                    <span className="font-semibold">Description:</span>{" "}
                    {cve.description}
                  </div>

                  {cve.fix_versions && cve.fix_versions.length > 0 && (
                    <div>
                      <span className="font-semibold">Fix:</span> upgrade to{" "}
                      {cve.fix_versions[0]}
                    </div>
                  )}

                  <div>
                    <span className="font-semibold">Affected:</span>{" "}
                    {cve.affected_package}
                  </div>

                  {cve.is_transitive && (
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      <span className="font-semibold">Type:</span> Transitive
                      dependency
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CVEBadge;
