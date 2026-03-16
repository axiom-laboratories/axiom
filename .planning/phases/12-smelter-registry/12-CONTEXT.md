# Phase 12: Smelter Registry

## Goal
Establish a vetted ingredient catalog for Puppet images to ensure security and compliance. Admins can maintain a list of approved packages (PIPs, system binaries), and the system will automatically flag those with known CVEs. The Foundry will enforce this catalog by either blocking builds (STRICT) or badging images as Non-Compliant (WARNING).

## Context
Phase 11 established the "Compatibility Engine," tagging tools with OS families. Phase 12 extends this by adding a governance layer over the actual *packages* (ingredients) used to build those tools and runtimes.

The "Smelter" name refers to the vetted nature of the ingredients — only pure, approved materials should go into the final Puppet images.

## Requirements
- **SMLT-01**: Admin can add packages to a vetted ingredient catalog (name, version constraint, sha256, OS family).
- **SMLT-02**: System auto-flags catalog entries with known CVEs via `pip-audit`/`Safety` integration.
- **SMLT-03**: Build fails (STRICT mode) if any blueprint ingredient is not in the approved catalog.
- **SMLT-04**: Admin can toggle enforcement mode between STRICT and WARNING per system config.
- **SMLT-05**: Dashboard shows Non-Compliant badge on images built with unapproved ingredients in WARNING mode.

## Key Components

### 1. Database Schema
- `approved_ingredients` table:
    - `id`: UUID (Primary Key)
    - `name`: String (e.g., "cryptography")
    - `version_constraint`: String (e.g., ">=42.0.0")
    - `sha256`: String (Nullable, for strict integrity)
    - `os_family`: Enum (DEBIAN, ALPINE, etc.)
    - `is_vulnerable`: Boolean (Default: False)
    - `vulnerability_report`: JSON (Nullable)
    - `created_at`: DateTime
    - `updated_at`: DateTime

### 2. Backend Logic (FastAPI)
- `SmelterService`:
    - `add_ingredient()`: Validation and insertion.
    - `scan_ingredients()`: Integration with `pip-audit`.
    - `validate_blueprint()`: Checks blueprint ingredients against the registry.
- `FoundryService` updates:
    - Inject registry check before triggering Docker build.
    - Track "Compliance Status" on the resulting `Template` image.

### 3. Frontend (React)
- **Smelter Catalog View**: A new admin page to manage approved ingredients.
- **System Config**: Toggle for STRICT vs WARNING mode.
- **Template Badges**: Update `Templates.tsx` to show "Non-Compliant" (Red/Amber) for images that bypassed the registry.

## Success Criteria
1. Admin can add a vetted package through the UI/API.
2. A build containing an unapproved package is rejected in STRICT mode.
3. A build containing an unapproved package is marked "Non-Compliant" in WARNING mode.
4. Security scanner identifies and flags a vulnerable package in the catalog.
