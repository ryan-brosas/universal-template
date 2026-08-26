<!-- capsule-v2 -->
# Canonical path pairing — why must expanduser() and resolve() travel together?

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How should a module normalize user-configured directory paths so sidecar computation never diverges from the directory itself?

## One named function used everywhere
**Path/Symbol:** `linkedin_mcp_server/session_state.py:canonical()` (:60-77); consumed by `auth_root_dir()`, `portable_cookie_path()`, `source_state_path()`.
**Signature:** `canonical(profile_dir: Path) -> Path` = `profile_dir.expanduser().resolve()`.
**Data Shape:** In: any user-spelled path (relative, `~`, symlinked). Out: absolute, dereferenced path. Every path in the module is spelled through this function — no exceptions.

### Decisive source
```python
def canonical(profile_dir: Path) -> Path:
    """Expand and resolve one profile path, the only way this module spells it.

    Both halves, everywhere, and the pairing is what was missing. Expanding
    without resolving and resolving without expanding used to sit side by side
    here: ``get_source_profile_dir`` did the first, ``auth_root_dir`` the
    second. An ordinary relative path survives that split... **A symlink does
    not.** ``shutil.move`` relocates the link itself while the sidecars are
    computed from the target's parent, so a rotation would move the profile out
    of one directory and its cookies out of another... One session, split
    across two roots, with no error anywhere.
    """
    return profile_dir.expanduser().resolve()
```

**Flow:** config value → `canonical()` at every read → profile dir and all sidecars (cookies.json, state jsons, quarantine dirs) derive from the SAME resolved parent.
**Invariant:** Path normalization is ONE named function used everywhere — not because either half is wrong alone, but because the PAIRING is the invariant. A relative path survives an expand-without-resolve / resolve-without-expand split; a symlink does not, and the failure is silent.
**Probe:** `tests/test_session_state.py` exercises paths through the module's accessors; the docstring records the measured failure mode (rotation splitting one session across two roots).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "canonical expanduser resolve auth_root_dir", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the named-normalizer-everywhere rule verbatim in any module that moves a directory while computing sibling paths. Adapt function name. Omit nothing — the lesson is the discipline, not the code.
