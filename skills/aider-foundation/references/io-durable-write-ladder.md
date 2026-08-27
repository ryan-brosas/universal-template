<!-- capsule-v2 -->
# Durable write ladder — how does a file-mutation choke point stay previewable, lock-tolerant, and never lie about failure?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** Where do you enforce dry-run, which failures deserve a retry, and how do readers report unreadable files without crashing the session?

## One mutation funnel with a dry-run gate; fail-open readers beside it
**Path/Symbol:** `aider/io.py`: `InputOutput.write_text` (:478-507), `read_text` (:453-476), `read_image` (:435-451). Consumers (graph CALLS, callers_total=43 distinct functions; usage-weighted 94 edges): every coder's `apply_edits`, `search_replace.{dmp_apply,dmp_lines_apply,map_patches,proc,git_cherry_pick_*}`, `main.check_gitignore/make_new_repo`, `ModelInfoManager._update_cache`, `OpenRouterModelManager._update_cache`, benchmark runners.
**Signature:** `write_text(filename, content, max_retries=5, initial_delay=0.1) -> None`; `read_text(filename, silent=False) -> str | None`; `read_image(filename) -> str | None` (base64).
**Data Shape:** writes honor `self.encoding` + `self.newline` centrally; readers return bare content or `None`; `None` is the universal "unreadable" signal callers must handle.

### Decisive source
```python
if self.dry_run:
    return                                    # :487-488 preview enforced at THE choke point
...
except PermissionError as err:
    if attempt < max_retries - 1:
        time.sleep(delay); delay *= 2         # :498-499 ONLY lock errors retry
    else:
        self.tool_error(f"Unable to write file {filename} after {max_retries} attempts: {err}")
        raise                                 # :504 final failure is LOUD
except OSError as err:
    self.tool_error(f"Unable to write file {filename}: {err}")
    raise                                     # :505-507 disk-full etc. never retried
```

```python
except FileNotFoundError: ...                # read_text :460 correct subclass order
except IsADirectoryError: ...
except OSError as err: ...
except UnicodeError: ... tool_error("Use --encoding to set the unicode encoding.")  # :475
```

**Flow:** every coder edit and cache write lands in `write_text`, so `dry_run` short-circuits before any filesystem touch — one gate protects all mutators. Retry policy is narrow by design: PermissionError (file locked by another process) backs off 0.1s→0.2→0.4→0.8→1.6 across five attempts then reports AND re-raises so the caller knows the edit failed; any other OSError reports and raises immediately (transient-vs-permanent split). Readers invert the contract: FileNotFoundError/IsADirectoryError/OSError/UnicodeError each map to a graded message (suppressible via `silent=True`) plus a `None` return; UnicodeError adds the `--encoding` remediation hint. Images divert to base64 `read_image`.
**Invariant:** a porter gets exactly three behaviors — preview mode cannot be bypassed by forgetting it in one coder, only lock contention is worth waiting for, and no read failure ever escapes as an exception. Known latent defect to NOT copy: `read_image` orders its broad `except OSError` (:440) BEFORE its `FileNotFoundError`/`IsADirectoryError` subclasses (:443/:446) — those two branches are unreachable dead code (`read_text` orders them correctly).
**Probe:** no dedicated upstream suite drives this plane (standing caveat, anchor-verified). Executed this run: `.venv/bin/python -m pytest tests/basic/test_io.py -k 'autocompleter or confirm_ask' -q` → **7 passed, 16 deselected**, plus byte-exact anchor checks of :487-507/:453-476/:435-451 against served snippets.
**Coverage caveat:** aider/io.py `no_recorded_issue` @ generation_matches:true.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "write_text", limit: 3 });
// rank-1 total:1: aider.aider.io.InputOutput.write_text aider/io.py 478-507 (-24.98)
await mcp.codebase_memory.trace_path({ project: "aider", function_name: "write_text", direction: "inbound" });
// callers_total: 43 (page 1 shows apply_edits family, search_replace internals, main, both _update_cache twins)
```

## Verdict
Adopt the single-funnel write choke point with an up-front dry-run gate, PermissionError-only exponential backoff ending in a loud raise, and fail-open readers returning `None` with graded diagnostics. Adapt retry bounds and messages to your host. Omit the read_image except-ordering (dead branches) — mirror read_text's ordering instead.
