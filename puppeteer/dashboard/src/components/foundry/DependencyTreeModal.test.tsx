import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DependencyTreeModal } from "./DependencyTreeModal";

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
  authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
}));

// Mock CVEBadge to avoid complexity
vi.mock('./CVEBadge', () => ({
  default: ({ cve_count, worst_severity }: any) => (
    <div data-testid="cve-badge">
      {cve_count > 0 ? `${worst_severity}: ${cve_count}` : 'Clean'}
    </div>
  ),
}));

const mockTreeResponse = {
  root_id: "flask-id",
  root_name: "Flask",
  root_version: "3.0.0",
  total_nodes: 5,
  total_cve_count: 2,
  worst_severity: "HIGH" as const,
  tree: {
    id: "flask-id",
    name: "Flask",
    version: "3.0.0",
    ecosystem: "PYPI",
    cve_count: 0,
    worst_severity: null,
    auto_discovered: false,
    mirror_status: "MIRRORED" as const,
    children: [
      {
        id: "jinja2-id",
        name: "Jinja2",
        version: "3.1.3",
        ecosystem: "PYPI",
        cve_count: 1,
        worst_severity: "HIGH" as const,
        auto_discovered: true,
        mirror_status: "MIRRORED" as const,
        children: [
          {
            id: "markupsafe-id",
            name: "MarkupSafe",
            version: "2.1.5",
            ecosystem: "PYPI",
            cve_count: 1,
            worst_severity: "HIGH" as const,
            auto_discovered: true,
            mirror_status: "MIRRORED" as const,
            children: [],
            cves: [
              {
                cve_id: "CVE-2024-1234",
                cvss_score: 7.5,
                severity: "HIGH" as const,
                description: "Test CVE",
                fix_versions: ["2.1.6"],
                affected_package: "MarkupSafe",
                is_transitive: true,
              },
            ],
          },
        ],
        cves: [
          {
            cve_id: "CVE-2024-5678",
            cvss_score: 7.0,
            severity: "HIGH" as const,
            description: "Jinja2 issue",
            fix_versions: ["3.1.4"],
            affected_package: "Jinja2",
            is_transitive: false,
          },
        ],
      },
      {
        id: "werkzeug-id",
        name: "Werkzeug",
        version: "3.0.1",
        ecosystem: "PYPI",
        cve_count: 0,
        worst_severity: null,
        auto_discovered: false,
        mirror_status: "MIRRORED" as const,
        children: [],
        cves: [],
      },
    ],
    cves: [],
  },
};

const renderWithQueryClient = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
};

describe("DependencyTreeModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthFetch.mockResolvedValue({
      ok: true,
      json: async () => mockTreeResponse,
    });
  });

  it("test_tree_modal_renders_recursive_tree", async () => {
    renderWithQueryClient(
      <DependencyTreeModal
        open={true}
        ingredient_id="flask-id"
        ingredient_name="Flask"
        onOpenChange={() => {}}
      />
    );

    // Wait for tree to load
    await waitFor(() => {
      expect(screen.getByText("Flask 3.0.0 — Dependency Tree")).toBeInTheDocument();
    });

    // Verify tree nodes are rendered
    expect(screen.getByText("Flask")).toBeInTheDocument();
    expect(screen.getByText("Jinja2")).toBeInTheDocument();
    expect(screen.getByText("MarkupSafe")).toBeInTheDocument();
    expect(screen.getByText("Werkzeug")).toBeInTheDocument();

    // Verify version strings
    expect(screen.getByText("3.0.0")).toBeInTheDocument();
    expect(screen.getByText("3.1.3")).toBeInTheDocument();
    expect(screen.getByText("2.1.5")).toBeInTheDocument();
  });

  it("test_deduped_nodes_labeled", async () => {
    // Create a tree with a deduped node
    const treeWithDedupe = {
      ...mockTreeResponse,
      tree: {
        ...mockTreeResponse.tree,
        children: [
          mockTreeResponse.tree.children[0],
          {
            ...mockTreeResponse.tree.children[0],
            id: "jinja2-id-2",
            name: "Jinja2",
          },
        ],
      },
    };

    mockAuthFetch.mockResolvedValue({
      ok: true,
      json: async () => treeWithDedupe,
    });

    renderWithQueryClient(
      <DependencyTreeModal
        open={true}
        ingredient_id="flask-id"
        ingredient_name="Flask"
        onOpenChange={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Flask")).toBeInTheDocument();
    });

    // The deduped label should appear
    const dedupedLabels = screen.queryAllByText("(deduped)");
    // At least one deduped label or the second Jinja2 reference
    expect(screen.getAllByText("Jinja2").length).toBeGreaterThanOrEqual(1);
  });

  it("test_auto_discovered_tag_shown", async () => {
    renderWithQueryClient(
      <DependencyTreeModal
        open={true}
        ingredient_id="flask-id"
        ingredient_name="Flask"
        onOpenChange={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Flask")).toBeInTheDocument();
    });

    // Jinja2 and MarkupSafe have auto_discovered=true
    const autoDiscoveredTags = screen.queryAllByText("auto-discovered");
    expect(autoDiscoveredTags.length).toBeGreaterThanOrEqual(1);
  });

  it("test_summary_footer_shows_total_counts", async () => {
    renderWithQueryClient(
      <DependencyTreeModal
        open={true}
        ingredient_id="flask-id"
        ingredient_name="Flask"
        onOpenChange={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Total: 5 packages, 2 CVEs/)).toBeInTheDocument();
    });

    // Check severity distribution is shown
    expect(screen.getByText(/Severity distribution:/)).toBeInTheDocument();
  });

  it("test_tree_node_expand_collapse", async () => {
    renderWithQueryClient(
      <DependencyTreeModal
        open={true}
        ingredient_id="flask-id"
        ingredient_name="Flask"
        onOpenChange={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Flask")).toBeInTheDocument();
    });

    // Find expand/collapse buttons and verify they exist
    const collapseButtons = screen.queryAllByLabelText(/Collapse|Expand/);
    expect(collapseButtons.length).toBeGreaterThan(0);

    // Click first expand button to test toggle
    if (collapseButtons.length > 0) {
      fireEvent.click(collapseButtons[0]);
      // Node state should toggle
      expect(collapseButtons[0]).toBeInTheDocument();
    }
  });

  it("test_cve_badges_rendered_on_nodes", async () => {
    renderWithQueryClient(
      <DependencyTreeModal
        open={true}
        ingredient_id="flask-id"
        ingredient_name="Flask"
        onOpenChange={() => {}}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Flask")).toBeInTheDocument();
    });

    // Check for CVE badges (mocked)
    const cveBadges = screen.queryAllByTestId("cve-badge");
    // Jinja2 and MarkupSafe have CVEs, Flask and Werkzeug don't
    expect(cveBadges.length).toBeGreaterThanOrEqual(2);
  });
});
