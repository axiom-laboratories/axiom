# Role-Based Access Control

Master of Puppets uses three roles — `admin`, `operator`, and `viewer` — with a permission model that can be customised through the dashboard.

---

## Roles Overview

### admin

Full, unrestricted access. The admin role bypasses all permission checks — no database lookup occurs. Use the admin account only for initial setup, user provisioning, and emergency access. Day-to-day platform work should be done with an `operator` account.

### operator

The standard role for platform engineers. Operators can manage jobs, nodes, Foundry templates and blueprints, signing keys, and scheduled job definitions. They cannot manage users, roles, or system configuration.

### viewer

Read-only access across the platform. Viewers can inspect job results, node status, Foundry content, and signing keys, but cannot submit jobs or make changes.

For the complete permission matrix showing which permissions are assigned to each role by default, see the [RBAC Permission Reference](rbac-reference.md).

---

## Managing Users

The **Users** section of the dashboard lists all accounts and provides controls for creation, role assignment, and credential management. Only `admin` users can access this section.

### Creating a user

1. Navigate to **Users** in the sidebar
2. Click **Create User** and fill in username, email, and initial password
3. Select the role: `admin`, `operator`, or `viewer`
4. Click **Save** — the user can now log in immediately

### Changing a user's role

Click the role badge next to a username, select the new role from the dropdown, and confirm. The change takes effect immediately; any active sessions for that user continue with the new role on their next request.

### Force password change on next login

Toggle **Force Password Change** on the user row. The user is prompted to set a new password on their next login. Their existing sessions remain valid until that change is completed.

### Resetting a user's password

Click **Reset Password** on a user row. A new temporary password is generated and returned. This immediately increments the user's token version, invalidating all active sessions — the user must log in again with the new password.

### Deleting a user

Click **Delete** on the user row to permanently remove the account.

!!! warning
    Deleting a user is permanent and cannot be undone. Any API keys or signing keys associated with that user are also removed.

---

## Customising Role Permissions

Permissions can be granted or revoked on a per-role basis through **Admin** → **Role Permissions**. This allows you to tailor the operator and viewer roles to your team's access requirements without creating custom roles.

!!! warning
    Permission changes affect all users with that role immediately. Adding `users:write` to the `operator` role gives every operator the ability to manage users — use with care.

### Updating permissions

1. Navigate to **Admin** → **Role Permissions**
2. Select a role tab (**operator** or **viewer**)
3. Click a permission chip to grant it; click it again to revoke
4. Changes take effect immediately for all new requests

The `admin` role's permissions cannot be modified — admin always has full access regardless of the permissions table.

---

## Service Principals

Service principals are machine identities — they are not human users and do not use the standard login flow. They are designed for automation, CI/CD pipelines, and any non-interactive integration that needs to authenticate against the API.

A service principal has a `client_id` and a `client_secret`, and is assigned a role just like a user. Actions performed by a service principal are attributed in the audit log as `sp:<name>`, making it straightforward to trace automated actions separately from human activity.

### Creating a service principal

1. Navigate to **Admin** → **Service Principals**
2. Click **Create Service Principal**
3. Enter a name (e.g. `ci-pipeline`) and select a role
4. Optionally set an expiry date — the service principal's tokens will be rejected after this date
5. Click **Create**

!!! danger
    The `client_secret` is shown only once immediately after creation. Copy it to your secrets manager before closing the dialog. It cannot be retrieved again. If lost, use the **Rotate Secret** button to generate a new one — this invalidates the old secret immediately.

### Rotating a service principal secret

Click **Rotate Secret** on the service principal row. The new secret is shown once. The previous secret is invalid from the moment rotation completes.

### Deactivating a service principal

Toggle **Active** to false on the service principal row. All tokens issued to that SP are rejected immediately. The service principal record is preserved — reactivating it does not require regenerating credentials.

To get a JWT for a service principal and use it in CI/CD pipelines, see the [OAuth & Authentication guide](oauth.md).

---

## API Keys

API keys are long-lived credentials tied to a specific user account, managed in **My Account**. They always begin with `mop_` and can be used in automation in place of short-lived JWT tokens. Unlike JWT tokens, API keys do not expire unless explicitly revoked.

See the [OAuth & Authentication guide](oauth.md) for usage patterns, including how to use API keys in scripts and how to scope them for read-only access.
