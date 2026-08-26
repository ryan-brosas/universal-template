<!-- capsule-v2 -->
# Agent-editable helper extension — how do users add custom helpers without forking the package?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How are workspace-defined helpers injected into the pre-imported namespace, and what import-ordering constraint makes it work?

## Bottom-import cycle-break + globals() merge
**Path/Symbol:** `src/browser_harness/helpers.py:_load_agent_helpers/bottom-import-of-recorder/goto_url-domain-skills` (:130-135, :518-538).
**Signature:** `_load_agent_helpers()` — spec_from_file_location("browser_harness_agent_helpers", `<workspace>/agent_helpers.py`), exec_module, merge non-underscore names into helpers.globals().
**Data Shape:** Workspace file OPTIONAL (missing ⇒ silent skip); underscore-prefixed names stay private; recorder exports (start_recording/stop_recording/recording_dir) re-exported through the same star-import surface; goto_url attaches up to 10 domain-skill markdown paths per hostname when `BH_DOMAIN_SKILLS=1`.

### Decisive source
```python
# Imported at the bottom so recorder's own `from . import helpers` sees a
# fully-defined module. Exposes the recording helpers via `from .helpers import *`.
from .recorder import start_recording, stop_recording, recording_dir

def _load_agent_helpers():
    p = AGENT_WORKSPACE / "agent_helpers.py"
    if not p.exists():
        return
    ...
    for name, value in vars(module).items():
        if name.startswith("_"):
            continue
        globals()[name] = value

_load_agent_helpers()
```

**Flow:** core definitions complete → recorder imported AT THE BOTTOM (breaking the helpers↔recorder cycle) → workspace module loaded → public names merged → run.py's star-import then wraps everything traced.
**Invariant:** The recorder import MUST come after helpers' definitions or the circular import executes against a half-built module; workspace helpers land BEFORE trace installation so user helpers get telemetry/recording free; underscore prefix is the only privacy boundary; domain-skills injection is env-gated OFF by default (agents opt in per deployment).
**Probe:** No direct unit test merges a workspace helper — coverage caveat; goto_url gating pinned in `tests/unit/test_helpers.py:37-53` (omits by default, includes sorted file names when enabled); packaged-skill frontmatter contract pinned by `tests/unit/test_skill.py` (exact name/description keys).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "agent helpers workspace load", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt bottom-import cycle-breaking + post-load workspace merge for any extensible-by-file tool. Adapt merge rules (allowlist instead of underscore filter). Omit domain-skills if you have no per-site hint corpus.
