<!-- capsule-v2 -->
# Source-footer freshness dialects — how does a card footer record WHERE the clone lives and HOW FRESH it is, in one line?

**Source:** user-authored digest docs over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/docs`; Codebase Memory `docs`. **Question:** What must the `Source:` footer pin so a reader can both locate the clone on disk and judge whether its digest still describes it?

## One-line footer: path + clone-depth + freshness stamp
**Path/Symbol:** every card's final lines — e.g. `docs/browser-use.md:8-9` (`Source:` line then `See` pointer); all 11 cards resolve to the same pointer text (11/11 identical, verified live).
**Signature:** `Source: \`~/work/inspo/<repo>/\` (<depth>, <stamp>)` followed by ``See `~/work/inspo/README.md` for the full inspo index.`` — two footer dialects exist for `<stamp>`:
  1. **shallow dialect (10 cards):** `(shallow clone, fresh HEAD)` — depth recorded, freshness asserted WITHOUT a commit id;
  2. **full dialect (1 card):** `(full clone, HEAD \`3c989dc0\` v0.13.8, refreshed 2026-08-18)` — depth + pinned SHA + version tag + refresh date.
**Data Shape:** input = clone metadata at ingest time; output = a footer whose freshness claim strength matches the ingest depth; the See-pointer binds the dir-local card set to the library-level index document.

### Decisive source
```markdown
Source: `~/work/inspo/browser-use/` (full clone, HEAD `3c989dc0` v0.13.8, refreshed 2026-08-18)
See `~/work/inspo/README.md` for the full inspo index.
```
(`docs/browser-use.md:8-9`; shallow twin: `Source: \`~/work/inspo/JobSpy/\` (shallow clone, fresh HEAD)` at `docs/JobSpy.md:8`)

**Flow:** write the local clone path with the `~/work/inspo/` prefix → record clone depth (shallow vs full) → stamp freshness: bare "fresh HEAD" only where the clone is shallow and re-pullable, full `HEAD <sha> <version>` + date where the clone is deep and drift matters → close with the See-pointer to the library index.
**Invariant:** exactly ONE `Source:` line per card and ONE See-pointer per card (11/11 cards, verified live); the freshness stamp's precision must MATCH the clone depth — never pin a SHA you cannot re-derive from a shallow clone, never assert bare "fresh" on a deep clone that can silently drift.
**Probe:** deterministic probe: `grep -c 'fresh HEAD' docs/*.md | grep -cv ':0'` = 10 AND `grep -c 'refreshed' docs/*.md | grep -cv ':0'` = 1 AND `grep -h '^See ' docs/*.md | sort -u | wc -l` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "docs", pattern: "work/inspo", limit: 15 });
// resolves ALL 11 card Modules (docs.<repo> each citing its Source:/See: footer lines 7-9)
// (EXECUTED 2026-08-24 thin-elevator pass: results: 11, per-file line pairs like 8;9;
// search_graph forms return 0 on this doc-shaped graph — search_code is the working primitive)
```

## Verdict
Adopt the one-line footer with depth-matched freshness stamps and the uniform See-pointer; adapt paths/stamps to your library layout but keep the depth↔precision coupling; omit SHA pins on shallow clones (unfalsifiable) — and NOTE THE LIVE DRIFT this capsule records: the pointer names `README.md`, which was rebuilt as `INSPO.md` on 2026-08-24, so footers now dangle until their owning lane refreshes them; porters should treat the pointer target as resolvable-through-rename or fix pointers at refresh time.
