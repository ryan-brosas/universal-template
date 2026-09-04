<!-- capsule-v2 -->
# ADR section merge — how do you let agents update a shared architecture record without clobbering unknown content?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What closed section vocabulary and merge algorithm keep a per-project ADR both editable and bounded?

## Six canonical sections + parse/merge/render with 8000-char cap
**Path/Symbol:** `src/store/store.c` — canonical_sections (7811–7813), `cbm_adr_parse_sections` (7880–7912), `cbm_store_adr_update_sections` (8201–8255), cap `CBM_ADR_MAX_LENGTH 8000` (store.h:768).
**Signature:** `int cbm_store_adr_update_sections(cbm_store_t *s, const char *project, const char **keys, const char **values, int count, cbm_adr_t *out);`
**Data Shape:** Sections = `## KEY` headers limited to {PURPOSE, STACK, ARCHITECTURE, PATTERNS, TRADEOFFS, PHILOSOPHY}; non-canonical `## CUSTOM` lines are CONTENT of the enclosing section (not new sections); ≤16 sections in memory; merged output >8000 chars ⇒ ERR before store.

### Decisive source
```c
static const char *canonical_sections[] = {"PURPOSE", "STACK", "ARCHITECTURE",
                                           "PATTERNS", "TRADEOFFS", "PHILOSOPHY"};
...
/* Render buffer discipline: snprintf returns the length it WOULD have written,
 * so clamp pos into [0, buf_sz-1] after every write or the next call computes a
 * wrapped (huge) remaining size and writes out of bounds. */
```

**Flow:** read existing ADR (missing table ⇒ NOT_FOUND so a legacy generation stays replaceable) → parse into ordered key/value sections via header detection (`## ` + canonical name + trim) → upsert each requested key or append within the 16-slot bound → render with clamped snprintf writes → enforce the 8000-char budget BEFORE storing → ON CONFLICT upsert keyed by project.
**Invariant:** Unknown headers must be preserved as body text, never dropped; the size gate fires before persistence, not after.
**Probe:** `tests/test_store_arch.c:adr_parse_sections_basic`, `adr_parse_sections_all_six`, `adr_parse_sections_non_canonical`, plus `adr_store_and_retrieve` / `adr_upsert`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_adr_update_sections", limit: 5 });
```

## Verdict
Adopt closed-vocabulary section parsing + pre-store size gate for any agent-writable doc; adapt the section list to your domain; omit the preamble handling if your format always starts with a header.
