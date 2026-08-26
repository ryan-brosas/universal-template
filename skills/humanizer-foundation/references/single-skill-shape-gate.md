<!-- capsule-v2 -->
# single-skill-shape-gate — what physical package shape survives plugin loaders and symlink incidents?

**Source:** Humanizer MIT-declared `main@e2e92e7b4b8229253ed5c8e81dc65463fdeddda5`; Codebase Memory `humanizer`. **Question:** How does a repo that IS a skill guarantee loaders find exactly one skill file — no nested duplicates, no symlinks, one pointer?

## One regular root SKILL.md + explicit loader pointer + prompt budget
**Path/Symbol:** `scripts/validate-package.py` :49–53 (layout gate) and :85–86 (budget gate); protected objects: repo root layout, `.claude-plugin/plugin.json` `skills` field.
**Signature:** no function — module-level set/attribute checks.
**Data Shape:** Inputs: filesystem walk result, symlink status of SKILL.md, parsed plugin.json. Failure messages: "Keep one regular SKILL.md at the repo root" (covers both walk mismatch and symlink) and "Point the Claude plugin skill loader at the repo root"; budget: "Keep SKILL.md at 500 lines or fewer".

### Decisive source
```python
skill_files = {path.relative_to(ROOT) for path in ROOT.rglob("SKILL.md")}
if SKILL_PATH.is_symlink() or skill_files != {Path("SKILL.md")}:
    raise SystemExit("Keep one regular SKILL.md at the repo root")
if PLUGIN.get("skills") != ["./"]:
    raise SystemExit("Point the Claude plugin skill loader at the repo root")
```
(:49–53.)

**Flow:** recursive glob for every SKILL.md under ROOT → the resulting relative-path SET must equal exactly `{SKILL.md}` → SKILL.md itself must not be a symlink → plugin.json's `skills` array must equal exactly `["./"]` (the repo root is registered AS the skill; there is no copied second copy to drift). Separately (:85–86), `len(SKILL.splitlines()) > 500` fails the run — the prompt budget keeps the corpus loadable in one context window.

**Invariant:** Any nested SKILL.md (vendored examples, node_modules, release folders) or a symlinked root skill breaks packaging discovery — the gate makes both impossible rather than documenting them. This encodes real incident history from README Version-history: v2.10.2 added a `skills/humanizer/` symlink path "so there is still one prompt" (fixes #202), v2.11.1 shipped a Desktop package with "one regular humanizer/SKILL.md" (fixes #224), v2.11.2 "Removed the plugin symlink and separate Claude Desktop package… GitHub's source ZIP now works in Claude Desktop." The final design deleted the indirection instead of maintaining it.

**Probe:** Deterministic probes executed: direct read :49–53 and :85–86 pins both gates; direct read of plugin.json :14 confirms `"skills": ["./"]`; validator GREEN run (exit 0) exercised both gates live against the actual tree; SKILL.md measured at 456 lines ≤ 500 by whole-file read. Mutation RED (adding a nested SKILL.md / swapping in a symlink) blocked by read-only checkout — recorded caveat.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "humanizer", qn_pattern: "skill_files|SKILL_PATH" })
```

## Verdict
Adopt set-equality over rglob plus an explicit is_symlink refusal as the canonical "one artifact" check, and the pattern of registering the repo root itself (`skills: ["./"]`) instead of copying files into a conventional subpath. Adopt a line-budget gate for any prompt-as-product file (500 here; pick your own context-window-derived number). Adapt the exact budget and the loader-pointer format per host. Omit nothing from the symlink ban if you distribute via ZIP archives — symlinks are exactly what source ZIPs mishandle.
