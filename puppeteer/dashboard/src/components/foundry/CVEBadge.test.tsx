import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CVEBadge } from "./CVEBadge";

interface CVEDetail {
  cve_id: string;
  cvss_score: number | null;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  description: string;
  fix_versions: string[];
  affected_package: string;
  is_transitive: boolean;
}

const mockCriticalCVE: CVEDetail = {
  cve_id: "CVE-2024-1234",
  cvss_score: 9.5,
  severity: "CRITICAL",
  description: "Critical vulnerability in package",
  fix_versions: ["1.2.3"],
  affected_package: "test-package",
  is_transitive: false,
};

const mockHighCVE: CVEDetail = {
  cve_id: "CVE-2024-5678",
  cvss_score: 7.5,
  severity: "HIGH",
  description: "High severity issue",
  fix_versions: ["2.0.0"],
  affected_package: "another-package",
  is_transitive: true,
};

describe("CVEBadge", () => {
  it("test_cve_badge_colors_by_severity", () => {
    // Test CRITICAL severity renders red
    const { rerender } = render(
      <CVEBadge
        cve_count={1}
        worst_severity="CRITICAL"
        cves={[mockCriticalCVE]}
        ingredient_name="test"
      />
    );

    const button = screen.getByRole("button");
    expect(button).toHaveClass("bg-red-100");
    expect(button).toHaveClass("text-red-900");

    // Test HIGH severity renders orange
    rerender(
      <CVEBadge
        cve_count={1}
        worst_severity="HIGH"
        cves={[mockHighCVE]}
        ingredient_name="test"
      />
    );

    expect(button).toHaveClass("bg-orange-100");

    // Test MEDIUM severity renders yellow
    rerender(
      <CVEBadge
        cve_count={1}
        worst_severity="MEDIUM"
        cves={[{ ...mockCriticalCVE, severity: "MEDIUM" }]}
        ingredient_name="test"
      />
    );

    expect(button).toHaveClass("bg-yellow-100");

    // Test LOW severity renders blue
    rerender(
      <CVEBadge
        cve_count={1}
        worst_severity="LOW"
        cves={[{ ...mockCriticalCVE, severity: "LOW" }]}
        ingredient_name="test"
      />
    );

    expect(button).toHaveClass("bg-blue-100");
  });

  it("test_cve_detail_panel_expandable", () => {
    render(
      <CVEBadge
        cve_count={1}
        worst_severity="CRITICAL"
        cves={[mockCriticalCVE]}
        ingredient_name="test"
      />
    );

    const button = screen.getByRole("button");

    // Initially detail panel should not be visible
    expect(screen.queryByText("CVSS Score:")).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(button);

    // Detail panel should now be visible
    // The expanded detail is shown after a click on the CVE row
    expect(screen.getAllByText(/CVE-2024-1234/).length).toBeGreaterThan(0);

    // Need to click the CVE row to expand details
    const cveRow = screen.getByText(/CVE-2024-1234/).closest('div');
    if (cveRow) {
      fireEvent.click(cveRow);
    }

    // Now detail should be visible
    expect(screen.getByText("CVSS Score:")).toBeInTheDocument();
    expect(screen.getByText("9.5")).toBeInTheDocument();
  });

  it("test_nvd_link_opens_external", () => {
    render(
      <CVEBadge
        cve_count={1}
        worst_severity="CRITICAL"
        cves={[mockCriticalCVE]}
        ingredient_name="test"
      />
    );

    // Expand the badge to show details
    const button = screen.getByRole("button");
    fireEvent.click(button);

    // Find NVD link
    const nvdLink = screen.getByRole("link", { name: /CVE-2024-1234/ });
    expect(nvdLink).toHaveAttribute(
      "href",
      "https://nvd.nist.gov/vuln/detail/CVE-2024-1234"
    );
    expect(nvdLink).toHaveAttribute("target", "_blank");
    expect(nvdLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("test_clean_badge_shows_checkmark", () => {
    render(
      <CVEBadge
        cve_count={0}
        worst_severity={null}
        cves={[]}
        ingredient_name="test"
      />
    );

    expect(screen.getByText("✅")).toBeInTheDocument();
    expect(screen.getByText("Clean")).toBeInTheDocument();
  });
});
