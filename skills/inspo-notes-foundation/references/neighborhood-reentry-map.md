<!-- capsule-v2 -->
# Ingest §3 Neighborhood re-entry map — how does a capture note hand the next session a ready-made reading plan?

**Source:** user-authored ingest notes over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/notes`; Codebase Memory `inspo-notes`. **Question:** What must the fixed Neighborhood section contain so a later session can resume exploration of the pinned subsystem without re-deriving its module map?

## The bullet grammar: backticked symbol + em-dash role
**Path/Symbol:** section 3 of every INGEST note (`browser-harness-get_ws_url.md:11`, `browser-use-BrowserSession.connect.md:11`, `cuga-agent-PolicySystem.md:9`, `growchief-cdpDetectionPass.md:11`, `jobspy-scrape.md:11`, `pydantic-ai-harness-BrowserUse.md:9`); graph Section nodes `inspo-notes.<note>.3.-Neighborhood` at those exact line anchors.
**Signature:** every bullet is `- `<backticked-symbol-or-file>`` + ` — ` + a ONE-LINE role clause naming what it does or why it matters to the target; bullets are ordered call-adjacent first (helpers the target directly uses), then lifecycle/entry neighbors, then test paths last when present.
**Data Shape:** 29 neighborhood bullets across the six notes (bh 8 · bu 5 · cuga 6 · gc 4 · js 2 · pah 4); roles are functional ("stale DevToolsActivePort must not count as a running browser"), never restatements of the name; tests appear as a neighborhood entry only when they pin the target's contract (`tests/unit/test_daemon.py`, `tests/ci/browser/test_cdp_headers.py`).

### Decisive source
```markdown
## 3. Neighborhood
- `profile_dirs` — OS Chrome/Edge/Brave/Arc/Dia paths the port file can live in.
- `_devtools_port_live` — stale DevToolsActivePort must not count as a running browser.
- `_ws_from_devtools_active_port` — Chrome 147+ 404 on `/json/version` for default
  profile; fall back to the ws path Chrome wrote.
```
(`notes/browser-harness-get_ws_url.md:11-14`)

**Flow:** finish the flow narrative (§2) → enumerate ONLY symbols a porter would actually open next, one line each → make every role clause carry a behavioral fact (what breaks without it), not a name echo → close with direct-test locations so the pressure test is reachable → later sessions read this list as their reading order into the indexed project.
**Invariant:** the section exists in ALL SIX notes (exactly one per note) and every bullet opens with a backticked token — a name-only bullet with no behavioral clause violates the format because it adds navigation cost instead of saving it. The graph resolves the section by its own heading text (`search_code pattern:"Neighborhood"` → 6 Section nodes, one per note, line-exact), which is itself the retrieval proof that the anatomy is uniform.
**Probe:** deterministic probes (repo-root-relative to the notes dir): `awk '/^## 3\. Neighborhood/,/^## 4\./' notes/browser-harness-get_ws_url.md | grep -c '^- `' = **8**, same awk for browser-use = **5**, cuga = **6**, growchief = **4**, jobspy = **2**, pydantic-ai-harness = **4** (total 29).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "inspo-notes", pattern: "Neighborhood", limit: 10 });
// EXECUTED 2026-08-24 inspo-notes pass 10: results: 6 — one .3.-Neighborhood Section node per note,
// each line-exact at its true heading line (11/11/9/11/11/9). search_graph BM25 returns total: 0 on this
// doc-shaped graph (tokenless Section nodes) — search_code is the working primitive, caveat inherited
// from the docs-knowledge pass-9 audit and re-confirmed live this pass.
```

## Verdict
Adopt the backticked-symbol + one-line-behavioral-role bullet grammar verbatim for any new capture note; adapt the ordering convention to your codebase's shape (call-adjacent-first is the observed norm, not a hard rule); omit exhaustive file listings — the neighborhood is a curated reading plan, not a directory census, and anything not worth one behavioral line belongs in the work record instead.
