<!-- capsule-v2 -->
# GUI launch shim — streamlit subprocess with dev-mode-conditional flags and credentials pre-seed

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does a terminal-first tool bolt on a browser UI (streamlit) without letting that dependency — or streamlit's own first-run prompts — break the CLI?

## Probe→consent→install via shared util; pre-write empty credentials.toml (#772); flag set forks on "-dev" in version
**Path/Symbol:** `aider/main.py`: `check_streamlit_install(io)` (:208, delegates to `utils.check_pip_install_extra(io, "streamlit", msg, ["aider-chat[browser]"])`), `write_streamlit_credentials()` (:217-230), `launch_gui(args)` (:233-268); entry branch :666-673 (skipped entirely when `return_coder`).
**Signature:** `st_args = ["run", gui.__file__, "--browser.gatherUsageStats=false", "--runner.magicEnabled=false", "--server.runOnSave=false"]` + dev-only additions `--global.developmentMode=false --server.fileWatcherType=none --client.toolbarMode=viewer` when NOT `"-dev" in str(__version__)`, then `"--" + argv` passthrough.
**Data Shape:** credential file = `<streamlit file_util.get_streamlit_file_path()>/credentials.toml` containing exactly `[general]\nemail = ""\n`.

### Decisive source
```python
credential_path = Path(get_streamlit_file_path()) / "credentials.toml"
if not os.path.exists(credential_path):
    empty_creds = '[general]\nemail = ""\n'
    os.makedirs(os.path.dirname(credential_path), exist_ok=True)
    with open(credential_path, "w") as f:
        f.write(empty_creds)      # See https://github.com/Aider-AI/aider/issues/772
...
is_dev = "-dev" in str(__version__)
if is_dev:
    print("Watching for file changes.")
else:
    st_args += ["--global.developmentMode=false", ...]
```

**Flow:** `--gui` → install probe (offers pip install of the browser extra if missing; abort politely on decline) → seed empty credentials so streamlit's interactive email prompt never appears (#772) → run streamlit IN-PROCESS via `cli.main(st_args)` with telemetry off and viewer toolbar → argv after `--` reaches the gui module.
**Invariant:** the GUI is a launch-mode, not a library mode: analytics events bracket it ("gui session"/"exit") and `return_coder` callers never see it; dev builds keep hot-reload enabled while release builds disable ALL watcher/magic machinery for stability.
**Probe:** deterministic anchors: `grep -nF 'empty_creds' aider/main.py` → :224/:228; `grep -nF 'gatherUsageStats' aider/main.py` → :249. Direct tests: none upstream for launch_gui (source-pinned caveat; check_streamlit_install shares utils.check_pip_install_extra covered by test_main).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "launch_gui write_streamlit_credentials", limit: 3 });
// resolves main.py GUI trio line-exact
```

## Verdict
Adopt the credentials-pre-seed + dev/release flag fork for embedding streamlit (or any first-run-prompting framework) inside another CLI; adapt flags. The #772 pattern — write the config file BEFORE importing the framework — generalizes to any tool that prompts on first paint.
