# RBAC Hardening

This guide covers least-privilege configuration patterns, service principal hygiene, and how to audit access in Master of Puppets.

For the permission reference table and how to configure roles in the dashboard, see the [RBAC guide](../feature-guides/rbac.md) and [RBAC Permission Reference](../feature-guides/rbac-reference.md).

---

## Principle of Least Privilege

Assign the minimum role needed for each user's actual job function. The default roles are designed for this:

| User type | Recommended role | Rationale |
|-----------|-----------------|-----------|
| Monitoring-only operator | `viewer` | Read-only; cannot submit or modify anything |
| Day-to-day job operator | `operator` | Can manage jobs and nodes; cannot touch users or system config |
| Platform administrator | `admin` | Use only for setup and user provisioning; not for day-to-day work |
| CI/CD pipeline | Service principal (`operator`) | Machine identity; no login; expiry date enforced |

!!! warning
    Do not use the `admin` account for day-to-day operations. Admin bypasses all permission checks, which means admin actions provide no RBAC signal in the audit log — every admin action appears as "permitted" regardless of what it is. Use a named operator account for routine tasks.

---

## Service Principal Hygiene

Service principals are the recommended machine identity for all automation. They authenticate with a client secret (no login flow) and are tracked independently in the audit log using the `sp:<name>` username prefix.

Hardening checklist:

- [ ] Set an expiry date (`expires_at`) on every service principal — do not create non-expiring SPs
- [ ] Assign the `operator` role, never `admin`, unless admin-level access is genuinely required
- [ ] Use one service principal per automation context (one for CI, one for monitoring scripts, etc.) — avoid shared SPs
- [ ] Rotate secrets on a schedule (quarterly or after any potential leak) — use **Admin** → **Service Principals** → **Rotate Secret**
- [ ] Deactivate (`is_active = false`) rather than deleting a compromised SP — deletion removes the audit trail

!!! danger
    A service principal with the `admin` role has full unrestricted access. Treat its client secret with the same care as the admin password.

---

## Auditing Permissions

Review current role permissions regularly to catch permission creep — permissions that were granted temporarily and never revoked.

**Dashboard procedure:**

1. Navigate to **Admin** → **Role Permissions**
2. Review the current permission set for each non-admin role
3. Remove any permissions that are no longer required

**Via API (for automation):**

```bash
# List current permissions for the operator role
curl -H "Authorization: Bearer <TOKEN>" \
  https://<HOST>/admin/roles/operator/permissions

# Revoke a permission
curl -X DELETE \
  -H "Authorization: Bearer <TOKEN>" \
  https://<HOST>/admin/roles/operator/permissions/webhooks:write
```

Permission changes are logged as `permission:grant` and `permission:revoke` in the audit log. These events include the acting admin's username and the affected role.

---

## Reviewing the Audit Log for Access Patterns

The audit log records all permission changes and security-relevant events. For a periodic access review:

- Search for `permission:grant` events in the last 90 days — review any unexpected grants
- Search for admin actions (filter by `username = <admin username>`) — admin bypasses RBAC; any admin action should be intentional and deliberate
- Look for `sp:*` actions from service principals that have been deactivated — these indicate a stale identity may still hold an active secret

Cross-link: For query patterns and the complete event inventory, see [Audit Log](audit-log.md).

---

## Hardening the Default Configuration

The default operator and viewer role permissions are calibrated for most deployments. Consider these optional hardening steps for stricter environments:

**1. Restrict viewer permissions further**
Remove `signatures:read` from `viewer` if signature key visibility is sensitive in your environment:

```bash
curl -X DELETE \
  -H "Authorization: Bearer <TOKEN>" \
  https://<HOST>/admin/roles/viewer/permissions/signatures:read
```

**2. Remove `tokens:write` from `operator`**
If operators should not be able to approve device flow requests, remove this permission. This limits device flow approvals to admin accounts only.

**3. Guard `users:write` carefully**
Granting `users:write` to `operator` effectively gives all operators the ability to manage users, create service principals, and grant permissions — do this only if you have a flat team structure where all operators also manage access.

!!! warning
    `users:write` is the most powerful non-admin permission. It controls user creation, deletion, role assignment, service principal management, and permission grant/revoke. Treat any role holding this permission as near-equivalent to admin.

**4. Separate read and write access by environment**
In multi-environment deployments (staging and production), consider creating environment-specific service principals with read-only access to production and full access to staging. This limits blast radius if a CI credential is compromised.

---

## Quick Reference: Default Role Permissions

| Permission | admin | operator | viewer |
|-----------|-------|----------|--------|
| `jobs:read` | bypass | yes | yes |
| `jobs:write` | bypass | yes | no |
| `nodes:read` | bypass | yes | yes |
| `nodes:write` | bypass | yes | no |
| `definitions:read` | bypass | yes | yes |
| `definitions:write` | bypass | yes | no |
| `foundry:read` | bypass | yes | yes |
| `foundry:write` | bypass | yes | no |
| `signatures:read` | bypass | yes | yes |
| `signatures:write` | bypass | yes | no |
| `tokens:write` | bypass | yes | no |
| `alerts:read` | bypass | yes | yes |
| `alerts:write` | bypass | yes | no |
| `webhooks:read` | bypass | yes | no |
| `webhooks:write` | bypass | yes | no |
| `users:write` | bypass | no | no |

"bypass" means admin skips the permission check entirely — the permission is neither stored nor evaluated.
