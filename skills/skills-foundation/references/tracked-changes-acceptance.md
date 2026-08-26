<!-- capsule-v2 -->
# Tracked-Changes Acceptance — how are all tracked changes in a DOCX accepted when no XML operation can do it reliably?

**Source:** anthropics/skills (source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `mnt-hdd-utopia-inspo-reference-skills`. **Question:** Why does acceptance go through a LibreOffice Basic macro, and why is a process TIMEOUT the success signal?

## Macro-dispatch acceptance where TimeoutExpired means done
**Path/Symbol:** `skills/docx/scripts/accept_changes.py::accept_changes` (:36–88) + `_setup_libreoffice_macro` (:91–118); env via `office/soffice.get_soffice_env` (see soffice-shim capsule).
**Signature:** `accept_changes(input_file: str, output_file: str) -> tuple[None, str]`; message string carries `Error: ...` prefix on failure (CLI exit code keys off `"Error" in message`, :134).
**Data Shape:** StarBasic module XML written to `$PROFILE/user/basic/Standard/Module1.xba` invoking `.uno:AcceptAllTrackedChanges` through `com.sun.star.frame.DispatchHelper`; soffice argv = `--headless -env:UserInstallation=file:///tmp/libreoffice_docx_profile --norestore vnd.sun.star.script:Standard.Module1.AcceptAllTrackedChanges?language=Basic&location=application <output>` with subprocess timeout=30.

### Decisive source
```python
try:
    result = subprocess.run(cmd, ..., timeout=30, check=False, env=get_soffice_env())
except subprocess.TimeoutExpired:
    return (
        None,
        f"Successfully accepted all tracked changes: {input_file} -> {output_file}",
    )
```
```python
Sub AcceptAllTrackedChanges()
    ...
    dispatcher.executeDispatch(document, ".uno:AcceptAllTrackedChanges", "", 0, Array())
    ThisComponent.store()
    ThisComponent.close(True)
End Sub
```

**Flow:** input must exist and be .docx → copy2 input to OUTPUT path first → ensure macro file exists (idempotent: if present and contains `AcceptAllTrackedChanges`, skip; else bootstrap the profile with one `--terminate_after_init` run, mkdir, write Module1.xba) → launch soffice headless pointed at that profile running the macro script URL against the output copy.
**Invariant:** The macro calls store() + close(True) but never exits the soffice PROCESS — so on success the 30s subprocess timeout fires, and TimeoutExpired is translated to SUCCESS; a clean exit (returncode observed) actually means something went wrong before the document opened. The work happens on the COPY, never the input. Profile isolation (-env:UserInstallation) keeps macro installation from touching the user's real LibreOffice profile. A porter who "fixes" the timeout handling into an error path breaks every successful run; one who drops --norestore gets session-recovery dialogs in headless mode.
**Probe:** No upstream tests (needs LibreOffice). Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c 'except subprocess.TimeoutExpired' skills/docx/scripts/accept_changes.py` = 1; `grep -c 'AcceptAllTrackedChanges' skills/docx/scripts/accept_changes.py` = 4. Behavioral caveat: full loop needs soffice on host; the inverted contract itself is pinned by the except-branch above.
**Coverage caveat:** integration surface untested upstream; treat live verification as port-time work.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "accept_changes", limit: 5 });
// skills.skills.docx.scripts.accept_changes.accept_changes Function accept_changes.py 36-88
```

## Verdict
Adopt the "UNO dispatch for what XML cannot express" rule (tracked-change acceptance mutates layout-dependent structures), the operate-on-copy discipline, idempotent macro provisioning, and — carefully documented — the timeout-as-success handshake for macros that don't exit. Adapt paths/timeout to host; keep the Error-prefix-in-message CLI contract only if you keep its exit-code consumer.
