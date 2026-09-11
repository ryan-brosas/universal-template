<!-- capsule-v2 -->
# Domain-skill exemplar: env-driven extraction script — what shape should a per-site helper script have so an agent can run it through the harness without re-deriving selectors?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How does this repo teach (by one decisive example) the contract for agent-run site-specific scripts?

## claude.ai share-transcript extractor as the canonical pattern
**Path/Symbol:** `agent-workspace/domain-skills/claude-ai/extract-share-transcript.py` (:1-68, whole file); sibling exemplar `browser-use-cloud/cleanup-zombies.py` (163L, covered by cloud-zombie-reaper).
**Signature:** reads `CLAUDE_SHARE_URL` + `OUTPUT_DIR` from environment; uses injected globals `new_tab()/wait_for_load()/js()` (`# noqa: F821 — provided by browser-harness`); exits nonzero with a message on missing env or `{error:…}` payload.
**Data Shape:** output pair named by title slug — `<slug>.json` {title, source_url, turns:[{role,text}]} and `<slug>.md` (## Human / ## Assistant headers); slug = `re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-") or "claude-share"`.
**Selectors:** user turns `[data-testid=user-message]`; assistant turns `.font-claude-response`; container found by walking up from the first user message until it contains the LAST one; title = first line of `[data-testid=page-header]` innerText else document.title.

### Decisive source
```python
new_tab(share_url)            # noqa: F821 — provided by browser-harness
wait_for_load()               # noqa: F821
time.sleep(2)                 # let the conversation tree render
...
data = json.loads(js(js_code))    # noqa: F821
if data.get("error"):
    sys.exit(data["error"])
```

**Flow:** env gate → open share URL in a new tab → fixed 2s render settle (deliberate: share pages hydrate late and are auth-gated) → single js() round-trip returning ONE JSON string (selection + walk-up + per-child role classification all inside the browser) → error dict becomes sys.exit message, never a traceback → mkdir -p OUTPUT_DIR → write JSON then MD → print a 4-line human summary (title/turns/paths).
**Invariant:** ALL logic that can live in the page lives in the page (one serialization boundary instead of many js() calls); auth is assumed from the operator's Chrome session — the script's failure mode for logged-out state is the explicit "no user messages found" error payload; outputs are deterministic functions of (URL, DOM) so reruns overwrite cleanly; the docstring's usage line shows the canonical invocation (`bh -c "$(cat …)"`) making the file self-documenting. This is the repo's ONLY full extractor example — mine the pattern here, don't re-derive it per site.
**Probe:** From repo root: `grep -c 'data-testid=user-message' agent-workspace/domain-skills/claude-ai/extract-share-transcript.py` → exactly 2; `grep -n 'font-claude-response' agent-workspace/domain-skills/claude-ai/extract-share-transcript.py` → :36; `grep -n 're.sub' agent-workspace/domain-skills/claude-ai/extract-share-transcript.py` → :51 slug rule; `grep -c 'noqa: F821' agent-workspace/domain-skills/claude-ai/extract-share-transcript.py` → 3 injected globals. No unit test covers domain-skills — coverage caveat.
**Anchored at the repo root.**

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "domain skills workspace helpers injection", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt env-in/env-files-out single-JSON-roundtrip scripts as the unit of site-specific automation. Adapt selectors per target. Omit the fixed sleep only if your target exposes a readiness signal.
