<!-- capsule-v2 -->
# Profile copy-to-temp isolation — how do you reuse a live Chrome profile without corrupting or locking it?

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** When launching a browser from the user's real Chrome profile, how do you avoid lock-file sharing violations (esp. Windows) and never write back to the original?

## _copy_profile(): copy-on-launch with transient-file skip and loud lock failure
**Path/Symbol:** `browser_use/browser/profile.py:BrowserProfile._copy_profile` (838-893); helpers `_ignore_chrome_profile_transient_files` (89), `_is_chrome_profile_lock_error` (94-113); patterns constant `CHROME_PROFILE_TRANSIENT_FILE_PATTERNS` (30).
**Signature:** `def _copy_profile(self) -> None` (runs inside `model_post_init`)
**Data Shape:** input `self.user_data_dir` + `profile_directory`; output: `self.user_data_dir` REPOINTED to fresh `tempfile.mkdtemp(prefix='browser-use-user-data-dir-')`. Copy skips `Singleton*`, `*.lock`, `*-journal`, `LOCK`, `LOCKFILE`.

### Decisive source
```python
if 'browser-use-user-data-dir-' in user_data_str.lower():
    # Already using a temp directory, no need to copy
    return
...
shutil.copytree(path_original_profile, path_temp_profile, ignore=_ignore_chrome_profile_transient_files)
except (OSError, shutil.Error) as error:
    if not _is_chrome_profile_lock_error(error):
        raise
    shutil.rmtree(temp_dir, ignore_errors=True)
    raise RuntimeError(
        f'Unable to copy Chrome profile "{self.profile_directory}" because one or more files are locked. '
        'Close any Chrome windows using this profile, or start browser-use with --cdp-url to connect to '
        'an already-running browser instead of copying the profile.') from error
...
local_state_src = path_original_user_data / 'Local State'
if local_state_src.exists():
    shutil.copy(local_state_src, local_state_dst)   # copied AFTER the profile dir
```

**Flow:** post-init → skip when user_data_dir is None OR already a temp dir → detect "is Chrome" (path/channel heuristics) → mkdtemp → copytree(profile dir, transient files ignored) → on lock error: delete temp dir, raise actionable RuntimeError suggesting --cdp-url → else also copy `Local State` → repoint `user_data_dir` at temp.
**Invariant:** the ORIGINAL profile is read-only forever; every launch works on a disposable copy. `_is_chrome_profile_lock_error` must recurse into shutil.Error's `(src, dst, exc)` triple structure AND check `winerror == 32` / PermissionError — missing any branch turns a friendly error into a confusing crash mid-copy. Temp-dir marker string doubles as idempotency guard (re-validation never re-copies its own temp dirs). Missing source profile dir ⇒ create empty structure in temp (fresh profile), not an error.
**Probe:** deterministic: `_is_chrome_profile_lock_error(PermissionError())` True; OSError with `winerror=32` True; shutil-triple args containing 'WinError 32' True; plain ValueError False. Executed green in gate 5. Coverage caveat: no upstream unit file.
**Retrieve note:** graph anchor `BrowserProfile._copy_profile` resolves at profile.py:838.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_copy_profile _is_chrome_profile_lock_error", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt copy-on-launch + transient-file skip + structured lock-error detection for any tool that borrows a live app profile; adapt the marker-string idempotency to your own temp prefix; omit Windows-specific message strings only if you don't target Windows (they are load-bearing there).
