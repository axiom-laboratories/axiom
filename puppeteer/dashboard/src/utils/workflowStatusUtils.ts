/**
 * Workflow Status Utilities
 *
 * Provides consistent status-to-color and status-to-variant mappings
 * for workflow runs and workflow step runs. Matches the pattern used
 * in Jobs and History views for UI consistency.
 */

/**
 * Maps workflow/step status to UI badge variant.
 * Used with shadcn Badge component: <Badge variant={getStatusVariant(status)}>
 *
 * @param status - The workflow or step status string
 * @returns Badge variant: 'default' | 'destructive' | 'outline' | 'secondary'
 */
export function getStatusVariant(
  status: string | undefined
): 'default' | 'destructive' | 'outline' | 'secondary' {
  if (!status) return 'outline';

  switch (status.toUpperCase()) {
    // Workflow run statuses
    case 'RUNNING':
      return 'default';
    case 'COMPLETED':
      return 'secondary';
    case 'PARTIAL':
      return 'outline';
    case 'FAILED':
      return 'destructive';
    case 'CANCELLED':
      return 'outline';

    // Workflow step run statuses
    case 'PENDING':
      return 'outline';
    case 'SKIPPED':
      return 'outline';

    // Fallback
    default:
      return 'outline';
  }
}

/**
 * Maps workflow/step status to hex/RGB color code.
 * Used for node borders and fills in the DAG canvas.
 *
 * @param status - The workflow or step status string
 * @returns Hex color code for the status
 */
export function getStatusColor(status: string | undefined): string {
  if (!status) return '#888888';

  switch (status.toUpperCase()) {
    // Workflow run statuses
    case 'RUNNING':
      return '#3b82f6'; // Blue
    case 'COMPLETED':
      return '#10b981'; // Green
    case 'PARTIAL':
      return '#f59e0b'; // Amber
    case 'FAILED':
      return '#ef4444'; // Red
    case 'CANCELLED':
      return '#888888'; // Grey

    // Workflow step run statuses
    case 'PENDING':
      return '#888888'; // Grey
    case 'SKIPPED':
      return '#888888'; // Grey

    // Fallback
    default:
      return '#888888';
  }
}

/**
 * Status to color mapping constant.
 * Useful for reference and bulk lookups.
 */
export const statusColorMap: Record<string, string> = {
  // Workflow run statuses
  'RUNNING': '#3b82f6',
  'COMPLETED': '#10b981',
  'PARTIAL': '#f59e0b',
  'FAILED': '#ef4444',
  'CANCELLED': '#888888',

  // Workflow step run statuses
  'PENDING': '#888888',
  'SKIPPED': '#888888',
};

/**
 * Status to variant mapping constant.
 * Useful for reference and bulk lookups.
 */
export const statusVariantMap: Record<string, 'default' | 'destructive' | 'outline' | 'secondary'> = {
  // Workflow run statuses
  'RUNNING': 'default',
  'COMPLETED': 'secondary',
  'PARTIAL': 'outline',
  'FAILED': 'destructive',
  'CANCELLED': 'outline',

  // Workflow step run statuses
  'PENDING': 'outline',
  'SKIPPED': 'outline',
};
