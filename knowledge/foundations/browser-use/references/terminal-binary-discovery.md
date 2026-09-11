<!-- capsule-v2 -->
# Terminal binary discovery ladder — how do you locate and capability-check an optional native companion binary?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** in what order should a Python wrapper resolve a native binary, and how does it verify the binary actually speaks the required subcommand before use?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py:186` `find_browser_use_terminal_binary`; `_find_packaged_browser_use_terminal_binary` (:211); `_terminal_supports_sdk_server` (:262); agent-tools dir resolution `_find_agent_tools_dir` (:228), `_agent_tools_dir_contains_ripgrep` (:254).
**Signature:** `find_browser_use_terminal_binary() -> str` (raises `BetaAgentError`); `_terminal_supports_sdk_server(binary: Path) -> bool`.
**Data Shape:** env override `BROWSER_USE_TERMINAL_BINARY`; packaged lookup via optional `browser_use_core.binary_path('browser-use-terminal')`; home candidates `~/.browser-use-terminal/packages/standalone/current/bin/browser-use-terminal` and `~/.local/bin/browser-use-terminal` (`BUT_HOME`/`BUT_INSTALL_DIR` overridable); final fallback `shutil.which`.

### Decisive source
```python
env_path = os.environ.get('BROWSER_USE_TERMINAL_BINARY')
if env_path: return env_path                       # 1. explicit override — NOT capability-checked
packaged_path = _find_packaged_browser_use_terminal_binary()   # 2. wheel-bundled core
for candidate in [but_home/'...'/ 'browser-use-terminal', but_install_dir/'...']:  # 3. install dirs
    if candidate.exists() and _terminal_supports_sdk_server(candidate):
        return str(candidate)
path_binary = shutil.which('browser-use-terminal')             # 4. PATH
if path_binary and _terminal_supports_sdk_server(Path(path_binary)):
    return path_binary
raise BetaAgentError(f'Could not find browser-use-terminal. Install ... with `{TERMINAL_INSTALL_COMMAND}` ...')
# capability check = run `<binary> --help` with timeout=5 and grep for 'sdk-server':
return 'sdk-server' in f'{result.stdout}\n{result.stderr}'
```

**Flow:** env → packaged → two well-known install dirs → PATH; every filesystem candidate (but NOT the env override) must pass the help-text probe advertising the `sdk-server` subcommand; failure raises with the exact one-line curl install command. A parallel ladder resolves the sibling `agent-tools/` dir (next to any accepted binary) and only trusts it when it contains ripgrep (`rg`, `rg.exe` on Windows); that dir is then injected into the child env via `_apply_agent_tools_env` + PATH prepend.
**Invariant:** existence is never sufficient — a stale binary without `sdk-server` must be skipped, not crashed on later; error messages carry the remediation command verbatim; the tools dir is validated by its payload (ripgrep present) not by its name.
**Probe:** no dedicated unit test pins this ladder at HEAD (the discovery path is exercised indirectly by protocol-negotiation tests); coverage caveat recorded. Deterministic source pin: `grep -n "sdk-server' in" browser_use/beta/service.py` hits :271 inside `_terminal_supports_sdk_server`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "find_browser_use_terminal_binary _agent_tools_dir_contains_ripgrep", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered ladder + help-probe capability gate + payload-validated tool dir as a reusable distribution pattern; adapt candidate paths and the probe token to your binary's CLI; omit the `browser_use_core` packaging import if you have no wheel-bundled twin.
