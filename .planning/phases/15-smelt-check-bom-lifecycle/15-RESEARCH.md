# Phase 15 Research: Smelt-Check, BOM & Lifecycle

## Standard Stack
- **Container Orchestration**: Docker CLI (via `asyncio.create_subprocess_exec`)
    - *Rationale*: Consistency with existing `FoundryService` build/push logic. Avoids new heavy dependencies like the Docker SDK for simple ephemeral runs.
- **BOM Generation**: `pip list --json` and `dpkg-query`
    - *Rationale*: Built-in tools that provide accurate runtime snapshots of the baked image.
- **BOM Search**: Normalized SQL Index (`package_index` table)
    - *Rationale*: Allows high-performance queries like "which images have package X" without parsing JSON in every row.
- **Compliance Export**: SPDX 2.3 JSON
    - *Rationale*: Industry standard for SBOM exchange.

## Architecture Patterns
- **Ephemeral Validation (Smelt-Check)**:
    - Step 1: `docker run --rm --name staging-<id> --memory=512m --cpus=0.5 <image_uri> <validation_cmd>`
    - Step 2: Capture exit code. 0 = Success, Else = Failure.
    - Step 3: Stream logs to a temporary buffer for dashboard reporting.
- **Runtime BOM Capture**:
    - During the Smelt-Check, run secondary commands to extract package lists.
    - Store the raw output in `image_bom` and parse/expand into `package_index`.
- **Lifecycle Enforcement**:
    - **Enrollment Middleware**: Check node's current image status. If `REVOKED`, return 403.
    - **Scheduler Filter**: When selecting a job for a node, ensure the target image is not `REVOKED`.

## Don't Hand-Roll
- **BOM Standards**: Use the identified minimal SPDX 2.3 schema. Do not invent a custom export format.
- **Resource Limiting**: Use Docker's native `--memory` and `--cpus` flags. Do not implement custom monitoring/killing logic.

## Common Pitfalls
- **Zombie Staging Containers**: If the `agent` service crashes during Smelt-Check, the staging container might keep running. *Fix*: Use unique names and implement a cleanup task at service startup to prune `staging-*` containers.
- **Transitive Bloat**: `package_index` can grow very large. *Fix*: Implement periodic pruning of index entries for images that have been deleted from the registry.
- **mTLS in Staging**: Staging nodes might need a mock client cert to pass connectivity tests. *Fix*: Smelter will provide a "Staging Identity" cert during the validation run.

## Code Examples

### 1. Ephemeral Staging Run
```python
cmd = [
    "docker", "run", "--rm", 
    "--memory", "512m", 
    "--cpus", "0.5",
    image_uri, 
    validation_cmd
]
proc = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
stdout, stderr = await proc.communicate()
is_success = proc.returncode == 0
```

### 2. Normalized Package Index Schema
```sql
CREATE TABLE package_index (
    id UUID PRIMARY KEY,
    image_id UUID REFERENCES puppet_templates(id),
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    source TEXT NOT NULL -- 'pip' or 'apt'
);
CREATE INDEX idx_pkg_name ON package_index(name);
```

## RESEARCH COMPLETE
Confidence Level: High (DinD patterns and SPDX schema verified).
Next Step: /gsd:plan-phase 15
