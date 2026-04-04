import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, ChevronDown, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import CVEBadge from './CVEBadge';
import { authenticatedFetch } from '@/auth';

interface CVEDetail {
  cve_id: string;
  cvss_score: number | null;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  description: string;
  fix_versions: string[];
  affected_package: string;
  is_transitive: boolean;
}

interface DependencyTreeNode {
  id: string;
  name: string;
  version: string;
  ecosystem: string;
  cve_count: number;
  worst_severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | null;
  auto_discovered: boolean;
  mirror_status: "PENDING" | "MIRRORED" | "FAILED";
  children: DependencyTreeNode[];
  cves: CVEDetail[];
}

interface DependencyTreeResponse {
  root_id: string;
  root_name: string;
  root_version: string;
  total_nodes: number;
  total_cve_count: number;
  worst_severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | null;
  tree: DependencyTreeNode;
}

interface DependencyTreeModalProps {
  open: boolean;
  ingredient_id: string;
  ingredient_name: string;
  onOpenChange: (open: boolean) => void;
}

interface TreeNodeState {
  [key: string]: boolean; // node_id -> expanded
}

const TreeNode: React.FC<{
  node: DependencyTreeNode;
  depth: number;
  expanded: TreeNodeState;
  onToggleExpand: (nodeId: string) => void;
  visitedIds: Set<string>;
}> = ({ node, depth, expanded, onToggleExpand, visitedIds }) => {
  const isDeduped = visitedIds.has(node.id);
  const isExpanded = expanded[node.id] ?? true;
  const hasChildren = node.children && node.children.length > 0 && !isDeduped;

  // Indent multiplier per depth
  const indentPx = depth * 20;

  return (
    <div key={node.id} className="space-y-1">
      <div
        style={{ marginLeft: `${indentPx}px` }}
        className="flex items-center gap-2 py-1"
      >
        {hasChildren ? (
          <button
            onClick={() => onToggleExpand(node.id)}
            className="p-0 hover:bg-accent/5 dark:hover:bg-accent/10 rounded"
            aria-label={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? (
              <ChevronDown size={16} />
            ) : (
              <ChevronRight size={16} />
            )}
          </button>
        ) : (
          <div className="w-4" />
        )}

        <div className="flex-1 font-mono text-sm space-x-2 flex items-center">
          <span>{node.name}</span>
          <span className="text-muted-foreground">
            {node.version}
          </span>

          {node.auto_discovered && (
            <span className="text-xs bg-[hsl(var(--cve-low-bg))] text-[hsl(var(--cve-low-fg))] px-2 py-0.5 rounded">
              auto-discovered
            </span>
          )}

          {isDeduped && (
            <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded">
              (deduped)
            </span>
          )}
        </div>

        {node.cve_count > 0 && (
          <CVEBadge
            cve_count={node.cve_count}
            worst_severity={node.worst_severity}
            cves={node.cves}
            ingredient_name={node.name}
          />
        )}

        {node.cve_count === 0 && (
          <div className="text-xs text-[hsl(var(--cve-clean-fg))]">
            ✅
          </div>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              onToggleExpand={onToggleExpand}
              visitedIds={
                new Set([...visitedIds, node.id])
              }
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const DependencyTreeModal: React.FC<DependencyTreeModalProps> = ({
  open,
  ingredient_id,
  ingredient_name,
  onOpenChange,
}) => {
  const [expandedNodes, setExpandedNodes] = useState<TreeNodeState>({});

  const { data: treeData, isLoading, error } = useQuery({
    queryKey: ['smelter-tree', ingredient_id],
    queryFn: async () => {
      if (!ingredient_id) return null;
      const res = await authenticatedFetch(
        `/api/smelter/ingredients/${ingredient_id}/tree`
      );
      if (!res.ok) throw new Error('Failed to fetch tree');
      return res.json() as Promise<DependencyTreeResponse>;
    },
    enabled: open && !!ingredient_id,
  });

  const toggleExpand = (nodeId: string) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [nodeId]: !prev[nodeId],
    }));
  };

  // Calculate severity distribution
  const severityDistribution = useMemo(() => {
    if (!treeData) return { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };

    const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };

    const traverse = (node: DependencyTreeNode) => {
      if (node.worst_severity) {
        counts[node.worst_severity]++;
      }
      node.children?.forEach(traverse);
    };

    traverse(treeData.tree);
    return counts;
  }, [treeData]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>
            {treeData?.root_name || ingredient_name} {treeData?.root_version}
            {' '} — Dependency Tree
          </DialogTitle>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="animate-spin mr-2" size={20} />
            Loading dependency tree...
          </div>
        )}

        {error && (
          <div className="text-[hsl(var(--cve-critical-fg))]">
            Error loading tree: {error.message}
          </div>
        )}

        {treeData && (
          <>
            <div className="bg-muted rounded p-4 font-mono text-sm space-y-1">
              <TreeNode
                node={treeData.tree}
                depth={0}
                expanded={expandedNodes}
                onToggleExpand={toggleExpand}
                visitedIds={new Set()}
              />
            </div>

            <DialogFooter className="border-t pt-4 mt-4">
              <div className="flex flex-col gap-2 w-full">
                <div className="text-sm text-muted-foreground">
                  Total: {treeData.total_nodes} packages,{' '}
                  {treeData.total_cve_count} CVEs
                </div>
                <div className="text-xs text-muted-foreground">
                  Severity distribution: {severityDistribution.CRITICAL} CRITICAL,{' '}
                  {severityDistribution.HIGH} HIGH,{' '}
                  {severityDistribution.MEDIUM} MEDIUM,{' '}
                  {severityDistribution.LOW} LOW
                </div>
              </div>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default DependencyTreeModal;
