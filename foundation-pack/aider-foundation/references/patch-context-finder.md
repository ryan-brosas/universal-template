<!-- capsule-v2 -->
# Patch context matching — exact → rstrip → strip fuzz tiers with EOF anchoring and a +10,000 penalty

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How do you locate a patch's context block inside the real file while QUANTIFYING how much benefit of the doubt you gave it?

## Three-tier match + EOF anchor
**Path/Symbol:** `aider/coders/patch_coder.py`: `find_context(lines, context, start, eof)` (:81), `find_context_core(lines, context, start)` (:59).
**Signature:** `(index: int, fuzz: int) — index -1 means not found; fuzz 0 | 1 | 100 | (+10_000 if EOF-anchored context didn't actually land at EOF)`.
**Data Shape:** tier 1 = exact list-slice equality; tier 2 = per-line `.rstrip()` equality (trailing whitespace ignored); tier 3 = per-line `.strip()` equality (leading AND trailing ignored); EOF marker first tries the file tail (`len(lines) - len(context)`), falls back to a from-`start` scan but stamps +10_000 so callers can detect the violation.

### Decisive source
```python
def find_context(lines, context, start, eof):
    if eof:
        if len(lines) >= len(context):
            new_index, fuzz = find_context_core(lines, context, len(lines) - len(context))
            if new_index != -1:
                return new_index, fuzz          # anchored at EOF as promised
        new_index, fuzz = find_context_core(lines, context, start)
        return new_index, fuzz + 10_000         # EOF lied ⇒ huge penalty, still applies
    return find_context_core(lines, context, start)
```

**Flow:** `_parse_update_file_sections` adds up `total_fuzz` across every section and scope match; `@@` scope lines get their own two-pass search (exact then strip-fuzzy, +1 each); the accumulated `Patch.fuzz` lets a host REJECT or flag patches that only applied through heavy fuzzing.
**Invariant:** tiers are tried in strict order and the FIRST hit returns (never "best of all hits"); empty context short-circuits to `(start, 0)`; the fuzz number is metadata for policy decisions, never silently discarded.
**Probe:** executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::patch-find-context-tiers` (exact=0 / rstrip=1 / EOF-hit=0 / EOF-miss≥10_000), repo venv GREEN. No upstream direct tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "find_context", limit: 5 });
// also resolves: find_context_core (same file)
```

## Verdict
Adopt the tiered matcher AND the fuzz-as-accounting contract (apply anyway, record the doubt); adapt tier thresholds if your sources are whitespace-noisier; omit nothing else — 35 lines total. Coverage caveat: probe-pinned only.
