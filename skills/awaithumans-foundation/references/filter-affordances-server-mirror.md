<!-- capsule-v2 -->
# Filter Affordances Server Mirror — UI toggles that encode the server's filter algebra so contradictory queries are never sent

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** Where should "these two filters together return nothing" be enforced — server, client, or both?

## Connected graph-selected seam
**Path/Symbol:** `packages/dashboard/components/filters/task-filter-bar.tsx` — `TaskFilterBar` (:46-190), `TogglePill` (:192-216), `FilterChip` (:218-238); server twins in `task_service.list_tasks` (:210-212 if-arm precedence) and `routes/tasks.py` non-operator scoping (:270-285 region).
**Signature:** `TaskFilterBarProps { filters; onChange(patch); isOperator; statusOptions; showUnassignedToggle?; searchPlaceholder? }`.
**Data Shape:** shared `FilterState { status; assignedTo; unassigned; mine }` consumed by both `/` (queue) and `/audit` pages.

### Decisive source
Mutual exclusion ON TURN-ON ONLY (:96-101, mirrored :109-113):
```tsx
<TogglePill
    active={filters.unassigned}
    onClick={() =>
        onChange({
            unassigned: !filters.unassigned,
            // Mutually exclusive with Mine.
            mine: !filters.unassigned ? false : filters.mine,
        })
    }
    label="Unassigned"
/>
```
Empty-intersection encoded as disabled input (:79):
```tsx
value={filters.assignedTo}
disabled={filters.unassigned || filters.mine}
```
Operator gating mirroring the route's forced scoping (:106):
```tsx
{isOperator && (
    <TogglePill active={filters.mine} ... label="Mine only" />
)}
```
Context-hidden toggle (:37-42 prop docstring): "Hide the 'Unassigned only' toggle on contexts where it doesn't make sense (e.g. audit page — terminal tasks are past assignment, the toggle would always return zero)."

**Flow:** turning Unassigned ON clears Mine (and vice-versa); DEACTIVATING either preserves its sibling (the ternary's false-arm passes the current value through). Search input disables while unassigned||mine because `unassigned AND assignee-filter` is guaranteed-empty SERVER-side too (list_tasks puts unassigned in the if-arm where it structurally wins). The server remains the authority — any contradictory URL typed by hand resolves to [] via list_tasks precedence; the client just prevents most of them from ever being built. Defense in depth across the wire boundary.
**Invariant:** affordances mirror server semantics 1:1 — operator-only Mine ↔ route strips/filters params for non-operators; hidden audit toggle ↔ terminal+unassigned ≡ ∅; disabled search ↔ empty AND-intersection. A shared component with per-context props (statusOptions/showUnassignedToggle/isOperator) keeps two pages from drifting (pre-#73 they were copy-pasted ~80 lines and already had).

**Probe:** server twins read directly — `tests/tasks/test_route_authorization.py::test_list_unassigned_ignored_for_non_operator` (:363-381, reviewer passing ?unassigned=true still sees only their own tasks) and `::test_list_assigned_to_filter_ignored_for_non_operator` (:208-220). No vitest runner exists for the component itself (node_modules absent — recorded caveat; deterministic line-checks used).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "filters from search params allowlist status page size offset update filters", limit: 10 });
```
Live at pin: TogglePill −25.56 (:192-216), clearAll −25.56 (:60-66), TaskFilterBar −25.4 (:46-190), TaskFilterBarProps −20.24 (:32-44), StatusOption −25.07 — the whole component family retrievable through the same URL-state vocabulary.

## Verdict
Adopt affordances-as-mirror: when two filters are semantically exclusive or role-gated server-side, encode that in the controls (mutual exclusion on turn-on, disable-on-empty-intersection, role gating, context hiding) AND keep the server guard as authority. Adapt pairs to your domain. Omit the client half only if you accept users constructing dead URLs that your API must then answer with empty sets.
