<!-- capsule-v2 -->
# Repo hygiene ladder — how do you mechanically enforce repo-wide discipline while exempting named append-only records?

**Source:** pi-template MIT `foundations-sync@37e9bc1736b7`; Codebase Memory `pi-template`. **Question:** What is the complete check ladder, what does it skip, and how does a single named exemption keep an unbounded multi-lane record from breaking the gate?

## Skip-listed walk + per-file check ladder + one named exemption
**Path/Symbol:** `scripts/repo-hygiene.py:walk` (lines 33–45), `check_file` (47–126), named exemption lines 53–56, secrets patterns line 110+, `check_orphans` (128–166), submodule ban line 182.
**Signature:** `walk() -> Iterator[str]` yields files under BASE minus `SKIP_DIRS` (`{.git, node_modules, .venv, site-packages, .bak, .veda, .pi/fabric, .pi/artifacts, inspect, .pi/hindsight}`, also skipping `*.bak` dirs/files and `.jsonl`); `check_file(path) -> None` appends to global `errors[]`.
**Data Shape:** TEXT_EXT gate limits text checks to md/json/yml/yaml/py/mjs/ts/toml/txt/sh.

### Decisive source
```python
# Named exemption: the append-only multi-lane drain work record is
# intentionally unbounded (one [DONE:N] entry per run across many
# cron lanes); the >1MB artifact rule was not meant for it.
if rel != ".pi/work/foundations-deep-farm/research.md":
    size_kb = os.path.getsize(path) / 1024
    if size_kb > MAX_KB:
        errors.append(f"large file ({size_kb:.0f}KB > {MAX_KB}KB): {rel}")
```
Ladder per text file: trailing whitespace (first offending line only, then break), missing EOF newline, mixed CRLF+LF, smart quotes \u201c\u201d\u2018\u2019 and ligatures fi/fl, `json.loads` / `tomllib.loads` validity, YAML validity for `.github/workflows/*.yml` + `.pi/**/*.yml` behind a best-effort `import yaml`, lightweight secret regexes (`(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]`, `sk-…20+`, `ghp_…20+`, `AKIA…16`) on code/config extensions, typo dictionary on prose (.md/.txt) only, first hit per category to keep output bounded.
`check_orphans()`: collects images vs markdown `![..](..)`/`<img src>` refs (repo-root and relative resolution), flags unreferenced images and committed scratch files (`.tmp .bak .log .swp`).

**Flow:** walk skip-list → per-file ladder → orphan sweep → submodule ban (`.gitmodules` presence) → print first 50 errors + total, exit 1 if any.
**Invariant:** generated/runtime state is skipped BY LIST, not by gitignore parsing; exactly one NAMED path may exceed the 1MB cap — exemptions are enumerated, never patterned.

**Probe (live, RED observed):** `python3 scripts/repo-hygiene.py` at the pin → exit 1 with EXACTLY:
```
REPO HYGIENE FAILURES:
  - large file (1638KB > 1024KB): .pi/work/foundations-deep-farm/llm-repo-learning.md
  - smart quote in .pi/work/foundations-deep-farm/llm-repo-learning.md
  ... 2 total
```
This is the exemption mechanism proving its own necessity: the SIBLING append-only ledger grew past the cap but has no named exemption yet (only `research.md` does). Do NOT widen the exemption pattern — add the specific path if you own it; this lane does not.

## Get live surrounding code
**Retrieve:** (executed at the pin)
```ts
await mcp.codebase_memory.search_graph({ project: "pi-template", query: "repo hygiene trailing whitespace secrets large files typos", limit: 5 });
// -> scripts.repo-hygiene.walk 33-45, check_file 47-126, check_orphans 128-166
```

## Verdict
Adopt the full ladder order and "first-hit-per-file" output bounding; adopt named-path exemptions as the ONLY legal way to waive a mechanical rule. Adapt extension sets and secret regexes to your stack. Omit Pi-specific skip dirs; re-derive them from your repo's generated-state list.
