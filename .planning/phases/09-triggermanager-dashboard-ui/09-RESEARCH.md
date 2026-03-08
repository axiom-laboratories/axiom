# Phase 9: TriggerManager Dashboard UI - Research

**Researched:** 2026-03-08
**Domain:** React/TypeScript frontend component fix + FastAPI backend extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Active/inactive toggle**
- Add an inline toggle to each table row: green "Active" / grey "Inactive" badge + a toggle button in the Actions column
- Requires adding `PATCH /api/admin/triggers/{id}` backend endpoint to update `is_active`
- Toggling a trigger **inactive** shows a confirmation dialog before sending the PATCH: "Disabling this trigger will prevent new jobs from being fired. Continue?"
- No side effects beyond flipping `is_active` — in-flight jobs complete normally

**Secret token management**
- Add a **Copy Token** button in each row (alongside the existing Copy Curl button)
- Add a **Rotate Key** button in the Actions column that opens a confirmation dialog: "This will invalidate the current token. Existing integrations will break until updated."
- After regeneration, display the new token in a **one-time reveal modal** with a Copy button and a warning: "This is the only time you'll see this token." (mirrors the Service Principal key reveal pattern)
- Requires a backend endpoint: `POST /api/admin/triggers/{id}/regenerate-token` (or equivalent PATCH field)

**Empty state**
- When no triggers exist, replace the empty table body with a centered message inside the table: "No triggers yet."
- Include a one-line description: "Triggers are secure webhooks that let external systems (GitHub Actions, scripts) fire jobs."
- Include a "+ Create Trigger" button that opens the create dialog
- The Create Trigger button in the card header remains as well

**Compile fixes**
- Add missing imports: `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter` from `@/components/ui/dialog`
- Add missing import: `Label` from `@/components/ui/label`

### Claude's Discretion
- Exact icon choice for Rotate Key button
- Styling details for confirmation dialogs (reuse existing modal styling pattern from the file)
- Whether regenerate-token is a separate POST endpoint or a field on the PATCH endpoint
- RBAC: use existing `admin` permission gate (same as create/delete triggers)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 9 is a focused repair-and-extend phase on a single component: `TriggerManager` inside `Admin.tsx`. The component was written but never made runnable — it uses `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter`, and `Label` without importing them, causing a compile error that prevents the entire Admin page from loading.

Beyond the compile fix, three features must be added: (1) an Active/Inactive toggle column with a disable-confirmation dialog, (2) a Copy Token button and a Rotate Key flow that ends in a one-time reveal modal, and (3) an empty-state treatment when the triggers list is empty. All three require complementary backend work: a `PATCH /api/admin/triggers/{id}` endpoint and a `POST /api/admin/triggers/{id}/regenerate-token` endpoint.

All patterns needed already exist in the codebase. `ServicePrincipals.tsx` provides the exact one-time credential reveal modal (using `Dialog` + `AlertDialog` + `AlertTriangle` warning banner), the rotate-confirmation `AlertDialog`, and the active/inactive Badge rendering pattern. The backend service (`trigger_service.py`) already has `list_triggers`, `create_trigger`, and `delete_trigger` — `update_trigger` and `regenerate_token` methods must be added.

**Primary recommendation:** Fix imports first (unblocks compile), then add backend endpoints, then layer in the three UI features, each as a discrete task. Do not attempt to do all work in one task.

---

## Standard Stack

### Core (already in project — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React + TypeScript | 18.x | Component framework | Project standard |
| `@tanstack/react-query` | 5.x | Server state, mutations, cache invalidation | Already used in TriggerManager |
| `sonner` | current | Toast notifications | Already used in TriggerManager |
| `lucide-react` | current | Icons | Already imported in Admin.tsx |
| `@/components/ui/dialog` | shadcn/ui | Modal dialogs | Already in `puppeteer/dashboard/src/components/ui/dialog.tsx` |
| `@/components/ui/alert-dialog` | shadcn/ui | Confirmation dialogs | Already in `puppeteer/dashboard/src/components/ui/alert-dialog.tsx` |
| `@/components/ui/label` | shadcn/ui | Form labels | Already in `puppeteer/dashboard/src/components/ui/label.tsx` |

### No new dependencies required

All required UI components are already present in the project's `src/components/ui/` directory. No `npm install` needed.

---

## Architecture Patterns

### Recommended File Touch Points

```
puppeteer/
├── agent_service/
│   ├── models.py                  # Add TriggerUpdate model
│   ├── services/trigger_service.py # Add update_trigger() + regenerate_token()
│   └── main.py                    # Add PATCH + POST regenerate-token routes (~line 2360)
└── dashboard/src/views/
    └── Admin.tsx                  # Fix imports, extend TriggerManager component
```

### Pattern 1: Import Fix (compile blocker)

The current `TriggerManager` (lines 54-213 of Admin.tsx) uses `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter`, and `Label` without importing them. The imports must be added to the top of Admin.tsx alongside existing imports.

```typescript
// Add to Admin.tsx imports
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
```

Both components exist at:
- `/home/thomas/Development/master_of_puppets/puppeteer/dashboard/src/components/ui/dialog.tsx`
- `/home/thomas/Development/master_of_puppets/puppeteer/dashboard/src/components/ui/label.tsx`

### Pattern 2: Active/Inactive Toggle — Inline Badge + Disable Confirmation

**State needed in TriggerManager:**
```typescript
const [isDisableConfirmOpen, setIsDisableConfirmOpen] = useState(false);
const [pendingToggleTrigger, setPendingToggleTrigger] = useState<any>(null);
```

**PATCH mutation:**
```typescript
const toggleMutation = useMutation({
    mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }) => {
        const res = await authenticatedFetch(`/api/admin/triggers/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active })
        });
        return res.json();
    },
    onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['automation-triggers'] });
        toast.success('Trigger updated');
    }
});
```

**Row badge rendering** (mirrors ServicePrincipals.tsx lines 344-353):
```typescript
// In table row — new Status column
<TableCell>
    {t.is_active ? (
        <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">Active</Badge>
    ) : (
        <Badge className="bg-zinc-500/10 text-zinc-400 border-zinc-500/20">Inactive</Badge>
    )}
</TableCell>
```

**Toggle button in Actions column:** When `t.is_active` is true, clicking the toggle button should set `pendingToggleTrigger` and open the disable confirmation dialog. When `t.is_active` is false, clicking directly calls `toggleMutation.mutate({ id: t.id, is_active: true })` (re-enabling needs no confirmation).

**Confirmation dialog** uses `AlertDialog` (already available, used in ServicePrincipals.tsx lines 626-644):
```typescript
<AlertDialog open={isDisableConfirmOpen} onOpenChange={setIsDisableConfirmOpen}>
    <AlertDialogContent className="bg-zinc-925 border-zinc-800 text-white">
        <AlertDialogHeader>
            <AlertDialogTitle>Disable this trigger?</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">
                Disabling this trigger will prevent new jobs from being fired. Continue?
            </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
            <AlertDialogCancel className="bg-zinc-800 border-zinc-700 text-white hover:bg-zinc-700">Cancel</AlertDialogCancel>
            <AlertDialogAction
                onClick={() => toggleMutation.mutate({ id: pendingToggleTrigger.id, is_active: false })}
                className="bg-amber-600 hover:bg-amber-700 text-white"
            >
                Disable Trigger
            </AlertDialogAction>
        </AlertDialogFooter>
    </AlertDialogContent>
</AlertDialog>
```

### Pattern 3: Copy Token Button

Add alongside the existing Copy Curl button in the Actions cell:
```typescript
<Button variant="ghost" size="sm" className="text-zinc-500 hover:text-white gap-2"
    onClick={() => { navigator.clipboard.writeText(t.secret_token); toast.success('Token copied'); }}>
    <Key className="h-3 w-3" /> Copy Token
</Button>
```

`Key` is already imported from `lucide-react` (line 6 of Admin.tsx).

### Pattern 4: Rotate Key + One-Time Reveal Modal

This mirrors the ServicePrincipals pattern exactly (lines 167-181 and 483-544 of ServicePrincipals.tsx).

**State:**
```typescript
const [isRotateConfirmOpen, setIsRotateConfirmOpen] = useState(false);
const [isTokenRevealOpen, setIsTokenRevealOpen] = useState(false);
const [newToken, setNewToken] = useState<string | null>(null);
const [pendingRotateTrigger, setPendingRotateTrigger] = useState<any>(null);
```

**Rotate mutation (calls POST /api/admin/triggers/{id}/regenerate-token):**
```typescript
const rotateMutation = useMutation({
    mutationFn: async (id: string) => {
        const res = await authenticatedFetch(`/api/admin/triggers/${id}/regenerate-token`, {
            method: 'POST'
        });
        return res.json(); // returns { secret_token: "trg_..." }
    },
    onSuccess: (data) => {
        queryClient.invalidateQueries({ queryKey: ['automation-triggers'] });
        setNewToken(data.secret_token);
        setIsRotateConfirmOpen(false);
        setIsTokenRevealOpen(true);
        toast.success('Token regenerated');
    }
});
```

**Rotate confirmation** (AlertDialog, amber-coloured like SP rotate):
```typescript
<AlertDialog open={isRotateConfirmOpen} onOpenChange={setIsRotateConfirmOpen}>
    <AlertDialogContent className="bg-zinc-925 border-zinc-800 text-white">
        <AlertDialogHeader>
            <AlertDialogTitle>Rotate trigger token?</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">
                This will invalidate the current token. Existing integrations will break until updated.
            </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
            <AlertDialogCancel className="bg-zinc-800 border-zinc-700 text-white hover:bg-zinc-700">Cancel</AlertDialogCancel>
            <AlertDialogAction
                onClick={() => pendingRotateTrigger && rotateMutation.mutate(pendingRotateTrigger.id)}
                className="bg-amber-600 hover:bg-amber-700 text-white"
            >
                Rotate Token
            </AlertDialogAction>
        </AlertDialogFooter>
    </AlertDialogContent>
</AlertDialog>
```

**One-time reveal modal** (Dialog, mirrors SP credentials modal lines 483-544):
```typescript
<Dialog open={isTokenRevealOpen} onOpenChange={setIsTokenRevealOpen}>
    <DialogContent className="bg-zinc-925 border-zinc-800 text-white max-w-lg">
        <DialogHeader>
            <div className="flex items-center gap-2 text-emerald-500 mb-2">
                <CheckCircle2 className="h-6 w-6" />
                <DialogTitle>New Token Generated</DialogTitle>
            </div>
            <DialogDescription className="text-zinc-400">
                This is the only time you'll see this token. Copy it now.
            </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
            <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
                <p className="text-xs text-amber-200/80">
                    Store this token securely. Loss requires another rotation.
                </p>
            </div>
            <div className="space-y-2">
                <Label className="text-zinc-400">Secret Token</Label>
                <div className="flex gap-2">
                    <Input readOnly value={newToken || ''} className="bg-zinc-950 border-zinc-800 font-mono text-xs" />
                    <Button size="icon" variant="outline"
                        onClick={() => { navigator.clipboard.writeText(newToken || ''); toast.success('Token copied'); }}>
                        <Copy className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
        <DialogFooter>
            <Button className="w-full bg-zinc-100 hover:bg-white text-zinc-950 font-bold"
                onClick={() => setIsTokenRevealOpen(false)}>
                I have saved the token
            </Button>
        </DialogFooter>
    </DialogContent>
</Dialog>
```

`AlertTriangle` must be imported from `lucide-react` (not currently imported in Admin.tsx — must be added).
`CheckCircle2` is already imported (line 11 of Admin.tsx).

### Pattern 5: Empty State

Replace the current bare `{triggers.map(...)}` inside `<TableBody>` with a conditional:

```typescript
<TableBody>
    {triggers.length === 0 ? (
        <TableRow>
            <TableCell colSpan={5} className="py-16 text-center">
                <div className="flex flex-col items-center gap-3">
                    <Zap className="h-8 w-8 text-zinc-700" />
                    <p className="text-white font-medium">No triggers yet.</p>
                    <p className="text-zinc-500 text-sm max-w-xs">
                        Triggers are secure webhooks that let external systems (GitHub Actions, scripts) fire jobs.
                    </p>
                    <Button size="sm" className="mt-2 bg-primary hover:bg-primary/90 text-white font-bold"
                        onClick={() => setIsCreateOpen(true)}>
                        <Plus className="mr-2 h-4 w-4" /> Create Trigger
                    </Button>
                </div>
            </TableCell>
        </TableRow>
    ) : (
        triggers.map((t: any) => ( /* existing row JSX */ ))
    )}
</TableBody>
```

The `colSpan` value must match the updated column count (currently 4 columns: Name, Slug, Target Job, Actions; adding Status column = 5 total).

### Pattern 6: Backend — TriggerUpdate Model

Add to `puppeteer/agent_service/models.py`:

```python
class TriggerUpdate(BaseModel):
    is_active: Optional[bool] = None
    name: Optional[str] = None
```

### Pattern 7: Backend — TriggerService Methods

Add to `puppeteer/agent_service/services/trigger_service.py`:

```python
@staticmethod
async def update_trigger(trigger_id: str, is_active: Optional[bool], db: AsyncSession) -> Trigger:
    result = await db.execute(select(Trigger).where(Trigger.id == trigger_id))
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    if is_active is not None:
        trigger.is_active = is_active
    await db.commit()
    await db.refresh(trigger)
    return trigger

@staticmethod
async def regenerate_token(trigger_id: str, db: AsyncSession) -> Trigger:
    result = await db.execute(select(Trigger).where(Trigger.id == trigger_id))
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    trigger.secret_token = "trg_" + secrets.token_hex(24)
    await db.commit()
    await db.refresh(trigger)
    return trigger
```

### Pattern 8: Backend — New Routes in main.py

Add after line ~2360 (after the existing DELETE route):

```python
@app.patch("/api/admin/triggers/{id}", response_model=TriggerResponse, tags=["Headless Automation"])
async def update_automation_trigger(
    id: str,
    req: TriggerUpdate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Toggle is_active or update name on an automation trigger."""
    return await trigger_service.update_trigger(id, req.is_active, db)

@app.post("/api/admin/triggers/{id}/regenerate-token", response_model=TriggerResponse, tags=["Headless Automation"])
async def regenerate_trigger_token(
    id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Rotate the secret token for an automation trigger."""
    return await trigger_service.regenerate_token(id, db)
```

`TriggerUpdate` must also be added to the import list in `main.py`.

### Anti-Patterns to Avoid

- **Don't add `AlertDialog` imports to Admin.tsx without checking** — `AlertDialog` and its sub-components must be explicitly imported from `@/components/ui/alert-dialog`. They are not auto-exported.
- **Don't re-enable triggers without any confirmation** — re-enabling is safe, only disable needs confirmation per the locked decisions.
- **Don't forget to update `colSpan`** — when a Status column is added to the table, the empty-state `colSpan` must reflect the new column count.
- **Don't use a separate route file** — all trigger endpoints live inline in `main.py`, following the existing pattern.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Confirmation dialog | Custom modal component | `AlertDialog` from `@/components/ui/alert-dialog` | Already in project, consistent with SP pattern |
| One-time reveal | Custom overlay | `Dialog` + `AlertTriangle` banner (SP pattern) | Exact pattern already in ServicePrincipals.tsx lines 483-544 |
| Toast notifications | Custom notification | `toast` from `sonner` | Already imported and used in TriggerManager |
| Secure token generation | Custom random | `secrets.token_hex(24)` (Python stdlib) | Already used in `create_trigger()` |

---

## Common Pitfalls

### Pitfall 1: Missing AlertDialog import in Admin.tsx
**What goes wrong:** `AlertDialog` is used by ServicePrincipals.tsx but is NOT currently imported in Admin.tsx. Adding it to TriggerManager without adding the import will cause the same compile error being fixed.
**How to avoid:** Add `AlertDialog`, `AlertDialogContent`, `AlertDialogHeader`, `AlertDialogTitle`, `AlertDialogDescription`, `AlertDialogFooter`, `AlertDialogCancel`, `AlertDialogAction` from `@/components/ui/alert-dialog` to Admin.tsx imports.
**Warning sign:** TypeScript reports `AlertDialog is not defined`.

### Pitfall 2: TriggerUpdate not imported in main.py
**What goes wrong:** The new PATCH route uses `TriggerUpdate` but the existing import in main.py only lists `TriggerCreate, TriggerResponse`. The app will crash at startup.
**How to avoid:** Add `TriggerUpdate` to the models import line in main.py.
**Warning sign:** `ImportError: cannot import name 'TriggerUpdate'` at server startup.

### Pitfall 3: Column count mismatch in empty state colSpan
**What goes wrong:** Current table has 4 columns. Adding a Status column makes 5. If `colSpan={4}` is used in the empty state, it won't span the full width and will look broken.
**How to avoid:** Count columns after modifications and set `colSpan` to match.

### Pitfall 4: Rotate mutation invalidates cache before token is captured
**What goes wrong:** If `queryClient.invalidateQueries` runs before the new token is extracted from the response, the reveal modal shows `null`.
**How to avoid:** Set `newToken` state from the mutation response `onSuccess` callback before `setIsTokenRevealOpen(true)` — this is the same order used in ServicePrincipals.tsx lines 175-180.

### Pitfall 5: `is_active` field missing from existing TriggerResponse
**What goes wrong:** The field `is_active` IS present in `TriggerResponse` (confirmed in models.py line 86) and in the `Trigger` DB model (db.py line 265). The backend is ready — no DB migration needed.
**Why it's still a pitfall:** Planners may assume a migration is needed. Confirm: `is_active` column already exists in the `triggers` table from initial `create_all`.

---

## Code Examples

### Current TriggerManager State (what's broken)

Lines 160-210 of Admin.tsx use `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter`, and `Label` with zero imports for them. The component renders a working table and create-dialog structure — all the layout is correct, just the imports are absent.

### Existing copyCurl helper (lines 102-110 of Admin.tsx)

```typescript
const copyCurl = (trigger: any) => {
    const baseUrl = window.location.origin;
    const curl = `curl -X POST "${baseUrl}/api/trigger/${trigger.slug}" \\
  -H "X-MOP-Trigger-Key: ${trigger.secret_token}" \\
  -H "Content-Type: application/json" \\
  -d '{"ref": "main", "actor": "github-actions"}'`;
    navigator.clipboard.writeText(curl);
    toast.success('Curl command copied to clipboard');
};
```

The Copy Token button can reuse the same clipboard + toast pattern without a helper function.

### TriggerService.create_trigger token format (trigger_service.py line 83)

```python
token = "trg_" + secrets.token_hex(24)
```

`regenerate_token` should use identical format for consistency.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Inline token in table row only | Copy Token button + one-time reveal on rotate | Security hygiene: token not re-shown after rotation |
| No empty state | Descriptive empty state with CTA | UX: users understand the feature purpose on first visit |
| Active column present in DB but not surfaced in UI | Badge + toggle button | Feature completeness: `is_active` was wired in backend but invisible |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `puppeteer/pytest.ini` (if exists) / vitest via `puppeteer/dashboard/vite.config.ts` |
| Quick run command (backend) | `cd puppeteer && pytest tests/test_tools.py -x` |
| Quick run command (frontend) | `cd puppeteer/dashboard && npm run test` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npm run test` |

### Phase Requirements → Test Map

This phase has no formal REQUIREMENTS.md IDs. Validation maps to behaviours:

| Behaviour | Test Type | Automated Command | File Exists? |
|-----------|-----------|-------------------|-------------|
| Admin.tsx compiles without error | build smoke | `cd puppeteer/dashboard && npm run build` | N/A (build step) |
| PATCH `/api/admin/triggers/{id}` flips `is_active` | integration | `cd puppeteer && pytest tests/test_tools.py -k trigger -x` | Wave 0 gap |
| POST `/api/admin/triggers/{id}/regenerate-token` returns new token | integration | `cd puppeteer && pytest tests/test_tools.py -k trigger -x` | Wave 0 gap |
| TriggerManager renders empty state when list is empty | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Admin.test.tsx` | Wave 0 gap |

### Sampling Rate

- **Per task commit:** `cd puppeteer/dashboard && npm run build` (verifies compile)
- **Per wave merge:** Full pytest + vitest suite
- **Phase gate:** Build clean + backend API tests pass before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `puppeteer/tests/test_tools.py` — add trigger PATCH and regenerate-token test cases (or new `tests/test_triggers.py`)
- [ ] `puppeteer/dashboard/src/views/__tests__/Admin.test.tsx` — smoke render test for TriggerManager empty state

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `/home/thomas/Development/master_of_puppets/puppeteer/dashboard/src/views/Admin.tsx` — confirmed missing imports, existing table structure, state management patterns
- Direct code inspection of `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/trigger_service.py` — confirmed existing methods, token format, DB session pattern
- Direct code inspection of `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/db.py` — confirmed `Trigger` model has `is_active`, `secret_token`, all fields present; no migration needed
- Direct code inspection of `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/models.py` — confirmed `TriggerResponse` includes `is_active`; `TriggerUpdate` does not yet exist
- Direct code inspection of `/home/thomas/Development/master_of_puppets/puppeteer/dashboard/src/views/ServicePrincipals.tsx` — confirmed one-time reveal modal pattern, AlertDialog rotate confirmation pattern, active/inactive badge rendering

### Secondary (MEDIUM confidence)
- UI component availability confirmed by directory listing of `puppeteer/dashboard/src/components/ui/` — `dialog.tsx`, `alert-dialog.tsx`, `label.tsx` all present

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use
- Architecture: HIGH — all patterns directly copied from existing codebase
- Pitfalls: HIGH — identified by direct code inspection, not inference
- Backend changes: HIGH — trivial extension of existing service pattern

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable codebase, no third-party version concerns)
