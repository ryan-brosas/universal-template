<!-- capsule-v2 -->
# Authentication-source gate — all artifacts or a remedy-naming refusal

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** When several files together constitute "we have a session", how should startup behave when only SOME of them exist?

## get_authentication_source
**Path/Symbol:** `linkedin_mcp_server/authentication.py` (:23-57); consumed by `drivers/browser.ensure_authenticated` (:918-926).
**Signature:** `get_authentication_source() -> bool` — raises `CredentialsNotFoundError`; `clear_auth_state(profile_dir: Path | None = None) -> bool`.
**Data Shape:** The gate reads THREE artifacts of one source session: profile dir (`profile_exists`), portable cookies (`portable_cookie_path`), source state metadata (`load_source_state`). Any one alone is not authentication.

### Decisive source
```python
source_state = load_source_state(profile_dir)
if profile_exists(profile_dir) and cookies_path.exists() and source_state:
    return True

if profile_exists(profile_dir) or cookies_path.exists():
    raise CredentialsNotFoundError(
        "LinkedIn source session metadata is missing or incomplete.\n\n"
        f"Expected source metadata: {source_state_path(profile_dir)}\n"
        f"Expected portable cookies: {cookies_path}\n\n"
        'Run with --login to create a fresh source session generation.')

raise CredentialsNotFoundError(          # nothing at all: enumerate the remedies
    "No LinkedIn source session found.\n\nOptions:\n"
    "  1. Run with --login ...\n  2. Run with --no-headless ...\n"
    "For Docker users:\n  Create the mounted profile with --login --login-viewer...")
```
**Flow:** check all three → success only on completeness; PARTIAL artifacts get a distinct error naming exactly which expected paths were checked (so the user can see what is missing) plus the repair command; ABSENT artifacts get an options menu including the Docker mount recipe. Clearing removes source AND every derived runtime session.
**Invariant:** Never proceed half-authenticated, and never collapse "corrupt/partial" into "absent" — the middle branch exists because a profile without its metadata means something different from no profile at all, and each failure names its own remedy. Errors carry paths, not guesses.
**Probe:** `tests/test_authentication.py` (:58-70) pins requires-metadata (partial ⇒ raise naming "source session metadata") and accepts-complete; :73-102 pins clear removing source + derived runtime files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "get_authentication_source CredentialsNotFoundError ensure_authenticated", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-state gate (complete / partial-naming-paths / absent-enumerating-remedies) for any multi-artifact credential store. Adapt artifact names and remedies; keep the "distinct message per failure shape" discipline. Omit the LinkedIn/Docker wording. Coverage caveat: none — module fully indexed; graph shows no direct CALLS inbound (dispatched via bootstrap/driver layer), consumer verified by search + test.
