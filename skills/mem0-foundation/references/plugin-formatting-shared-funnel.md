<!-- capsule-v2 -->
# Shared timeline formatting funnel — what does a display helper need so every hook timeline renders identically and never crashes?

**Source:** mem0 Apache-2.0 `main@7e096155714c`. **Question:** when three different hooks render memory timelines, what belongs in the shared module and what is the failure contract for display-only code?

## TYPE_ICONS + format_age (._formatting.py)
**Path/Symbol:** `integrations/mem0-plugin/scripts/_formatting.py:TYPE_ICONS` (lines 12–26) + `format_age` (29–51); imported by `file_context.py` and `session_timeline.py`.
**Signature:** `format_age(memory: dict) -> str`; `TYPE_ICONS: dict[str, str]` (13 categories: decision, anti_pattern, bug_fix, convention, task_learning, user_preference, session_summary, session_state, project_profile, compact_summary, auto_capture, environmental, health_check).
**Data Shape:** input memory carries ISO-8601 `created_at` (optionally `Z`-suffixed); output buckets `"{n}m ago"` (<1h), `"{n}h ago"` (<24h), `"1d ago"` (exact), `"{n}d ago"` (<30d), `"{n}mo ago"` (30-day months).

### Decisive source
```python
    try:
        from datetime import datetime, timezone
        if created.endswith("Z"):
            created = created[:-1] + "+00:00"
        dt = datetime.fromisoformat(created)
        now = datetime.now(timezone.utc)
        delta = now - dt
        seconds = int(delta.total_seconds())
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        ...
    except Exception:
        return ""
```
**Flow:** either timeline hook iterates memories → `cat = meta.get("type", "unknown")` → `icon = TYPE_ICONS.get(cat, "❓")` (unknown categories get a fallback icon, never a KeyError) → `age = format_age(m)` → `age_str = f" ({age})" if age else ""` (empty age renders as nothing, not "()"). The same funnel guarantees both hooks' lines differ only in text length (150 vs 120 chars) and header.
**Invariant:** display helpers must be total functions — every malformed input (`created_at` missing, non-ISO, naive datetime mixed with aware) collapses to `""` via the blanket except, and unknown categories collapse to the `❓` fallback. The `Z` → `+00:00` rewrite exists because `datetime.fromisoformat` pre-3.11 rejects the trailing `Z`; pinning "now" to `timezone.utc` makes the delta well-defined even for naive parsed inputs. A display crash must never take down the hook — the callers additionally wrap `main()` in silent-exit-0.
**Probe:** no dedicated test file (honest gap); byte-exact grep probes executed this pass: `created.endswith("Z")` (1 hit), `TYPE_ICONS.get(cat, "❓")` in both consumers (2 hits), `days // 30` (1 hit). Whole-file read (51 lines).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "format age timeline icons formatting", limit: 10, fields: ["signature", "lines"] });
```
Recorded for graph-connected sessions; MCP not connected this pass (DEGRADED path, whole-file direct reads instead).

## Verdict
Adopt the total-function display contract (fallback icon, empty-string age, blanket except) and the Z-suffix normalization for any timeline renderer. Adapt the bucket boundaries (1h/24h/30d) and icon vocabulary to your memory types. Omit nothing else — the module is minimal by design. Coverage: whole file read; no dedicated tests (recorded gap, grep probes GREEN).
